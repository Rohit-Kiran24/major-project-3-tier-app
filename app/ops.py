"""
Ops Console — live telemetry and demonstration controls.

Every number reported here is measured, never simulated. Where a figure can only
come from AWS (Auto Scaling state, scaling history, alarm state) and we are not
running on EC2, the response says so explicitly rather than inventing a value.

Disabled entirely unless DEMO_MODE=true. Destructive actions additionally require
the caller's username to appear in ADMIN_USERS.
"""

import json
import os
import subprocess
import sys
import time
from collections import deque
from functools import wraps
from urllib import request as urlrequest

import psutil
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from config import Config

ops_bp = Blueprint('ops', __name__, url_prefix='/api/ops')

# ---------------------------------------------------------------- constants --
MAX_SPIKE_SECONDS = 600          # hard cap, whatever the client asks for
NODE_TTL = 15                    # seconds a node's metrics stay in Redis
MAX_BURST = 200
HEAL_COOLDOWN = 120
SCALE_COOLDOWN = 30
SPIKE_CHANNEL = 'ops:spike'
NODE_KEY = 'ops:node:'

# Busy-loop in a SEPARATE PROCESS. Doing this in a thread would block eventlet's
# event loop: WebSockets would drop and /health would stop answering, so the ALB
# would pull the instance out and the ASG would terminate the very machine being
# load-tested.
_BURN = "import time,sys\nend=time.time()+float(sys.argv[1])\nwhile time.time()<end: pass\n"

_state = {
    'connections': 0,
    'msg_times': deque(maxlen=2000),
    'spike_procs': [],
    'spike_until': 0.0,
    'last_action': {},
    'started_at': time.time(),
}

_identity = None


# ----------------------------------------------------------------- identity --
def get_identity():
    """Instance id / AZ from EC2 IMDSv2, or a local fallback. Cached."""
    global _identity
    if _identity is not None:
        return _identity

    def imds(path, token):
        req = urlrequest.Request(
            'http://169.254.169.254/latest/meta-data/' + path,
            headers={'X-aws-ec2-metadata-token': token},
        )
        return urlrequest.urlopen(req, timeout=1).read().decode()

    try:
        treq = urlrequest.Request(
            'http://169.254.169.254/latest/api/token',
            method='PUT',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
        )
        token = urlrequest.urlopen(treq, timeout=1).read().decode()
        _identity = {
            'instance_id': imds('instance-id', token),
            'az': imds('placement/availability-zone', token),
            'instance_type': imds('instance-type', token),
            'on_aws': True,
        }
    except Exception:
        _identity = {
            'instance_id': os.environ.get('HOSTNAME', 'local')[:12],
            'az': 'local',
            'instance_type': 'container',
            'on_aws': False,
        }
    return _identity


def short_id():
    return get_identity()['instance_id']


# ------------------------------------------------------------ chat counters --
def inc_connections():
    _state['connections'] += 1


def dec_connections():
    _state['connections'] = max(0, _state['connections'] - 1)


def note_message():
    _state['msg_times'].append(time.time())


def _msgs_per_min():
    cutoff = time.time() - 60
    return sum(1 for t in _state['msg_times'] if t >= cutoff)


# ------------------------------------------------------------------ metrics --
def _redis_client():
    import redis
    return redis.Redis(
        host=Config.REDIS_HOST, port=Config.REDIS_PORT,
        socket_timeout=1, socket_connect_timeout=1, decode_responses=True,
    )


def local_metrics():
    ident = get_identity()
    return {
        'instance_id': ident['instance_id'],
        'az': ident['az'],
        'instance_type': ident['instance_type'],
        'on_aws': ident['on_aws'],
        'cpu': round(psutil.cpu_percent(interval=None), 1),
        'memory': round(psutil.virtual_memory().percent, 1),
        'uptime_s': int(time.time() - _state['started_at']),
        'connections': _state['connections'],
        'msgs_per_min': _msgs_per_min(),
        'spiking': is_spiking(),
        'ts': time.time(),
    }


