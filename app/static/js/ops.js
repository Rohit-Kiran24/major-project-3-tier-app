/**
 * Ops Console — live telemetry and demo controls.
 *
 * Every value drawn here comes from a real measurement returned by the server.
 * Nothing is animated or invented: if a figure is unavailable (AWS-only data
 * while running locally) the panel says so instead of showing a placeholder.
 */

// ======================== State ========================
const POLL_MS = 3000;
const MAX_POINTS = 200;               // ~10 minutes at 3s
const SERIES_COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4'];

let history = [];                     // [{t, cpus:{id:pct}, count, msgs, db, redis}]
let logLines = [];
let cpuChart = null, trafficChart = null;
let spikeTimer = null;

// ======================== Helpers ========================
function q(id) { return document.getElementById(id); }

function fmtUptime(s) {
    if (s < 60) return s + 's';
    if (s < 3600) return Math.floor(s / 60) + 'm';
    return Math.floor(s / 3600) + 'h' + Math.floor((s % 3600) / 60) + 'm';
}

function addLog(msg, type) {
    const t = new Date().toLocaleTimeString([], {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    logLines.unshift({ t: t, msg: msg, type: type || 'info' });
    if (logLines.length > 80) logLines.pop();
    const el = q('elog');
    if (!el) return;
    el.innerHTML = logLines.map(function (l) {
        return '<div class="el"><span class="el-t">' + l.t + '</span>' +
               '<span class="' + l.type + '">' + escapeHtml(l.msg) + '</span></div>';
    }).join('');
}

function barColor(v) {
    return v > 80 ? 'var(--error)' : v > 60 ? 'var(--warning)' : 'var(--accent)';
}

// ======================== Panel + theme ========================
function toggleOps() {
    const p = q('opsPanel');
    if (p) p.classList.toggle('hidden');
}

function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme');
    const next = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) { /* private mode */ }
    if (cpuChart) { cpuChart.destroy(); cpuChart = null; }
    if (trafficChart) { trafficChart.destroy(); trafficChart = null; }
    initCharts();
    renderCharts();
}

(function restoreTheme() {
    try {
        const t = localStorage.getItem('theme');
        if (t) document.documentElement.setAttribute('data-theme', t);
    } catch (e) { /* ignore */ }
})();

// ======================== Charts ========================
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function initCharts() {
    if (typeof Chart === 'undefined') return;      // CDN blocked: skip silently
    const grid = cssVar('--border') || 'rgba(255,255,255,.08)';
    const text = cssVar('--text-muted') || '#888';

    const base = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: text, boxWidth: 8, font: { size: 9 } } }
        },
        scales: {
            x: { ticks: { color: text, font: { size: 8 }, maxTicksLimit: 5 },
                 grid: { color: grid } }
        }
    };

    const cpuEl = q('cpuChart');
    if (cpuEl) {
        cpuChart = new Chart(cpuEl, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: Object.assign({}, base, {
                scales: {
                    x: base.scales.x,
                    y: {
                        min: 0, max: 100,
                        ticks: { color: text, font: { size: 8 }, callback: function (v) { return v + '%'; } },
                        grid: { color: grid }
                    },
                    y1: {
                        position: 'right', min: 0, max: 4,
                        ticks: { color: text, font: { size: 8 }, stepSize: 1 },
                        grid: { drawOnChartArea: false }
                    }
                }
            })
        });
    }

    const trEl = q('trafficChart');
    if (trEl) {
        trafficChart = new Chart(trEl, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: Object.assign({}, base, {
                scales: {
                    x: base.scales.x,
                    y: { min: 0, ticks: { color: text, font: { size: 8 } }, grid: { color: grid } },
                    y1: { position: 'right', min: 0,
                          ticks: { color: text, font: { size: 8 }, callback: function (v) { return v + 'ms'; } },
                          grid: { drawOnChartArea: false } }
                }
            })
        });
    }
}

