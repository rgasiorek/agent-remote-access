// Chat application state
const AGENT_API_URL = 'http://localhost:8001';
let sessionId = null;  // Don't auto-load from localStorage - user must select from dropdown
let totalCost = 0;
let turnCount = 0;

// DOM elements
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const resetBtn = document.getElementById('reset-btn');
const sessionInfo = document.getElementById('session-info');
const sessionSelect = document.getElementById('session-select');
const turnCountEl = document.getElementById('turn-count');
const totalCostEl = document.getElementById('total-cost');

// Get auth credentials from localStorage or prompt
let authCredentials = localStorage.getItem('auth_credentials');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateSessionInfo();
    loadSessions();

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    resetBtn.addEventListener('click', resetConversation);
    sessionSelect.addEventListener('change', switchSession);

    // Reload sessions when dropdown is opened
    sessionSelect.addEventListener('focus', loadSessions);
    sessionSelect.addEventListener('mousedown', loadSessions);

    // Send on Enter (Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Load conversation history from localStorage
    loadChatHistory();
});

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

async function sendMessage() {
    const message = messageInput.value.trim();

    if (!message) return;

    // Disable input while sending
    setInputState(false);

    // Add user message to chat
    addMessage('user', message);

    // Clear input
    messageInput.value = '';

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
            // Show error
            addMessage('error', `Error: ${data.error || 'Unknown error occurred'}`);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        addMessage('error', `Failed to send message: ${error.message}`);
    } finally {
        setInputState(true);
        messageInput.focus();
    }
}

function resetConversation() {
    if (!confirm('Start a new conversation? This will clear the current session.')) {
        return;
    }

    // Clear local state
    sessionId = null;
    localStorage.removeItem('claude_session_id');
    turnCount = 0;
    totalCost = 0;

    // Clear dropdown selection
    sessionSelect.value = '';

    // Clear UI
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <h2>New Conversation</h2>
            <p>Send a message to start a new conversation with Claude Code.</p>
        </div>
    `;
    localStorage.removeItem('chat_history');

    updateStats();
    updateSessionInfo();
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

function setInputState(enabled) {
    messageInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
    sendBtn.textContent = enabled ? 'Send' : 'Sending...';
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
                <p>Choose a session from the dropdown above to continue, or send a message to start a new one.</p>
            </div>
        `;
        updateStats();
        updateSessionInfo();
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
