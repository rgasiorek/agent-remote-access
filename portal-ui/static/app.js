// Chat application state
let AGENT_API_URL = '';  // Will be loaded from config
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
const headerPrompt = document.getElementById('header-prompt');

// Get auth credentials from localStorage or prompt
let authCredentials = localStorage.getItem('auth_credentials');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load frontend config first to get agent API URL
    await loadFrontendConfig();

    // Then load project config
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

async function loadFrontendConfig() {
    // All API requests now go through the portal-ui proxy at /api/*
    // This works for both local (direct) and remote (Cloudflare) access
    AGENT_API_URL = window.location.origin;
    console.log('Using portal-ui proxy for API calls, base URL:', AGENT_API_URL);
}

async function loadConfig() {
    console.log('loadConfig: Starting config fetch from', `${AGENT_API_URL}/api/config`);
    try {
        const response = await fetch(`${AGENT_API_URL}/api/config`);
        console.log('loadConfig: Fetch response status:', response.status, response.ok);

        if (response.ok) {
            const config = await response.json();
            console.log('loadConfig: Config received:', config);
            projectPath = config.project_path;

            // Update header prompt with actual project path
            if (headerPrompt && projectPath) {
                const username = getCurrentUsername();
                const promptText = `${username}@agenthost:${projectPath}$`;
                console.log('loadConfig: Updating header to:', promptText);
                headerPrompt.textContent = promptText;
            } else if (headerPrompt) {
                console.error('loadConfig: No project path in config');
                headerPrompt.textContent = 'Error: No project path';
            }

            if (projectInfoEl) {
                projectInfoEl.textContent = `user@agenthost:${projectPath}`;
                // Show the element only if there's content
                if (projectPath) {
                    projectInfoEl.style.display = 'inline-block';
                } else {
                    projectInfoEl.style.display = 'none';
                }
            }
        } else {
            console.error('loadConfig: Bad response status:', response.status);
            if (headerPrompt) {
                headerPrompt.textContent = `Error: HTTP ${response.status}`;
            }
        }
    } catch (error) {
        console.error('loadConfig: Fetch exception:', error, error.message);
        if (headerPrompt) {
            headerPrompt.textContent = `Error: ${error.message || 'Config load failed'}`;
        }
    }
}