function renderCharts() {
    if (!cpuChart || !history.length) return;

    const labels = history.map(function (h) {
        return new Date(h.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });

    // One CPU line per server seen in the window
    const ids = [];
    history.forEach(function (h) {
        Object.keys(h.cpus).forEach(function (id) { if (ids.indexOf(id) === -1) ids.push(id); });
    });

    const datasets = ids.map(function (id, i) {
        return {
            label: id,
            data: history.map(function (h) { return h.cpus[id] !== undefined ? h.cpus[id] : null; }),
            borderColor: SERIES_COLORS[i % SERIES_COLORS.length],
            backgroundColor: 'transparent',
            borderWidth: 1.8, pointRadius: 0, spanGaps: true, tension: .25, yAxisID: 'y'
        };
    });

    // The thresholds the real CloudWatch alarms use
    datasets.push({
        label: 'scale-out 70%', data: labels.map(function () { return 70; }),
        borderColor: '#ef4444', borderDash: [4, 4], borderWidth: 1,
        pointRadius: 0, fill: false, yAxisID: 'y'
    });
    datasets.push({
        label: 'scale-in 30%', data: labels.map(function () { return 30; }),
        borderColor: '#8b8b9e', borderDash: [3, 5], borderWidth: 1,
        pointRadius: 0, fill: false, yAxisID: 'y'
    });
    datasets.push({
        label: 'servers', data: history.map(function (h) { return h.count; }),
        borderColor: '#22c55e', borderWidth: 1.6, pointRadius: 0,
        stepped: true, yAxisID: 'y1'
    });

    cpuChart.data.labels = labels;
    cpuChart.data.datasets = datasets;
    cpuChart.update('none');

    if (trafficChart) {
        trafficChart.data.labels = labels;
        trafficChart.data.datasets = [
            { label: 'msgs/min', data: history.map(function (h) { return h.msgs; }),
              borderColor: '#6366f1', borderWidth: 1.8, pointRadius: 0, tension: .25, yAxisID: 'y' },
            { label: 'DB ms', data: history.map(function (h) { return h.db; }),
              borderColor: '#f59e0b', borderWidth: 1.4, pointRadius: 0, tension: .25, yAxisID: 'y1' },
            { label: 'Redis ms', data: history.map(function (h) { return h.redis; }),
              borderColor: '#06b6d4', borderWidth: 1.4, pointRadius: 0, tension: .25, yAxisID: 'y1' }
        ];
        trafficChart.update('none');
    }
}

// ======================== Polling ========================
async function refresh() {
    let status, cluster;
    try {
        const [sRes, cRes] = await Promise.all([
            fetch('/api/ops/status'), fetch('/api/ops/cluster')
        ]);
        status = await sRes.json();
        cluster = await cRes.json();
    } catch (e) {
        addLog('Telemetry request failed: ' + e.message, 'err');
        return;
    }

    renderStatus(status);
    renderCluster(cluster, status);
    recordHistory(status, cluster);
    renderCharts();
}

function renderStatus(s) {
    const mode = q('opsMode');
    if (mode) {
        mode.textContent = s.mode === 'aws' ? 'AWS LIVE' : 'LOCAL';
        mode.className = 'badge' + (s.mode === 'aws' ? '' : ' warn');
    }

    const n = s.node;
    q('cpuV').textContent = n.cpu + '%';
    q('memV').textContent = n.memory + '%';
    q('cpuB').style.width = n.cpu + '%';
    q('cpuB').style.background = barColor(n.cpu);
    q('memB').style.width = n.memory + '%';
    q('stConns').textContent = n.connections;
    q('stMsgs').textContent = n.msgs_per_min;
    q('stUptime').textContent = fmtUptime(n.uptime_s);

    const d = s.dependencies;
    q('depV').textContent =
        (d.database.ok ? d.database.ms + 'ms' : 'down') + ' / ' +
        (d.redis.ok ? d.redis.ms + 'ms' : 'down');

    setTier('tierData', d.database.ok && d.redis.ok ? 'ok' : 'bad',
            'RDS ' + (d.database.ok ? d.database.ms + 'ms' : 'down') +
            ' · Redis ' + (d.redis.ok ? d.redis.ms + 'ms' : 'down'));

    // Spike countdown on the button
    const btn = q('spikeBtn');
    if (btn) {
        if (s.spike.active) {
            btn.textContent = 'Stop spike (' + s.spike.seconds_left + 's)';
            btn.onclick = doSpikeStop;
        } else {
            btn.textContent = 'Spike load';
            btn.onclick = doSpike;
        }
    }
}

function setTier(id, cls, val) {
    const el = q(id);
    if (!el) return;
    el.className = 'tier ' + cls;
    q(id + 'Val').textContent = val;
}

function renderCluster(c, s) {
    const nodes = c.nodes || [];
    const asg = c.asg || {};
    q('stServers').textContent = nodes.length;

    setTier('tierApp', nodes.length ? 'ok' : 'bad', nodes.length + ' server(s)');

    if (asg.available) {
        setTier('tierWeb', 'ok', 'ASG ' + asg.instances.length + '/' + asg.desired + ' desired');
    } else {
        setTier('tierWeb', 'warn', s.mode === 'aws' ? 'ASG unavailable' : 'AWS only');
    }

    // Merge Redis-reported metrics with AWS lifecycle state where available
    const life = {};
    (asg.instances || []).forEach(function (i) { life[i.instance_id] = i; });

    q('nodeList').innerHTML = nodes.map(function (n) {
        const info = life[n.instance_id];
        const state = info ? info.lifecycle : (n.on_aws ? 'unknown' : 'local');
        const me = n.instance_id === (s.node && s.node.instance_id) ? ' me' : '';
        return '<div class="node ' + state.toLowerCase() + me + '">' +
            '<div class="node-head"><span class="node-name">' + escapeHtml(n.instance_id) + '</span>' +
            '<span class="node-badge">' + escapeHtml(state) + '</span></div>' +
            '<div class="node-meta">' +
            '<span>AZ <b>' + escapeHtml(n.az) + '</b></span>' +
            '<span>CPU <b>' + n.cpu + '%</b></span>' +
            '<span>Conn <b>' + n.connections + '</b></span>' +
            (n.spiking ? '<span><b>spiking</b></span>' : '') +
            '</div></div>';
    }).join('');

    // Scaling timeline: real ASG activity, plus alarm state
    const tl = q('timeline');
    if (asg.available) {
        const alarms = (asg.alarms || []).map(function (a) {
            return '<div class="tl"><span class="tl-t">alarm</span><span class="' +
                (a.state === 'ALARM' ? 'warn' : 'ok') + '">' +
                escapeHtml(a.name) + ': ' + a.state + '</span></div>';
        }).join('');
        const acts = (asg.activities || []).slice(0, 6).map(function (a) {
            return '<div class="tl"><span class="tl-t">' +
                new Date(a.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
                '</span><span>' + escapeHtml(a.description) + '</span></div>';
        }).join('');
        tl.innerHTML = alarms + acts || '<div class="dim">No scaling activity yet</div>';
    } else {
        tl.innerHTML = '<div class="dim">' + escapeHtml(asg.reason || 'AWS only') + '</div>';
    }
}

function recordHistory(s, c) {
    const cpus = {};
    (c.nodes || []).forEach(function (n) { cpus[n.instance_id] = n.cpu; });
    history.push({
        t: Date.now(),
        cpus: cpus,
        count: (c.nodes || []).length,
        msgs: s.node.msgs_per_min,
        db: s.dependencies.database.ok ? s.dependencies.database.ms : null,
        redis: s.dependencies.redis.ok ? s.dependencies.redis.ms : null
    });
    if (history.length > MAX_POINTS) history.shift();
}

// ======================== Controls ========================
async function post(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
    });
    const data = await res.json().catch(function () { return {}; });
    return { ok: res.ok, status: res.status, data: data };
}

