/**
 * Three-Tier Chat — Client-Side WebSocket Logic
 * Handles: connection, room switching, message send/receive, history loading
 */

// ======================== State ========================
let socket = null;
let currentRoom = 'general';

// ======================== Initialize ========================
document.addEventListener('DOMContentLoaded', () => {
    connectSocket();
    loadMessages(currentRoom);
    document.getElementById('messageInput').focus();
});

// ======================== WebSocket Connection ========================
function connectSocket() {
    socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => {
        updateStatus('connected');
        socket.emit('join', { room: currentRoom });
    });

    socket.on('disconnect', () => {
        updateStatus('disconnected');
    });

    socket.on('connect_error', () => {
        updateStatus('disconnected');
    });

    // Receive new message (broadcast from server via Redis pub/sub)
    socket.on('new_message', (data) => {
        if (data.room === currentRoom) {
            appendMessage(data);
            scrollToBottom();
        }
    });

    // Status messages (join/leave)
    socket.on('status', (data) => {
        appendStatusMessage(data.msg);
    });
}

// ======================== Room Management ========================
function switchRoom(roomName) {
    if (roomName === currentRoom) return;

    // Leave old room
    socket.emit('leave', { room: currentRoom });

    // Update UI
    document.querySelectorAll('.room-item').forEach(el => el.classList.remove('active'));
    const target = document.querySelector(`.room-item[data-room="${roomName}"]`);
    if (target) target.classList.add('active');

    // Join new room
    currentRoom = roomName;
    document.getElementById('currentRoomTitle').textContent = `# ${roomName}`;
    socket.emit('join', { room: currentRoom });

    // Load message history
    clearMessages();
    loadMessages(currentRoom);
    document.getElementById('messageInput').focus();
}

function toggleNewRoom() {
    const form = document.getElementById('newRoomForm');
    form.style.display = form.style.display === 'none' ? 'flex' : 'none';
    if (form.style.display === 'flex') {
        document.getElementById('newRoomName').focus();
    }
}

function createRoom() {
    const nameInput = document.getElementById('newRoomName');
    const name = nameInput.value.trim().toLowerCase().replace(/\s+/g, '-');

    if (!name || name.length < 2) return;

    fetch('/api/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        // Add room to sidebar
        const roomList = document.getElementById('roomList');
        const div = document.createElement('div');
        div.className = 'room-item';
        div.dataset.room = data.name;
        div.onclick = () => switchRoom(data.name);
        div.innerHTML = `<span class="room-icon">#</span><span class="room-name">${data.name}</span>`;
        roomList.appendChild(div);

        // Switch to new room
        switchRoom(data.name);
        nameInput.value = '';
        toggleNewRoom();
    })
    .catch(err => console.error('Create room error:', err));
}

// ======================== Messages ========================
function sendMessage(e) {
    e.preventDefault();
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    socket.emit('message', {
        message: message,
        room: currentRoom
    });

    input.value = '';
    input.focus();
}

function loadMessages(roomName) {
    const loading = document.getElementById('messagesLoading');
    if (loading) loading.style.display = 'block';

    fetch(`/api/messages/${getRoomId(roomName)}?limit=50`)
        .then(res => res.json())
        .then(data => {
            if (loading) loading.style.display = 'none';
            if (data.messages) {
                data.messages.forEach(msg => appendMessage(msg));
                scrollToBottom();
            }
        })
        .catch(err => {
            if (loading) loading.style.display = 'none';
            console.error('Load messages error:', err);
        });
}

function getRoomId(roomName) {
    // Find room ID from the room list items
    const roomItems = document.querySelectorAll('.room-item');
    let idx = 1;
    for (const item of roomItems) {
        if (item.dataset.room === roomName) return idx;
        idx++;
    }
    return 1; // Default to first room
}

function appendMessage(data) {
    const container = document.getElementById('messagesContainer');
    const loading = document.getElementById('messagesLoading');
    if (loading) loading.style.display = 'none';

    const isOwn = data.username === CURRENT_USER;
    const time = formatTime(data.created_at);

    const div = document.createElement('div');
    div.className = `message ${isOwn ? 'own' : 'other'}`;
    // served_by is present on live messages only (history is not tagged).
    // Two browsers showing different values is direct proof that delivery
    // crossed instances through the Redis backplane.
    const via = data.served_by
        ? `<div class="message-via">via ${escapeHtml(data.served_by)}` +
          `${data.az ? ' · ' + escapeHtml(data.az) : ''}</div>`
        : '';

    div.innerHTML = `
        <div class="message-header">
            <span class="message-author">${escapeHtml(data.username)}</span>
            <span class="message-time">${time}</span>
        </div>
        <div class="message-content">${escapeHtml(data.content)}</div>
        ${via}
    `;

    container.appendChild(div);
}

function appendStatusMessage(text) {
    const container = document.getElementById('messagesContainer');
    const div = document.createElement('div');
    div.className = 'status-message';
    div.textContent = text;
    container.appendChild(div);
    scrollToBottom();
}

function clearMessages() {
    const container = document.getElementById('messagesContainer');
    container.innerHTML = '<div class="messages-loading" id="messagesLoading">Loading messages...</div>';
}

// ======================== UI Helpers ========================
function updateStatus(state) {
    const dot = document.querySelector('.status-dot');
    const text = document.querySelector('.status-text');

    dot.className = 'status-dot';
    if (state === 'connected') {
        dot.classList.add('connected');
        text.textContent = 'Connected';
    } else if (state === 'disconnected') {
        dot.classList.add('disconnected');
        text.textContent = 'Disconnected';
    } else {
        text.textContent = 'Connecting...';
    }
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function formatTime(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Handle Enter key for new room input
document.addEventListener('keydown', (e) => {
    if (e.target.id === 'newRoomName' && e.key === 'Enter') {
        createRoom();
    }
});
