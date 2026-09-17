"""
Chat module — WebSocket event handlers + REST API for rooms/messages.
Uses Flask-SocketIO with Redis message queue for cross-instance pub/sub.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from models import db, Room, Message
import ops

chat_bp = Blueprint('chat', __name__)


# ======================== REST API Routes ========================

@chat_bp.route('/chat')
@login_required
def chat_page():
    """Main chat page."""
    rooms = Room.query.order_by(Room.created_at).all()
    return render_template(
        'chat.html', rooms=rooms, user=current_user,
        demo_mode=ops.demo_enabled(), is_admin=ops.is_admin(),
        served_by=ops.short_id(), served_az=ops.get_identity()['az'],
    )


@chat_bp.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    """List all chat rooms."""
    rooms = Room.query.order_by(Room.created_at).all()
    return jsonify([r.to_dict() for r in rooms])


@chat_bp.route('/api/rooms', methods=['POST'])
@login_required
def create_room():
    """Create a new chat room."""
    data = request.get_json()
    name = data.get('name', '').strip()

    if not name or len(name) < 2:
        return jsonify({'error': 'Room name must be at least 2 characters'}), 400

    if Room.query.filter_by(name=name).first():
        return jsonify({'error': 'Room already exists'}), 409

    room = Room(name=name, description=data.get('description', ''), created_by=current_user.id)
    db.session.add(room)
    db.session.commit()

    return jsonify(room.to_dict()), 201


@chat_bp.route('/api/messages/<int:room_id>', methods=['GET'])
@login_required
def get_messages(room_id):
    """Get paginated message history for a room."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 50, type=int)
    per_page = min(per_page, 100)  # Cap at 100

    messages = (
        Message.query
        .filter_by(room_id=room_id)
        .order_by(Message.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        'messages': [m.to_dict() for m in reversed(messages.items)],
        'page': page,
        'pages': messages.pages,
        'total': messages.total
    })


# ======================== WebSocket Event Handlers ========================

def register_socket_events(socketio):
    """Register all SocketIO event handlers."""

    @socketio.on('connect')
    def handle_connect():
        if not current_user.is_authenticated:
            return False  # Reject unauthenticated connections
        ops.inc_connections()
        emit('status', {'msg': f'{current_user.username} connected'})

    @socketio.on('join')
    def handle_join(data):
        room = data.get('room', 'general')
        join_room(room)
        emit('status', {
            'msg': f'{current_user.username} joined {room}'
        }, room=room)

    @socketio.on('leave')
    def handle_leave(data):
        room = data.get('room', 'general')
        leave_room(room)
        emit('status', {
            'msg': f'{current_user.username} left {room}'
        }, room=room)

    @socketio.on('message')
    def handle_message(data):
        room_name = data.get('room', 'general')
        content = data.get('message', '').strip()

        if not content:
            return

        # Find or create room
        room = Room.query.filter_by(name=room_name).first()
        if not room:
            return

        # Save to RDS (persistent history)
        msg = Message(
            content=content,
            user_id=current_user.id,
            room_id=room.id
        )
        db.session.add(msg)
        db.session.commit()

        ops.note_message()

        # Broadcast to ALL instances via Redis pub/sub.
        # served_by/az travel with the message so the UI can show which instance
        # handled it — visible proof that delivery crosses instances.
        emit('new_message', {
            'id': msg.id,
            'content': content,
            'username': current_user.username,
            'room': room_name,
            'created_at': msg.created_at.isoformat(),
            'served_by': ops.short_id(),
            'az': ops.get_identity()['az'],
        }, room=room_name)

    @socketio.on('disconnect')
    def handle_disconnect():
        ops.dec_connections()
        if current_user.is_authenticated:
            emit('status', {
                'msg': f'{current_user.username} disconnected'
            }, broadcast=True)
