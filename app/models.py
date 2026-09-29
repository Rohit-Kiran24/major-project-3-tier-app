"""
SQLAlchemy models for the chat application.
Tables: users, rooms, messages
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin

db = SQLAlchemy()
bcrypt = Bcrypt()


def iso_utc(dt):
    """Serialize a naive UTC datetime with an explicit 'Z' suffix.

    db.Column(db.DateTime, default=datetime.utcnow) stores naive UTC values,
    and naive isoformat() ("2026-09-29T12:47:03") carries no timezone marker.
    The browser's `new Date(...)` then reads it as local time instead of UTC,
    so every timestamp displayed is off by the viewer's UTC offset. Appending
    'Z' is enough for JavaScript to parse it as UTC and convert it correctly.
    """
    return dt.isoformat() + 'Z'


class User(UserMixin, db.Model):
    """User account for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    rooms_created = db.relationship('Room', backref='creator', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': iso_utc(self.created_at)
        }


class Room(db.Model):
    """Chat room / channel."""
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    messages = db.relationship('Message', backref='room', lazy='dynamic',
                               cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': iso_utc(self.created_at)
        }


class Message(db.Model):
    """Chat message with persistent storage."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'username': self.author.username if self.author else '[deleted]',
            'room_id': self.room_id,
            'created_at': iso_utc(self.created_at)
        }
