// Interior Design Agent - Frontend JavaScript

// Check authentication
const getAuthenticatedUser = () => {
    const userData = localStorage.getItem('authenticated_user');
    if (!userData) {
        // Redirect to login page
        window.location.href = '/login';
        return null;
    }
    try {
        return JSON.parse(userData);
    } catch (e) {
        console.error('Failed to parse user data:', e);
        localStorage.removeItem('authenticated_user');
        window.location.href = '/login';
        return null;
    }
};

const AUTHENTICATED_USER = getAuthenticatedUser();
if (!AUTHENTICATED_USER) {
    // Redirect happened
    throw new Error('Not authenticated');
}

const USER_ID = AUTHENTICATED_USER.id;

// Generate a session ID for this browser session
const SESSION_ID = 'session-' + Math.random().toString(36).substr(2, 9);

// Current room ID
let currentRoomId = null;

// Track pending design selections (versions waiting for user to select or reject)
let pendingSelections = new Set();

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeChatForm();
    loadUserRooms();
    loadUserPreferences();
    updateChatInputState();
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

            // Debug logging
            console.log('Chat response:', data);
            console.log('Images:', data.images);
            console.log('Version ID:', data.design_version_id);
            console.log('Room ID:', data.room_id);

            // Update current room BEFORE adding message to chat
            if (data.room_id && data.room_id !== currentRoomId) {
                currentRoomId = data.room_id;
            }

            // Remove loading message
            loadingMsg.remove();

            // Add agent response (now with correct currentRoomId)
            addMessageToChat(data.message, 'agent', data.images, data.design_version_id, data.room_id);

            // Reload rooms and design history
            if (data.room_id) {
                await loadUserRooms();
                await loadDesignHistory(data.room_id);
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
function addMessageToChat(message, role, images = [], versionId = null, roomId = null) {
    console.log('addMessageToChat called with:', { role, imagesLength: images?.length, versionId, roomId });

    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    let content = `<div class="message-content">`;

    if (role === 'user') {
        content += `<strong>You:</strong> ${escapeHtml(message)}`;
    } else if (role === 'system') {
        content += escapeHtml(message);
    } else {
        // Render markdown for agent messages
        const renderedMarkdown = marked.parse(message);
        content += `<strong>Designer:</strong><div class="markdown-content">${renderedMarkdown}</div>`;
    }

    content += `</div>`;

    // Add images if present with Select/Reject buttons
    if (images && images.length > 0 && versionId && roomId) {
        // Add this version to pending selections
        pendingSelections.add(versionId);

        content += `<div class="design-images" data-version-id="${versionId}" data-room-id="${roomId}">`;
        images.forEach(imageData => {
            content += `<div class="design-image-container">
                <div class="design-image">
                    <img src="${imageData.url}" alt="Design visualization" />
                </div>
                <div class="image-actions">
                    <button class="btn-select" onclick="selectImage('${roomId}', '${versionId}', '${imageData.id}')">
                        👍 Select This Design
                    </button>
                </div>
            </div>`;
        });

        // Add a single "Reject All" button for the entire version
        content += `
            <div class="version-actions">
                <button class="btn-reject-all" onclick="rejectDesign('${roomId}', '${versionId}')">
                    👎 Reject All Designs
                </button>
            </div>
        `;

        content += `</div>`;

        // Update chat input state
        setTimeout(() => updateChatInputState(), 100);
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

        historyDiv.innerHTML = data.versions.map(version => {
            const images = data.images[version.id] || [];
            const hasImages = images.length > 0;

            return `
                <div class="design-version-card ${version.selected ? 'selected' : ''} ${version.rejected ? 'rejected' : ''}">
                    <div class="version-header">
                        <strong>Version ${version.version_number}</strong>
                        ${version.selected ? '<span class="status-badge selected-badge">✓ Selected</span>' : ''}
                        ${version.rejected ? '<span class="status-badge rejected-badge">✗ Rejected</span>' : ''}
                    </div>

                    <div class="version-description">
                        ${version.description.substring(0, 120)}${version.description.length > 120 ? '...' : ''}
                    </div>

                    ${hasImages ? `
                        <div class="version-images">
                            ${images.map(img => `
                                <div class="image-thumb ${img.selected ? 'selected-image' : ''}" onclick="openImageModal('${img.image_url}', 'Design Version ${version.version_number}')">
                                    <img src="${img.image_url}" alt="Design variation" />
                                    ${img.selected ? '<div class="selected-overlay">✓</div>' : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

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

// Select a specific image from a design
async function selectImage(roomId, versionId, imageId) {
    try {
        const response = await fetch(`/api/rooms/${roomId}/designs/${versionId}/select?user_id=${USER_ID}&image_id=${imageId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error('Failed to select design');
        }

        // Remove from pending selections
        pendingSelections.delete(versionId);

        // Hide selection buttons for this version
        hideSelectionButtons(versionId);

        // Reload design history and preferences
        await loadDesignHistory(roomId);
        await loadUserPreferences();
        addMessageToChat('Design selected! Your preferences have been updated.', 'system');

        // Update chat input state
        updateChatInputState();

    } catch (error) {
        console.error('Error selecting design:', error);
        addMessageToChat('Failed to select design. Please try again.', 'system');
    }
}

// Legacy function for compatibility
async function selectDesign(roomId, versionId) {
    return selectImage(roomId, versionId, null);
}

// Reject a design
async function rejectDesign(roomId, versionId) {
    try {
        const feedback = encodeURIComponent("I don't like this design");
        const response = await fetch(`/api/rooms/${roomId}/designs/${versionId}/reject?user_id=${USER_ID}&feedback=${feedback}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error('Failed to reject design');
        }

        // Remove from pending selections
        pendingSelections.delete(versionId);

        // Hide selection buttons for this version
        hideSelectionButtons(versionId);

        // Reload design history and preferences
        await loadDesignHistory(roomId);
        await loadUserPreferences();
        addMessageToChat('All designs rejected. Your preferences have been updated.', 'system');

        // Update chat input state
        updateChatInputState();

    } catch (error) {
        console.error('Error rejecting design:', error);
        addMessageToChat('Failed to reject design. Please try again.', 'system');
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Hide selection buttons for a specific version
function hideSelectionButtons(versionId) {
    const designImagesDiv = document.querySelector(`.design-images[data-version-id="${versionId}"]`);
    if (designImagesDiv) {
        // Hide all select buttons
        designImagesDiv.querySelectorAll('.btn-select').forEach(btn => {
            btn.style.display = 'none';
        });
        // Hide the reject all button
        const rejectBtn = designImagesDiv.querySelector('.btn-reject-all');
        if (rejectBtn) {
            rejectBtn.style.display = 'none';
        }
    }
}

// Update chat input state based on pending selections
function updateChatInputState() {
    const input = document.getElementById('message-input');
    const submitBtn = document.querySelector('.send-button');

    if (pendingSelections.size > 0) {
        // Disable input when there are pending selections
        input.disabled = true;
        input.placeholder = 'Please select or reject a design to continue...';
        if (submitBtn) submitBtn.disabled = true;
    } else {
        // Enable input when no pending selections
        input.disabled = false;
        input.placeholder = 'Describe the room you want to design...';
        if (submitBtn) submitBtn.disabled = false;
    }
}

// Logout function
function logout() {
    localStorage.removeItem('authenticated_user');
    window.location.href = '/login';
}

// Image Modal functions
function openImageModal(imageSrc, caption) {
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');
    const modalCaption = document.getElementById('modalCaption');

    modal.style.display = 'block';
    modalImg.src = imageSrc;
    modalCaption.innerHTML = caption || 'Design Image';
}

function closeImageModal() {
    const modal = document.getElementById('imageModal');
    modal.style.display = 'none';
}

// Close modal when clicking outside the image
window.onclick = function(event) {
    const modal = document.getElementById('imageModal');
    if (event.target == modal) {
        closeImageModal();
    }
}

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeImageModal();
    }
});
