// Interior Design Agent - Frontend JavaScript

// Generate a user ID (in production, this would be from authentication)
const USER_ID = localStorage.getItem('user_id') || (() => {
    const id = 'user-' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('user_id', id);
    return id;
})();

// Generate a session ID for this browser session
const SESSION_ID = 'session-' + Math.random().toString(36).substr(2, 9);

// Current room ID
let currentRoomId = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeChatForm();
    loadUserRooms();
    loadUserPreferences();
});

// Initialize chat form submission
function initializeChatForm() {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = input.value.trim();
        if (!message) return;

        // Clear input
        input.value = '';

        // Add user message to chat
        addMessageToChat(message, 'user');

        // Show loading indicator
        const loadingMsg = addLoadingMessage();

        try {
            // Send message to API
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: USER_ID,
                    session_id: SESSION_ID,
                    room_id: currentRoomId,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            const data = await response.json();

            // Remove loading message
            loadingMsg.remove();

            // Add agent response
            addMessageToChat(data.message, 'agent', data.images);

            // Update current room
            if (data.room_id && data.room_id !== currentRoomId) {
                currentRoomId = data.room_id;
                await loadUserRooms();
                await loadDesignHistory(currentRoomId);
            }

            // Reload preferences (they may have been learned)
            await loadUserPreferences();

        } catch (error) {
            console.error('Error:', error);
            loadingMsg.remove();
            addMessageToChat('Sorry, there was an error processing your message.', 'agent');
        }
    });
}

// Add message to chat
function addMessageToChat(message, role, images = []) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    let content = `<div class="message-content">`;

    if (role === 'user') {
        content += `<strong>You:</strong> ${escapeHtml(message)}`;
    } else {
        content += `<strong>Designer:</strong> ${escapeHtml(message)}`;
    }

    content += `</div>`;

    // Add images if present
    if (images && images.length > 0) {
        content += `<div class="design-images">`;
        images.forEach(imageUrl => {
            content += `<div class="design-image">
                <img src="${imageUrl}" alt="Design visualization" />
            </div>`;
        });
        content += `</div>`;
    }

    messageDiv.innerHTML = content;
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add loading message
function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message agent-message';
    loadingDiv.innerHTML = `<div class="message-content">
        <strong>Designer:</strong> <span class="loading"></span> Thinking...
    </div>`;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return loadingDiv;
}

// Load user rooms
async function loadUserRooms() {
    try {
        const response = await fetch(`/api/rooms/${USER_ID}`);
        if (!response.ok) throw new Error('Failed to load rooms');

        const data = await response.json();
        const roomsList = document.getElementById('rooms-list');

        if (data.rooms.length === 0) {
            roomsList.innerHTML = '<p class="empty-state">No rooms yet. Start a conversation to create your first room!</p>';
            return;
        }

        roomsList.innerHTML = data.rooms.map(room => `
            <div class="room-item ${room.id === currentRoomId ? 'active' : ''}"
                 onclick="selectRoom('${room.id}', '${room.name}')">
                <div>${room.name}</div>
                <small style="opacity: 0.7;">${room.room_type.replace('_', ' ')}</small>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading rooms:', error);
    }
}

// Select a room
async function selectRoom(roomId, roomName) {
    currentRoomId = roomId;
    await loadUserRooms();
    await loadDesignHistory(roomId);
    addMessageToChat(`Switched to ${roomName}`, 'system');
}

// Load design history for a room
async function loadDesignHistory(roomId) {
    try {
        const response = await fetch(`/api/rooms/${roomId}/designs`);
        if (!response.ok) throw new Error('Failed to load design history');

        const data = await response.json();
        const historyDiv = document.getElementById('design-history');

        if (data.versions.length === 0) {
            historyDiv.innerHTML = '<p class="empty-state">No designs yet for this room</p>';
            return;
        }

        historyDiv.innerHTML = data.versions.map(version => `
            <div class="design-item">
                <div><strong>Version ${version.version_number}</strong> ${version.selected ? '✓' : ''}</div>
                <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
                    ${version.description.substring(0, 100)}...
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading design history:', error);
    }
}

// Load user preferences
async function loadUserPreferences() {
    try {
        const response = await fetch(`/api/preferences/${USER_ID}`);
        if (!response.ok) throw new Error('Failed to load preferences');

        const data = await response.json();
        const prefsList = document.getElementById('preferences-list');

        if (data.preferences.length === 0) {
            prefsList.innerHTML = '<p class="empty-state">Preferences will be learned as you chat</p>';
            return;
        }

        // Group preferences by type
        const grouped = {};
        data.preferences.forEach(pref => {
            if (!grouped[pref.preference_type]) {
                grouped[pref.preference_type] = [];
            }
            grouped[pref.preference_type].push(pref);
        });

        prefsList.innerHTML = Object.entries(grouped).map(([type, prefs]) => {
            const topPref = prefs[0]; // Highest confidence
            return `
                <div class="pref-item">
                    <span class="pref-type">${type}:</span>
                    <span class="pref-value">${topPref.preference_value}</span>
                    <span class="pref-confidence">${(topPref.confidence * 100).toFixed(0)}%</span>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
