// Chat application state
let sessionId = localStorage.getItem('claude_session_id') || null;
let conversationId = localStorage.getItem('claude_conv_id') || 'default';
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateSessionInfo();
    loadSessions();

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    resetBtn.addEventListener('click', resetConversation);
    sessionSelect.addEventListener('change', switchSession);

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
        // Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                conv_id: conversationId
            })
        });

        if (response.status === 401) {
            // Auth required - browser will handle basic auth prompt
            window.location.reload();
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
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

async function resetConversation() {
    if (!confirm('Start a new conversation? This will clear the current session.')) {
        return;
    }

    try {
        const response = await fetch(`/api/reset?conv_id=${conversationId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to reset session');
        }

        // Clear local state
        sessionId = null;
        localStorage.removeItem('claude_session_id');
        turnCount = 0;
        totalCost = 0;

        // Clear UI
        chatContainer.innerHTML = `
            <div class="welcome-message">
                <h2>New Conversation Started</h2>
                <p>Send a message to interact with Claude Code.</p>
            </div>
        `;
        localStorage.removeItem('chat_history');

        updateStats();
        updateSessionInfo();

    } catch (error) {
        console.error('Error resetting conversation:', error);
        alert('Failed to reset conversation: ' + error.message);
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
        const response = await fetch('/api/sessions');

        if (!response.ok) {
            console.error('Failed to load sessions');
            return;
        }

        const sessions = await response.json();

        // Clear existing options except "New Session"
        sessionSelect.innerHTML = '<option value="">New Session</option>';

        // Add session options
        Object.entries(sessions).forEach(([convId, session]) => {
            const option = document.createElement('option');
            option.value = convId;

            const lastMsg = session.last_message || 'No messages';
            const preview = lastMsg.length > 40 ? lastMsg.substring(0, 40) + '...' : lastMsg;
            const turns = session.turn_count || 0;

            option.textContent = `${convId} (${turns} turns) - ${preview}`;
            option.title = `Last message: ${lastMsg}\nTurns: ${turns}\nLast active: ${session.last_message_at}`;

            // Select current conversation
            if (convId === conversationId) {
                option.selected = true;
            }

            sessionSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function switchSession() {
    const selectedConvId = sessionSelect.value;

    if (!selectedConvId) {
        // New session
        resetConversation();
        return;
    }

    // Switch to selected conversation
    conversationId = selectedConvId;
    localStorage.setItem('claude_conv_id', conversationId);

    // Clear current chat
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Switched to: ${conversationId}</h2>
            <p>Send a message to continue this conversation.</p>
        </div>
    `;
    localStorage.removeItem('chat_history');

    // Note: We don't have the session_id for this conversation yet
    // It will be loaded when we send the first message
    sessionId = null;
    localStorage.removeItem('claude_session_id');

    updateStats();
    updateSessionInfo();
}
