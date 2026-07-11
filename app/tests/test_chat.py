"""Unit tests for chat API routes."""
import pytest
from app import create_app
from models import db, User, Room


@pytest.fixture
def app():
    import os
    os.environ['USE_SECRETS_MANAGER'] = 'false'

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Client with authenticated user."""
    with app.app_context():
        user = User(username='chatuser')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={
        'username': 'chatuser',
        'password': 'password123'
    })
    return client


def test_get_rooms_unauthenticated(client):
    response = client.get('/api/rooms')
    assert response.status_code in [302, 401]


def test_get_rooms_authenticated(auth_client):
    response = auth_client.get('/api/rooms')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_create_room(auth_client):
    response = auth_client.post('/api/rooms',
        json={'name': 'test-room', 'description': 'A test room'},
        content_type='application/json'
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'test-room'


def test_create_duplicate_room(auth_client):
    auth_client.post('/api/rooms',
        json={'name': 'dup-room'},
        content_type='application/json'
    )
    response = auth_client.post('/api/rooms',
        json={'name': 'dup-room'},
        content_type='application/json'
    )
    assert response.status_code == 409


def test_get_messages(auth_client, app):
    with app.app_context():
        room = Room.query.filter_by(name='general').first()
        if room:
            response = auth_client.get(f'/api/messages/{room.id}')
            assert response.status_code == 200
            data = response.get_json()
            assert 'messages' in data
            assert 'total' in data
