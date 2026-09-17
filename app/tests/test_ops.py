"""
Unit tests for the Ops Console.

Covers the three things that matter most: the panel does not exist unless it is
switched on, its endpoints are not reachable without a login, and destructive
actions are refused for non-admins. Also checks that AWS-only features report
their absence honestly instead of returning invented numbers.
"""
import importlib
import os

import pytest

import ops


@pytest.fixture
def make_app(monkeypatch):
    """Build an app with a chosen DEMO_MODE / ADMIN_USERS combination."""
    def _make(demo='true', admins='tester'):
        monkeypatch.setenv('DEMO_MODE', demo)
        monkeypatch.setenv('ADMIN_USERS', admins)
        monkeypatch.setenv('OPS_BACKGROUND', 'false')
        monkeypatch.delenv('ASG_NAME', raising=False)
        import app as app_module
        importlib.reload(app_module)
        application = app_module.create_app()
        application.config['TESTING'] = True
        return application
    return _make


def _login(client, application, username='tester', admin=True):
    from models import db, User
    with application.app_context():
        user = User(username=username)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    client.post('/login', data={'username': username, 'password': 'password123'},
                follow_redirects=True)


# ─── Feature flag ────────────────────────────────────────────────────────────

def test_ops_endpoints_absent_when_demo_mode_off(make_app):
    """With DEMO_MODE off the blueprint is never registered, so the demo and
    chaos endpoints do not exist at all — not merely forbidden."""
    application = make_app(demo='false')
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        assert client.get('/api/ops/status').status_code == 404
        assert client.post('/api/ops/spike').status_code == 404
        assert client.post('/api/ops/heal').status_code == 404


def test_ops_endpoints_exist_when_demo_mode_on(make_app):
    application = make_app(demo='true')
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        # Present, but gated by login rather than missing
        assert client.get('/api/ops/status').status_code != 404


# ─── Authentication ──────────────────────────────────────────────────────────

def test_status_requires_login(make_app):
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        assert client.get('/api/ops/status').status_code in (302, 401)


def test_spike_requires_login(make_app):
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        assert client.post('/api/ops/spike').status_code in (302, 401)


# ─── Authorisation ───────────────────────────────────────────────────────────

def test_non_admin_cannot_spike(make_app):
    """A logged-in non-admin may read telemetry but not press the buttons."""
    application = make_app(admins='someone-else')
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        assert client.get('/api/ops/status').status_code == 200
        assert client.post('/api/ops/spike', json={'minutes': 1}).status_code == 403


def test_no_admins_configured_blocks_everyone(make_app):
    application = make_app(admins='')
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        res = client.post('/api/ops/spike', json={'minutes': 1})
        assert res.status_code == 403
        assert 'ADMIN_USERS' in res.get_json()['error']


# ─── Telemetry shape ─────────────────────────────────────────────────────────

def test_status_reports_real_fields(make_app):
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        data = client.get('/api/ops/status').get_json()

        assert data['mode'] in ('aws', 'local')
        assert data['is_admin'] is True
        for key in ('cpu', 'memory', 'uptime_s', 'connections', 'msgs_per_min'):
            assert key in data['node']
        assert isinstance(data['node']['cpu'], (int, float))
        assert 'database' in data['dependencies']
        assert 'redis' in data['dependencies']


def test_cluster_reports_aws_unavailable_locally(make_app):
    """Running off EC2 the panel must say AWS data is unavailable rather than
    fabricate an Auto Scaling Group, which is what the 2-tier panel did."""
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        asg = client.get('/api/ops/cluster').get_json()['asg']
        assert asg['available'] is False
        assert 'reason' in asg


# ─── AWS-only guards ─────────────────────────────────────────────────────────

@pytest.mark.parametrize('path', ['/api/ops/scale', '/api/ops/heal'])
def test_aws_only_actions_refused_locally(make_app, path):
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        res = client.post(path, json={})
        assert res.status_code == 503
        assert res.get_json()['error'] == 'AWS only'


# ─── Burst limits ────────────────────────────────────────────────────────────

def test_burst_is_capped(make_app):
    application = make_app()
    with application.app_context():
        from models import db, Room
        db.create_all()
        if not Room.query.filter_by(name='general').first():
            db.session.add(Room(name='general', description='General discussion'))
            db.session.commit()
        client = application.test_client()
        _login(client, application, 'tester')
        data = client.post('/api/ops/burst', json={'count': 99999}).get_json()
        assert data['count'] == ops.MAX_BURST
        assert data['rate_per_s'] > 0


def test_burst_unknown_room(make_app):
    application = make_app()
    with application.app_context():
        from models import db
        db.create_all()
        client = application.test_client()
        _login(client, application, 'tester')
        res = client.post('/api/ops/burst', json={'count': 1, 'room': 'nope'})
        assert res.status_code == 404


# ─── Spike safety ────────────────────────────────────────────────────────────

def test_spike_seconds_are_capped():
    """The cap protects a burstable instance from an unbounded busy loop."""
    assert ops.MAX_SPIKE_SECONDS == 600


def test_spike_runs_in_a_separate_process():
    """A CPU burn inside the eventlet worker would block the event loop, drop
    WebSockets and fail health checks, so the ASG would kill the instance under
    test. The load must therefore be a child process."""
    started = ops.start_spike(10)
    try:
        assert started is True
        assert ops.is_spiking() is True
        assert ops.start_spike(10) is False        # no second spike while running
        for proc in ops._state['spike_procs']:
            assert proc.pid != os.getpid()
    finally:
        ops.stop_spike()
    assert ops.is_spiking() is False


def test_identity_falls_back_off_ec2():
    ops._identity = None
    ident = ops.get_identity()
    assert ident['on_aws'] is False
    assert ident['az'] == 'local'
    assert ops.aws_available() is False
