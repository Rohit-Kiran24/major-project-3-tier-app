"""Unit tests for chat API routes — uses SQLite in-memory, no real DB needed."""
import os
import pytest

# Override env BEFORE importing app so Config picks up test values
os.environ['USE_SECRETS_MANAGER'] = 'false'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'test'
os.environ['DB_USER'] = 'test'
os.environ['DB_PASS'] = 'test'
os.environ['SECRET_KEY'] = 'ci-test-secret-key'

from app import create_app
from models import db, User, Room


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with application.app_context():
        db.create_all()
        # Seed a default room (normally created by create_app, but SQLite starts fresh)
        if not Room.query.filter_by(name='general').first():
            db.session.add(Room(name='general', description='General discussion'))
            db.session.commit()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """A test client that is already logged in."""
    with app.app_context():
        user = User(username='chatuser')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={
        'username': 'chatuser',
        'password': 'password123'
    }, follow_redirects=True)
    return client


def test_get_rooms_redirects_when_unauthenticated(client):
    """Unauthenticated users should be redirected to login."""
    response = client.get('/api/rooms')
    assert response.status_code in [302, 401]


def test_get_rooms_when_authenticated(auth_client):
    response = auth_client.get('/api/rooms')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_create_new_room(auth_client):
    response = auth_client.post('/api/rooms',
        json={'name': 'test-room', 'description': 'A test room'},
        content_type='application/json'
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'test-room'


def test_create_duplicate_room_returns_conflict(auth_client):
    auth_client.post('/api/rooms',
        json={'name': 'dup-room'},
        content_type='application/json'
    )
    response = auth_client.post('/api/rooms',
        json={'name': 'dup-room'},
        content_type='application/json'
    )
    assert response.status_code == 409


def test_get_messages_for_general_room(auth_client, app):
    with app.app_context():
        room = Room.query.filter_by(name='general').first()
        if room:
            response = auth_client.get(f'/api/messages/{room.id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'messages' in data
            assert 'total' in data