async function doSpike() {
    const mins = parseFloat(q('spikeMins').value);
    addLog('Spiking every server for ' + mins + ' min...', 'warn');
    const r = await post('/api/ops/spike', { minutes: mins });
    if (!r.ok) { addLog('Spike failed: ' + (r.data.error || r.status), 'err'); return; }
    addLog('Spike running' + (r.data.cluster_wide ? ' cluster-wide' : ' on this server only'), 'warn');
    if (!r.data.cluster_wide) {
        addLog('Redis unreachable: other servers were not loaded, so the ASG average may stay below 70%', 'warn');
    }
    refresh();
}

async function doSpikeStop() {
    const r = await post('/api/ops/spike/stop');
    addLog(r.ok ? 'Spike stopped' : 'Stop failed', r.ok ? 'ok' : 'err');
    refresh();
}

async function doScale(delta) {
    addLog('Requesting desired capacity ' + (delta > 0 ? '+' : '') + delta + '...', 'info');
    const r = await post('/api/ops/scale', { delta: delta });
    addLog(r.ok ? 'Desired capacity now ' + r.data.desired
                : 'Scale failed: ' + (r.data.error || r.status), r.ok ? 'ok' : 'err');
}

async function doHeal() {
    if (!confirm('Mark this server unhealthy? The Auto Scaling Group will terminate and replace it.')) return;
    addLog('Marking this server unhealthy...', 'warn');
    const r = await post('/api/ops/heal', {});
    addLog(r.ok ? 'Marked ' + r.data.instance_id + ' unhealthy; ASG will replace it'
                : 'Self-heal failed: ' + (r.data.error || r.status), r.ok ? 'ok' : 'err');
}

async function doBurst() {
    const count = parseInt(q('burstCount').value, 10);
    addLog('Writing ' + count + ' messages...', 'info');
    const r = await post('/api/ops/burst', { count: count, room: currentRoom });
    if (!r.ok) { addLog('Burst failed: ' + (r.data.error || r.status), 'err'); return; }
    addLog(r.data.count + ' messages in ' + r.data.write_ms + 'ms (' +
           r.data.rate_per_s + '/s, ' + r.data.per_message_ms + 'ms each)', 'ok');
}

// ======================== Start ========================
document.addEventListener('DOMContentLoaded', function () {
    initCharts();
    addLog('Ops Console connected', 'info');
    refresh();
    setInterval(refresh, POLL_MS);
});
