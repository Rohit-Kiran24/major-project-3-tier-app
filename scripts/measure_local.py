"""
Local multi-instance measurement harness.

Runs real measurements against the docker-compose stack (two application
containers, one PostgreSQL, one Redis) and writes the results to JSON. Every
figure quoted in the report and the paper should come from a run of this script,
so the numbers can be reproduced on demand.

Prerequisites:
    docker compose -f docker/docker-compose.yml up -d --build
    pip install "python-socketio[client]" requests

Usage:
    python scripts/measure_local.py all
    python scripts/measure_local.py latency --probes 30
    python scripts/measure_local.py failure
    python scripts/measure_local.py recovery --outage 45

What each phase measures:
    latency   cross-instance vs same-instance delivery time (the cost of the
              Redis backplane), plus burst throughput and persistence
    failure   probe behaviour and delivery while Redis is stopped
    recovery  the interval between /ready reporting 200 and cross-instance
              delivery actually resuming after Redis returns
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime

import requests
import socketio

APP_A = 'http://localhost:5000'
APP_B = 'http://localhost:5001'
ROOM = 'general'
REDIS_CONTAINER = 'docker-redis-1'
RESULTS = 'measurements.json'


# ----------------------------------------------------------------- helpers --
def log(msg):
    print('  ' + msg, flush=True)


def login(base_url, username, password='probe-pass-123'):
    """Register (idempotent) and log in. Returns the session cookie header."""
    session = requests.Session()
    session.post(f'{base_url}/register',
                 data={'username': username, 'password': password,
                       'confirm_password': password}, timeout=10)
    res = session.post(f'{base_url}/login',
                       data={'username': username, 'password': password},
                       timeout=10)
    if 'session' not in session.cookies:
        raise RuntimeError(f'login failed at {base_url} (status {res.status_code})')
    return '; '.join(f'{k}={v}' for k, v in session.cookies.items()), session


def connect(base_url, cookie, on_message=None):
    """Open an authenticated Socket.IO connection and join the room."""
    client = socketio.Client(reconnection=False)
    if on_message:
        client.on('new_message', on_message)
    client.connect(base_url, headers={'Cookie': cookie},
                   transports=['websocket'], wait_timeout=15)
    client.emit('join', {'room': ROOM})
    time.sleep(0.5)          # let the join settle before probing
    return client


def summarise(samples):
    if not samples:
        return {'count': 0}
    ordered = sorted(samples)
    idx95 = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        'count': len(samples),
        'mean_ms': round(statistics.mean(samples), 2),
        'median_ms': round(statistics.median(samples), 2),
        'p95_ms': round(ordered[idx95], 2),
        'max_ms': round(max(samples), 2),
    }


def probe_health(base_url, timeout=25):
    """Record status AND latency. Latency is the point: a probe that answers
    200 too slowly is still a failed health check as far as a load balancer
    with a 5-second timeout is concerned."""
    out = {}
    for path in ('/health', '/ready'):
        start = time.perf_counter()
        try:
            res = requests.get(base_url + path, timeout=timeout)
            out[path] = {'status': res.status_code,
                         'seconds': round(time.perf_counter() - start, 2)}
        except Exception as exc:
            out[path] = {'status': f'no response ({type(exc).__name__})',
                         'seconds': round(time.perf_counter() - start, 2)}
        out[path]['within_alb_timeout_5s'] = (
            isinstance(out[path]['status'], int) and out[path]['seconds'] <= 5)
    return out


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=60)


def redis_container_name():
    """Find the Redis container whatever the compose project is called."""
    res = docker('ps', '--filter', 'name=redis', '--format', '{{.Names}}')
    names = [n for n in res.stdout.split() if n]
    # Other projects may have containers matching "redis" (a kind control-plane
    # node, for instance), so prefer this compose project's own service.
    for name in names:
        if name.startswith('docker-redis'):
            return name
    if not names:
        raise RuntimeError('no running Redis container found')
    raise RuntimeError(f'could not identify the compose Redis among: {names}')


# ------------------------------------------------------------ measurements --
def measure_latency(probes):
    """Cross-instance vs same-instance delivery latency, then a burst."""
    log(f'connecting three clients ({probes} probes)')
    cookie_a, session_a = login(APP_A, 'probe_sender')
    cookie_b, _ = login(APP_B, 'probe_receiver')
    cookie_c, _ = login(APP_A, 'probe_baseline')

    arrivals = {'cross': {}, 'same': {}}
    origins = {}
    burst = {'tag': None, 'seen': 0, 'last': None}

    def record(bucket):
        def handler(data):
            now = time.perf_counter()
            content = data.get('content', '')
            if content.startswith('probe:'):
                tag = content.split(':', 2)[1]
                arrivals[bucket].setdefault(tag, now)
                origins.setdefault(tag, {})[bucket] = data.get('served_by')
            elif bucket == 'cross' and burst['tag'] and content.startswith(
                    'burst:' + burst['tag']):
                burst['seen'] += 1
                burst['last'] = now
        return handler

    sender = connect(APP_A, cookie_a)
    receiver_cross = connect(APP_B, cookie_b, record('cross'))
    receiver_same = connect(APP_A, cookie_c, record('same'))

    sent = {}
    for _ in range(probes):
        tag = uuid.uuid4().hex[:8]
        sent[tag] = time.perf_counter()
        sender.emit('message', {'message': f'probe:{tag}:latency', 'room': ROOM})
        time.sleep(0.25)
    time.sleep(3)            # allow stragglers

    cross_ms = [(arrivals['cross'][t] - sent[t]) * 1000 for t in sent if t in arrivals['cross']]
    same_ms = [(arrivals['same'][t] - sent[t]) * 1000 for t in sent if t in arrivals['same']]

    result = {
        'probes_sent': probes,
        'cross_instance': {**summarise(cross_ms),
                           'delivered': f'{len(cross_ms)} / {probes}'},
        'same_instance': {**summarise(same_ms),
                          'delivered': f'{len(same_ms)} / {probes}'},
    }
    if cross_ms and same_ms:
        delta = result['cross_instance']['mean_ms'] - result['same_instance']['mean_ms']
        result['backplane_cost_ms'] = round(delta, 2)
        result['backplane_cost_pct'] = round(
            100 * delta / result['same_instance']['mean_ms'], 1)

    # Did the two paths really come from different instances?
    instances = {b: v for tag in origins for b, v in origins[tag].items()}
    result['served_by'] = instances
    result['distinct_instances'] = len(set(instances.values()))

    log(f"cross {result['cross_instance'].get('mean_ms')} ms  |  "
        f"same {result['same_instance'].get('mean_ms')} ms")

    # ---- burst ----
    log('burst: 200 messages as fast as the client can send')
    burst_tag = uuid.uuid4().hex[:6]
    burst['tag'] = burst_tag
    burst_n = 200
    t0 = time.perf_counter()
    for i in range(burst_n):
        sender.emit('message', {'message': f'burst:{burst_tag}:{i}', 'room': ROOM})
    deadline = time.perf_counter() + 30
    while burst['seen'] < burst_n and time.perf_counter() < deadline:
        time.sleep(0.1)
    elapsed = (burst['last'] or time.perf_counter()) - t0

    result['burst'] = {
        'sent': burst_n,
        'received_cross_instance': burst['seen'],
        'elapsed_s': round(elapsed, 2),
        'rate_per_s': round(burst['seen'] / elapsed, 1) if elapsed > 0 else None,
        'loss': burst_n - burst['seen'],
    }
    log(f"burst {burst['seen']}/{burst_n} in {elapsed:.2f}s "
        f"({result['burst']['rate_per_s']}/s)")

    # ---- persistence ----
    try:
        res = session_a.get(f'{APP_A}/api/messages/1?limit=1000', timeout=10)
        result['persisted_messages'] = len(res.json().get('messages', []))
    except Exception as exc:
        result['persisted_messages'] = f'error: {exc}'

    for client in (sender, receiver_cross, receiver_same):
        client.disconnect()
    return result


def measure_unauthenticated():
    """A Socket.IO client with no session cookie must be rejected (FR9)."""
    client = socketio.Client(reconnection=False)
    try:
        client.connect(APP_A, transports=['websocket'], wait_timeout=10)
        client.disconnect()
        return {'rejected': False, 'note': 'connection was accepted — FR9 NOT met'}
    except Exception as exc:
        return {'rejected': True, 'error_type': type(exc).__name__}


def measure_failure():
    """Probe behaviour, connection survival and delivery with Redis stopped."""
    container = redis_container_name()
    cookie_a, _ = login(APP_A, 'probe_sender')
    cookie_b, _ = login(APP_B, 'probe_receiver')
    cookie_c, _ = login(APP_A, 'probe_baseline')

    seen = {'cross': 0, 'same': 0}
    disconnects = {'sender': False, 'cross': False, 'same': False}

    def counter(bucket):
        def handler(data):
            if data.get('content', '').startswith('outage:'):
                seen[bucket] += 1
        return handler

    sender = connect(APP_A, cookie_a)
    receiver_cross = connect(APP_B, cookie_b, counter('cross'))
    receiver_same = connect(APP_A, cookie_c, counter('same'))

    for name, client in (('sender', sender), ('cross', receiver_cross),
                         ('same', receiver_same)):
        client.on('disconnect', (lambda n: lambda: disconnects.__setitem__(n, True))(name))

    before = {'app_a': probe_health(APP_A), 'app_b': probe_health(APP_B)}
    log(f'stopping {container}')
    docker('stop', container)
    time.sleep(5)

    during = {'app_a': probe_health(APP_A), 'app_b': probe_health(APP_B)}

    sent_ok, send_errors = 0, []
    for i in range(10):
        try:
            sender.emit('message', {'message': f'outage:{i}', 'room': ROOM})
            sent_ok += 1
        except Exception as exc:
            send_errors.append(type(exc).__name__)
        time.sleep(0.3)
    time.sleep(3)

    log(f'starting {container}')
    docker('start', container)
    time.sleep(10)
    after = {'app_a': probe_health(APP_A), 'app_b': probe_health(APP_B)}

    for client in (sender, receiver_cross, receiver_same):
        try:
            client.disconnect()
        except Exception:
            pass

    return {
        'probes_before_outage': before,
        'probes_during_outage': during,
        'probes_after_recovery': after,
        'websocket_clients_dropped': disconnects,
        'messages_attempted': 10,
        'messages_accepted_by_client': sent_ok,
        'send_errors': send_errors,
        'delivered_same_instance': seen['same'],
        'delivered_cross_instance': seen['cross'],
    }


def measure_recovery(outage_s):
    """
    D8: after Redis returns, how long does /ready report 200 while
    cross-instance delivery is still not working?

    Clients are dropped during the outage, so this reconnects a fresh pair on
    each attempt and asks the only question that matters to a user: when does a
    message sent on one instance reach the other again?
    """
    container = redis_container_name()
    cookie_a, _ = login(APP_A, 'probe_sender')
    cookie_b, _ = login(APP_B, 'probe_receiver')

    log(f'stopping {container} for {outage_s}s')
    docker('stop', container)
    time.sleep(outage_s)

    log('restarting; polling /ready and the delivery path')
    docker('start', container)
    t_restart = time.perf_counter()

    ready_at = None
    delivered_at = None
    deadline = t_restart + 120
    attempt = 0

    while time.perf_counter() < deadline and (ready_at is None or delivered_at is None):
        if ready_at is None:
            try:
                if requests.get(APP_A + '/ready', timeout=25).status_code == 200:
                    ready_at = time.perf_counter()
                    log(f'  /ready 200 at t+{ready_at - t_restart:.1f}s')
            except Exception:
                pass

        if delivered_at is None:
            got = {'hit': False}

            def handler(data):
                if data.get('content', '').startswith('recover:'):
                    got['hit'] = True

            sender = receiver = None
            try:
                receiver = connect(APP_B, cookie_b, handler)
                sender = connect(APP_A, cookie_a)
                sender.emit('message', {'message': f'recover:{attempt}', 'room': ROOM})
                waited = time.perf_counter() + 4
                while not got['hit'] and time.perf_counter() < waited:
                    time.sleep(0.2)
                if got['hit']:
                    delivered_at = time.perf_counter()
                    log(f'  delivery resumed at t+{delivered_at - t_restart:.1f}s')
            except Exception:
                pass
            finally:
                for client in (sender, receiver):
                    try:
                        if client:
                            client.disconnect()
                    except Exception:
                        pass
            attempt += 1
        time.sleep(1)

    window = None
    if ready_at and delivered_at:
        window = round(delivered_at - ready_at, 2)

    return {
        'outage_s': outage_s,
        'ready_200_after_restart_s': round(ready_at - t_restart, 2) if ready_at else None,
        'delivery_resumed_after_restart_s': (
            round(delivered_at - t_restart, 2) if delivered_at else None),
        'window_s': window,
        'note': ('positive window = /ready reported 200 while cross-instance '
                 'delivery was still broken (defect D8)'),
    }


# ------------------------------------------------------------------- main --
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['latency', 'failure', 'recovery', 'all'])
    parser.add_argument('--probes', type=int, default=30)
    parser.add_argument('--outage', type=int, default=45)
    parser.add_argument('--out', default=RESULTS)
    args = parser.parse_args()

    for url in (APP_A, APP_B):
        try:
            requests.get(url + '/health', timeout=5)
        except Exception:
            sys.exit(f'{url} is not responding — is docker compose up?')

    results = {
        'run_at': datetime.now().isoformat(timespec='seconds'),
        'app_a': APP_A, 'app_b': APP_B,
    }

    if args.phase in ('latency', 'all'):
        print('\n[1] latency, burst, persistence')
        results['latency'] = measure_latency(args.probes)
        print('\n[2] unauthenticated WebSocket (FR9)')
        results['unauthenticated'] = measure_unauthenticated()
        log(f"rejected: {results['unauthenticated']['rejected']}")

    if args.phase in ('failure', 'all'):
        print('\n[3] behaviour with Redis stopped')
        results['failure'] = measure_failure()

    if args.phase in ('recovery', 'all'):
        print('\n[4] D8 — recovery window')
        results['recovery'] = measure_recovery(args.outage)

    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump(results, handle, indent=2)
    print(f'\nresults written to {args.out}')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
