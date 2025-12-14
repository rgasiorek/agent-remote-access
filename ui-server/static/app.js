// Chat application state
const AGENT_API_URL = 'http://localhost:8001';
const UI_API_URL = 'http://localhost:8000';
let sessionId = null;  // Don't auto-load - user must select from dropdown
let totalCost = 0;
let turnCount = 0;
let projectPath = '';

// DOM elements
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const sessionInfo = document.getElementById('session-info');
const sessionSelect = document.getElementById('session-select');
const turnCountEl = document.getElementById('turn-count');
const totalCostEl = document.getElementById('total-cost');
const projectInfoEl = document.getElementById('project-info');

// Get auth credentials from localStorage or prompt
let authCredentials = localStorage.getItem('auth_credentials');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load config first
    await loadConfig();

    updateSessionInfo();
    loadSessions();
    updateSendButtonState();

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    sessionSelect.addEventListener('change', switchSession);

    // Reload sessions when dropdown is opened
    sessionSelect.addEventListener('focus', loadSessions);
    sessionSelect.addEventListener('mousedown', loadSessions);

    // Send on Enter (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                sendMessage();
            }
        }
    });
});

async function loadConfig() {
    try {
        const response = await fetch(`${UI_API_URL}/api/config`);
        if (response.ok) {
            const config = await response.json();
            projectPath = config.project_path;
            if (projectInfoEl) {
                projectInfoEl.textContent = projectPath;
            }
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

function getAuthHeaders() {
    if (!authCredentials) {
        const username = prompt('Enter username:');
        const password = prompt('Enter password:');
        if (username && password) {
            authCredentials = btoa(`${username}:${password}`);
            localStorage.setItem('auth_credentials', authCredentials);
        }
    }
    return {
        'Authorization': `Basic ${authCredentials}`,
        'Content-Type': 'application/json'
    };
}

function updateSendButtonState() {
    // Disable send button if no session selected
    const hasSession = sessionId !== null && sessionId !== '';
    sendBtn.disabled = !hasSession;
    messageInput.disabled = !hasSession;

    if (!hasSession) {
        messageInput.placeholder = 'Select a session first...';
    } else {
        messageInput.placeholder = 'Message your AI agent...';
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();

    if (!message) return;

    // Check if session is selected
    if (!sessionId) {
        alert('Please select a session first');
        return;
    }

    // Disable input while sending
    setInputState(false, 'Sending...');

    // Add user message to chat
    addMessage('user', message);

    // Clear input
    messageInput.value = '';

    // Add status message
    const statusMsg = addStatusMessage('Sending message to agent...');

    try {
        // Send to Agent API
        const response = await fetch(`${AGENT_API_URL}/api/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        // Update status - agent received the message
        updateStatusMessage(statusMsg, '✓ Agent received message, thinking...');

        if (response.status === 401) {
            // Auth failed - clear credentials and retry
            localStorage.removeItem('auth_credentials');
            authCredentials = null;
            alert('Authentication failed. Please enter your credentials again.');
            window.location.reload();
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            // Remove status message
            removeStatusMessage(statusMsg);

            // Update session
            sessionId = data.session_id;
            localStorage.setItem('claude_session_id', sessionId);

            // Update stats
            turnCount = data.turns;
            totalCost += data.cost;
            updateStats();
            updateSessionInfo();

            // Add Claude's response
            addMessage('assistant', data.response);
        } else {
            // Update status to show error
            updateStatusMessage(statusMsg, '✗ Error: ' + (data.error || 'Unknown error occurred'), 'error');

            // Also add error message
            addMessage('error', `Error: ${data.error || 'Unknown error occurred'}`);

            // Remove status after a delay
            setTimeout(() => removeStatusMessage(statusMsg), 3000);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        updateStatusMessage(statusMsg, '✗ Failed to send message', 'error');
        addMessage('error', `Failed to send message: ${error.message}`);
        setTimeout(() => removeStatusMessage(statusMsg), 3000);
    } finally {
        setInputState(true, 'Send');
        updateSendButtonState();
        if (!sendBtn.disabled) {
            messageInput.focus();
        }
    }
}

function addMessage(role, content) {
    // Remove welcome message if present
    const welcome = chatContainer.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'message-role';
    roleLabel.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'Claude' : 'Error';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(roleLabel);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Save to localStorage
    saveChatHistory();
}

function updateStats() {
    turnCountEl.textContent = turnCount;
    totalCostEl.textContent = `$${totalCost.toFixed(4)}`;
}

function updateSessionInfo() {
    if (sessionId) {
        sessionInfo.textContent = `Session: ${sessionId.substring(0, 8)}...`;
        sessionInfo.className = 'info-badge active';
    } else {
        sessionInfo.textContent = 'No active session';
        sessionInfo.className = 'info-badge';
    }
}

function setInputState(enabled, buttonText = null) {
    messageInput.disabled = !enabled;
    sendBtn.disabled = !enabled;

    if (buttonText) {
        sendBtn.innerHTML = `<span class="btn-icon">→</span><span class="btn-text">${buttonText}</span>`;
    } else {
        const text = enabled ? 'Send' : 'Sending...';
        const icon = enabled ? '→' : '⋯';
        sendBtn.innerHTML = `<span class="btn-icon">${icon}</span><span class="btn-text">${text}</span>`;
    }
}

function addStatusMessage(text, type = 'info') {
    const statusDiv = document.createElement('div');
    statusDiv.className = `status-message status-${type}`;
    statusDiv.textContent = text;
    chatContainer.appendChild(statusDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return statusDiv;
}

function updateStatusMessage(statusDiv, text, type = 'info') {
    if (statusDiv && statusDiv.parentNode) {
        statusDiv.textContent = text;
        statusDiv.className = `status-message status-${type}`;
    }
}

function removeStatusMessage(statusDiv) {
    if (statusDiv && statusDiv.parentNode) {
        statusDiv.remove();
    }
}

function saveChatHistory() {
    const messages = Array.from(chatContainer.querySelectorAll('.message')).map(msg => ({
        role: msg.classList.contains('message-user') ? 'user' :
              msg.classList.contains('message-assistant') ? 'assistant' : 'error',
        content: msg.querySelector('.message-content').textContent
    }));
    localStorage.setItem('chat_history', JSON.stringify(messages));
}

function loadChatHistory() {
    const history = localStorage.getItem('chat_history');
    if (!history) return;

    try {
        const messages = JSON.parse(history);
        if (messages.length > 0) {
            // Remove welcome message
            const welcome = chatContainer.querySelector('.welcome-message');
            if (welcome) welcome.remove();

            // Add all messages
            messages.forEach(msg => {
                addMessageWithoutSave(msg.role, msg.content);
            });
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

function addMessageWithoutSave(role, content) {
    const welcome = chatContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'message-role';
    roleLabel.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'Claude' : 'Error';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    messageDiv.appendChild(roleLabel);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
}

async function loadSessions() {
    try {
        const response = await fetch(`${AGENT_API_URL}/api/sessions`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            console.error('Failed to load sessions');
            return;
        }

        const data = await response.json();
        const sessions = data.sessions || [];

        // Remember current selection to restore after rebuild
        const currentSelection = sessionSelect.value;

        // Rebuild dropdown - start empty
        sessionSelect.innerHTML = '<option value="">Select a session...</option>';

        sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.session_id;

            // Show FULL session ID + preview of first message
            const display = session.display || 'No description';
            const preview = display.length > 40 ? display.substring(0, 40) + '...' : display;

            option.textContent = `${session.session_id} - ${preview}`;
            option.title = `${display}\nProject: ${session.project || 'N/A'}`;

            sessionSelect.appendChild(option);
        });

        // Restore selection if it still exists in the list
        if (currentSelection) {
            sessionSelect.value = currentSelection;
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function switchSession() {
    const selectedSessionId = sessionSelect.value;

    if (!selectedSessionId) {
        // No session selected - clear everything
        sessionId = null;
        turnCount = 0;
        totalCost = 0;
        chatContainer.innerHTML = `
            <div class="welcome-message">
                <h2>Select a Session</h2>
                <p>Choose a session from the dropdown to continue an existing conversation.</p>
                <p class="project-info" id="project-info">${projectPath}</p>
            </div>
        `;
        updateStats();
        updateSessionInfo();
        updateSendButtonState();
        return;
    }

    // Switch to selected session
    sessionId = selectedSessionId;
    localStorage.setItem('claude_session_id', sessionId);

    // Clear current chat
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Switched to session: ${sessionId.substring(0, 8)}...</h2>
            <p>Send a message to resume this conversation.</p>
        </div>
    `;
    localStorage.removeItem('chat_history');

    // Reset stats (we don't track them across sessions)
    turnCount = 0;
    totalCost = 0;
    updateStats();
    updateSessionInfo();
}