def dependency_latency():
    """Real round-trip times to PostgreSQL and Redis."""
    out = {}
    from models import db
    t0 = time.perf_counter()
    try:
        db.session.execute(db.text('SELECT 1'))
        out['database'] = {'ok': True, 'ms': round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        out['database'] = {'ok': False, 'error': str(exc)[:120]}

    t0 = time.perf_counter()
    try:
        _redis_client().ping()
        out['redis'] = {'ok': True, 'ms': round((time.perf_counter() - t0) * 1000, 1)}
    except Exception as exc:
        out['redis'] = {'ok': False, 'error': str(exc)[:120]}
    return out


def publish_metrics():
    """Share this node's metrics so any node can render the whole cluster."""
    try:
        m = local_metrics()
        _redis_client().setex(NODE_KEY + m['instance_id'], NODE_TTL, json.dumps(m))
    except Exception:
        pass


def cluster_nodes():
    """Every node that reported within the TTL, this one included."""
    nodes = {}
    try:
        r = _redis_client()
        for key in r.scan_iter(NODE_KEY + '*', count=100):
            raw = r.get(key)
            if raw:
                n = json.loads(raw)
                nodes[n['instance_id']] = n
    except Exception:
        pass
    me = local_metrics()
    nodes.setdefault(me['instance_id'], me)
    return sorted(nodes.values(), key=lambda n: n['instance_id'])


# -------------------------------------------------------------------- spike --
def is_spiking():
    _state['spike_procs'] = [p for p in _state['spike_procs'] if p.poll() is None]
    return bool(_state['spike_procs'])


def start_spike(seconds):
    seconds = max(10, min(int(seconds), MAX_SPIKE_SECONDS))
    if is_spiking():
        return False
    workers = max(1, os.cpu_count() or 1)
    _state['spike_procs'] = [
        subprocess.Popen([sys.executable, '-c', _BURN, str(seconds)])
        for _ in range(workers)
    ]
    _state['spike_until'] = time.time() + seconds
    return True


def stop_spike():
    for p in _state['spike_procs']:
        try:
            p.terminate()
        except Exception:
            pass
    _state['spike_procs'] = []
    _state['spike_until'] = 0.0


def broadcast_spike(action, seconds=0):
    """Tell every node to spike. One instance at 100% only moves the ASG average
    to ~50% with two instances, which never crosses the 70% alarm threshold."""
    try:
        _redis_client().publish(
            SPIKE_CHANNEL, json.dumps({'action': action, 'seconds': seconds}))
        return True
    except Exception:
        return False


def spike_listener():
    """Background task: act on spike commands sent by any node."""
    while True:
        try:
            pubsub = _redis_client().pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(SPIKE_CHANNEL)
            for msg in pubsub.listen():
                try:
                    cmd = json.loads(msg['data'])
                except Exception:
                    continue
                if cmd.get('action') == 'start':
                    start_spike(cmd.get('seconds', 300))
                elif cmd.get('action') == 'stop':
                    stop_spike()
        except Exception:
            time.sleep(5)


def metrics_publisher():
    while True:
        publish_metrics()
        time.sleep(3)


# ---------------------------------------------------------------------- AWS --
def _asg_name():
    return os.environ.get('ASG_NAME', '')


def _boto(service):
    import boto3
    return boto3.client(
        service, region_name=os.environ.get('AWS_DEFAULT_REGION', 'ap-south-1'))


def aws_available():
    return bool(get_identity()['on_aws'] and _asg_name())


def asg_state():
    """Live Auto Scaling state, recent activity and alarm status."""
    if not aws_available():
        return {'available': False,
                'reason': 'Not running on EC2, or ASG_NAME is unset (AWS only)'}
    try:
        asg = _boto('autoscaling')
        group = asg.describe_auto_scaling_groups(
            AutoScalingGroupNames=[_asg_name()])['AutoScalingGroups'][0]
        acts = asg.describe_scaling_activities(
            AutoScalingGroupName=_asg_name(), MaxRecords=10)['Activities']
        project = os.environ.get('PROJECT_NAME', 'three-tier-chat')
        alarms = _boto('cloudwatch').describe_alarms(
            AlarmNames=[project + '-high-cpu', project + '-low-cpu'])['MetricAlarms']
        return {
            'available': True,
            'desired': group['DesiredCapacity'],
            'min': group['MinSize'],
            'max': group['MaxSize'],
            'instances': [{'instance_id': i['InstanceId'], 'az': i['AvailabilityZone'],
                           'lifecycle': i['LifecycleState'], 'health': i['HealthStatus']}
                          for i in group['Instances']],
            'activities': [{'description': a['Description'], 'status': a['StatusCode'],
                            'start': a['StartTime'].isoformat()} for a in acts],
            'alarms': [{'name': a['AlarmName'], 'state': a['StateValue']} for a in alarms],
        }
    except Exception as exc:
        return {'available': False, 'reason': str(exc)[:200]}


# --------------------------------------------------------------- decorators --
def demo_enabled():
    return os.environ.get('DEMO_MODE', 'false').lower() == 'true'


def _admins():
    return [u.strip() for u in os.environ.get('ADMIN_USERS', '').split(',') if u.strip()]


def is_admin():
    return getattr(current_user, 'username', None) in _admins()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _admins():
            return jsonify({'error': 'No admins configured. Set ADMIN_USERS.'}), 403
        if not is_admin():
            return jsonify({'error': 'Admin only'}), 403
        return fn(*args, **kwargs)
    return wrapper


def _cooldown(key, seconds):
    last = _state['last_action'].get(key, 0)
    remaining = seconds - (time.time() - last)
    if remaining > 0:
        return int(remaining)
    _state['last_action'][key] = time.time()
    return 0


# ---------------------------------------------------------------- endpoints --
@ops_bp.route('/status', methods=['GET'])
@login_required
def status():
    return jsonify({
        'mode': 'aws' if get_identity()['on_aws'] else 'local',
        'aws_features': aws_available(),
        'is_admin': is_admin(),
        'node': local_metrics(),
        'dependencies': dependency_latency(),
        'spike': {'active': is_spiking(),
                  'seconds_left': max(0, int(_state['spike_until'] - time.time()))},
    })


@ops_bp.route('/cluster', methods=['GET'])
@login_required
def cluster():
    return jsonify({'nodes': cluster_nodes(), 'asg': asg_state()})


@ops_bp.route('/spike', methods=['POST'])
@login_required
@admin_required
def spike():
    minutes = float((request.get_json(silent=True) or {}).get('minutes', 5))
    seconds = int(max(0.5, min(minutes, 10)) * 60)
    if is_spiking():
        return jsonify({'error': 'A spike is already running'}), 409
    delivered = broadcast_spike('start', seconds)
    start_spike(seconds)   # always load this node, even if Redis is unreachable
    return jsonify({'status': 'ok', 'seconds': seconds, 'cluster_wide': delivered})


@ops_bp.route('/spike/stop', methods=['POST'])
@login_required
@admin_required
def spike_stop():
    broadcast_spike('stop')
    stop_spike()
    return jsonify({'status': 'ok'})


@ops_bp.route('/scale', methods=['POST'])
@login_required
@admin_required
def scale():
    if not aws_available():
        return jsonify({'error': 'AWS only'}), 503
    wait = _cooldown('scale', SCALE_COOLDOWN)
    if wait:
        return jsonify({'error': 'Cooling down, {}s left'.format(wait)}), 429
    state = asg_state()
    if not state.get('available'):
        return jsonify({'error': state.get('reason', 'ASG unavailable')}), 503
    delta = int((request.get_json(silent=True) or {}).get('delta', 1))
    target = max(state['min'], min(state['desired'] + delta, state['max']))
    _boto('autoscaling').set_desired_capacity(
        AutoScalingGroupName=_asg_name(), DesiredCapacity=target, HonorCooldown=False)
    return jsonify({'status': 'ok', 'desired': target})


@ops_bp.route('/heal', methods=['POST'])
@login_required
@admin_required
def heal():
    if not aws_available():
        return jsonify({'error': 'AWS only'}), 503
    wait = _cooldown('heal', HEAL_COOLDOWN)
    if wait:
        return jsonify({'error': 'Cooling down, {}s left'.format(wait)}), 429
    instance_id = (request.get_json(silent=True) or {}).get('instance_id') or short_id()
    _boto('autoscaling').set_instance_health(
        InstanceId=instance_id, HealthStatus='Unhealthy', ShouldRespectGracePeriod=False)
    return jsonify({'status': 'ok', 'instance_id': instance_id})


@ops_bp.route('/burst', methods=['POST'])
@login_required
@admin_required
def burst():
    from datetime import datetime
    from models import db, Message, Room, iso_utc

    body = request.get_json(silent=True) or {}
    count = max(1, min(int(body.get('count', 100)), MAX_BURST))
    room_name = body.get('room', 'general')
    room = Room.query.filter_by(name=room_name).first()
    if not room:
        return jsonify({'error': 'Room {} not found'.format(room_name)}), 404

    tag = short_id()
    az = get_identity()['az']
    now = datetime.utcnow()
    contents = ['[burst {}/{}] from {}'.format(i + 1, count, tag) for i in range(count)]

    t0 = time.perf_counter()
    # created_at is set explicitly rather than left to the column default so the
    # value written to the row and the value broadcast below are the same
    # timestamp — bulk_save_objects does not write server/ORM-evaluated defaults
    # back onto the Python objects, so relying on msg.created_at after this call
    # would read back an unset attribute.
    db.session.bulk_save_objects([
        Message(content=c, user_id=current_user.id, room_id=room.id, created_at=now)
        for c in contents
    ])
    db.session.commit()
    write_ms = (time.perf_counter() - t0) * 1000

    note_message()

    # bulk_save_objects is a straight INSERT — it never goes through the
    # per-message handler in chat.py, so without this loop a burst writes rows
    # to PostgreSQL that nobody's open browser ever sees appear. The point of
    # the button is to watch messages arrive live, so broadcast each one the
    # same way a normal send does.
    from app import socketio
    created_at = iso_utc(now)
    for content in contents:
        socketio.emit('new_message', {
            'content': content,
            'username': current_user.username,
            'room': room_name,
            'created_at': created_at,
            'served_by': tag,
            'az': az,
        }, room=room_name)

    return jsonify({
        'status': 'ok',
        'count': count,
        'write_ms': round(write_ms, 1),
        'per_message_ms': round(write_ms / count, 2),
        'rate_per_s': round(count / max(write_ms / 1000, 0.001), 1),
    })


# --------------------------------------------------------------------- init --
def init(socketio):
    """Start background tasks. Skipped under pytest via OPS_BACKGROUND=false."""
    if not demo_enabled():
        return
    if os.environ.get('OPS_BACKGROUND', 'true').lower() != 'true':
        return
    psutil.cpu_percent(interval=None)      # prime the CPU sampler
    socketio.start_background_task(metrics_publisher)
    socketio.start_background_task(spike_listener)