function getCurrentUsername() {
    // Try to get username from auth credentials
    if (authCredentials) {
        try {
            const decoded = atob(authCredentials);
            const username = decoded.split(':')[0];
            return username || 'user';
        } catch (e) {
            return 'user';
        }
    }
    return 'user';
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

    // Add user message to chat immediately
    addMessage('user', message);

    // Clear input
    messageInput.value = '';

    // Show AI thinking status immediately
    const statusMsg = addStatusMessage('AI is thinking...');
    setInputState(false, 'AI is thinking...');

    // Track elapsed time and update status message
    const startTime = Date.now();
    let warningShown = false;

    const timeoutWarning = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);

        if (elapsed >= 60 && !warningShown) {
            updateStatusMessage(statusMsg, '⏳ Complex task detected, this may take several minutes...', 'info');
            warningShown = true;
        } else if (elapsed < 60) {
            updateStatusMessage(statusMsg, `AI is thinking... (${elapsed}s)`, 'info');
        } else {
            updateStatusMessage(statusMsg, `⏳ Still processing... (${elapsed}s)`, 'info');
        }
    }, 2000); // Update every 2 seconds

    try {
        // Step 1: Submit async task (RESTful: /api/sessions/{session_id}/chat)
        const effectiveSessionId = sessionId || 'new';
        const submitResponse = await fetch(`${AGENT_API_URL}/api/sessions/${effectiveSessionId}/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                message: message
            })
        });

        if (submitResponse.status === 401) {
            localStorage.removeItem('auth_credentials');
            authCredentials = null;
            alert('Authentication failed. Please enter your credentials again.');
            window.location.reload();
            return;
        }

        if (!submitResponse.ok) {
            const errorData = await submitResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${submitResponse.status}`);
        }

        const submitData = await submitResponse.json();
        const taskId = submitData.task_id;

        // Step 2: Poll for completion every 5 seconds (RESTful: /api/sessions/{session_id}/tasks/{task_id})
        const pollInterval = setInterval(async () => {
            try {
                const statusResponse = await fetch(`${AGENT_API_URL}/api/sessions/${effectiveSessionId}/tasks/${taskId}`, {
                    headers: getAuthHeaders()
                });

                if (!statusResponse.ok) {
                    throw new Error(`Status check failed: ${statusResponse.status}`);
                }

                const statusData = await statusResponse.json();

                if (statusData.status === 'completed') {
                    // Stop polling and timer
                    clearInterval(pollInterval);
                    clearInterval(timeoutWarning);
                    removeStatusMessage(statusMsg);

                    const result = statusData.result;

                    if (result.is_error) {
                        // Handle error response
                        addMessage('error', `Error: ${result.result || 'Unknown error occurred'}`);
                    } else {
                        // Update session
                        sessionId = result.session_id;
                        localStorage.setItem('claude_session_id', sessionId);

                        // Update stats
                        turnCount = result.num_turns || 0;
                        totalCost += result.total_cost_usd || 0;
                        updateStats();
                        updateSessionInfo();

                        // Add Claude's response
                        addMessage('assistant', result.result);
                    }

                    // Step 3: Cleanup task file after rendering (RESTful: DELETE /api/sessions/{session_id}/tasks/{task_id})
                    fetch(`${AGENT_API_URL}/api/sessions/${effectiveSessionId}/tasks/${taskId}`, {
                        method: 'DELETE',
                        headers: getAuthHeaders()
                    }).catch(err => console.warn('Cleanup failed:', err));

                    // Re-enable input
                    setInputState(true, 'Send');
                    updateSendButtonState();
                    if (!sendBtn.disabled) {
                        messageInput.focus();
                    }
                } else if (statusData.status === 'not_found') {
                    // Task not found
                    clearInterval(pollInterval);
                    clearInterval(timeoutWarning);
                    updateStatusMessage(statusMsg, '✗ Task not found', 'error');
                    addMessage('error', 'Task not found. Please try again.');
                    setTimeout(() => removeStatusMessage(statusMsg), 5000);

                    setInputState(true, 'Send');
                    updateSendButtonState();
                }
                // else: status is "processing" - continue polling

            } catch (pollError) {
                console.error('Poll error:', pollError);
                // Continue polling even on transient errors
            }
        }, 5000); // Poll every 5 seconds

    } catch (error) {
        clearInterval(timeoutWarning);
        console.error('Error sending message:', error);

        updateStatusMessage(statusMsg, '✗ Failed to send message', 'error');
        addMessage('error', `Failed to send message: ${error.message}`);

        setTimeout(() => removeStatusMessage(statusMsg), 5000);
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
    console.log('updateSessionInfo called, sessionId:', sessionId);
    if (sessionId) {
        const badgeText = `● ${sessionId.substring(0, 8)}`;
        console.log('Setting badge to:', badgeText);
        sessionInfo.textContent = badgeText;
        sessionInfo.className = 'info-badge active';
    } else {
        console.log('No session, setting badge to: ● no session');
        sessionInfo.textContent = '● no session';
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

        if (sessions.length === 0 && data.hint) {
            // Show hint as disabled option when no sessions found
            const hintOption = document.createElement('option');
            hintOption.disabled = true;
            hintOption.textContent = `💡 ${data.hint}`;
            sessionSelect.appendChild(hintOption);
        }

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
    console.log('switchSession called, selected:', selectedSessionId);

    if (!selectedSessionId) {
        // No session selected - clear everything
        console.log('No session selected, clearing...');
        sessionId = null;
        turnCount = 0;
        totalCost = 0;
        chatContainer.innerHTML = `
            <div class="welcome-message">
                <h2>Select a Session</h2>
                <p>Choose a session from the dropdown to continue an existing conversation.</p>
                ${projectPath ? `<p class="project-info">user@agenthost:${projectPath}</p>` : ''}
            </div>
        `;
        updateStats();
        updateSessionInfo();
        updateSendButtonState();
        return;
    }

    // Switch to selected session
    console.log('Setting sessionId to:', selectedSessionId);
    sessionId = selectedSessionId;

    // Clear current chat
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <h2>Session: ${sessionId.substring(0, 8)}...</h2>
            <p>Send a message to resume this conversation.</p>
            ${projectPath ? `<p class="project-info">user@agenthost:${projectPath}</p>` : ''}
        </div>
    `;

    // Reset stats (we don't track them across sessions)
    turnCount = 0;
    totalCost = 0;
    updateStats();
    updateSessionInfo();
    updateSendButtonState();
    messageInput.focus();
}
