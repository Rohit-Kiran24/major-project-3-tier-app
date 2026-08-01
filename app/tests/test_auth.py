"""
Unit tests for authentication routes.
conftest.py sets all env vars + SQLite URI before import, so no PostgreSQL needed.
"""
import pytest
from app import create_app
from models import db, User


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
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


def test_health_endpoint_is_shallow(client):
    """
    /health is the ALB liveness probe and must return 200 whenever the process
    is serving — even with Redis down, as it is in CI. If this ever starts
    returning 503 on a dependency failure, the ASG will terminate healthy
    instances during a transient blip.
    """
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data['status'] == 'healthy'
    # Must not report dependency state — that belongs to /ready.
    assert 'database' not in data
    assert 'redis' not in data


def test_ready_endpoint_reports_dependencies(client):
    """/ready is the deep check: 200 healthy, 503 degraded (no Redis in CI)."""
    response = client.get('/ready')
    assert response.status_code in [200, 503]
    data = response.get_json()
    assert data is not None
    assert 'status' in data
    assert 'database' in data
    assert 'redis' in data
