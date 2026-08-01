"""
Main Flask Application — Three-Tier Chat App
Entrypoint for Gunicorn. Initializes Flask, SocketIO, database, and blueprints.
"""

import os
import logging
from flask import Flask, jsonify, redirect, url_for
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config
from models import db, bcrypt, User, Room
from auth import auth_bp
from chat import chat_bp, register_socket_events

# ======================== App Factory ========================

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize config (fetch secrets from AWS if enabled)
    Config.init_app(app)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    # ======================== Health Check Routes ========================

    @app.route('/')
    def index():
        """Redirect to chat or login."""
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('chat.chat_page'))
        return redirect(url_for('auth.login'))

    @app.route('/health')
    def health():
        """
        Liveness probe — used by the ALB target group.

        Deliberately shallow: it reports only that this process is up and
        serving. It must NOT check RDS or Redis. The ASG uses ELB health
        checks, so a dependency blip that returned 503 here would make the
        ALB drop the instance and the ASG terminate it — turning a brief
        Redis hiccup into a rolling instance-replacement loop.

        For dependency status use /ready.
        """
        return jsonify({
            'status': 'healthy',
            'service': 'three-tier-chat'
        }), 200

    @app.route('/ready')
    def ready():
        """
        Readiness probe — deep check of RDS and Redis connectivity.

        Returns 503 when a dependency is down. Intended for humans, dashboards
        and debugging; not wired to the ALB for the reason described above.
        """
        try:
            db.session.execute(db.text('SELECT 1'))
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'

        try:
            import redis
            r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, socket_timeout=2)
            r.ping()
            redis_status = 'healthy'
        except Exception as e:
            redis_status = f'unhealthy: {str(e)}'

        status = 'healthy' if db_status == 'healthy' and redis_status == 'healthy' else 'degraded'
        code = 200 if status == 'healthy' else 503

        return jsonify({
            'status': status,
            'database': db_status,
            'redis': redis_status
        }), code

    # Create tables on first request
    with app.app_context():
        db.create_all()
        # Create default room if none exists
        if not Room.query.filter_by(name='general').first():
            default_room = Room(name='general', description='General discussion')
            db.session.add(default_room)
            db.session.commit()

    return app


# ======================== Create App + SocketIO ========================

app = create_app()

# Initialize SocketIO with Redis message queue for cross-instance pub/sub
redis_url = Config.REDIS_URL if os.environ.get('USE_SECRETS_MANAGER', 'false').lower() == 'true' \
    or os.environ.get('REDIS_HOST', 'localhost') != 'localhost' \
    else None

socketio = SocketIO(
    app,
    message_queue=redis_url,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=False
)

# Register WebSocket event handlers
register_socket_events(socketio)

# ======================== Dev Server ========================
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
