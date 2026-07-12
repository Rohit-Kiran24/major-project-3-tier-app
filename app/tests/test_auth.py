"""Unit tests for authentication routes — uses SQLite in-memory so no real DB needed."""
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
from models import db, User


@pytest.fixture
def app():
    """Create test application with in-memory SQLite (no PostgreSQL needed)."""
    application = create_app()
    application.config['TESTING'] = True
    # Override PostgreSQL URI with SQLite so tests run without a real DB
    application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    application.config['WTF_CSRF_ENABLED'] = False

    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_page_loads(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Create Account' in response.data


def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign In' in response.data


def test_register_new_user(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpass123',
        'confirm_password': 'testpass123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_register_duplicate_user(client, app):
    with app.app_context():
        user = User(username='existing')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    response = client.post('/register', data={
        'username': 'existing',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b'already taken' in response.data


def test_login_valid_credentials(client, app):
    with app.app_context():
        user = User(username='validuser')
        user.set_password('correctpass')
        db.session.add(user)
        db.session.commit()

    response = client.post('/login', data={
        'username': 'validuser',
        'password': 'correctpass'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_invalid_credentials(client):
    response = client.post('/login', data={
        'username': 'nouser',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert b'Invalid' in response.data


def test_health_endpoint_returns_json(client):
    response = client.get('/health')
    # 200 (all good) or 503 (degraded — expected in CI with no real DB/Redis)
    assert response.status_code in [200, 503]
    data = response.get_json()
    assert data is not None
    assert 'status' in data
    assert 'database' in data
