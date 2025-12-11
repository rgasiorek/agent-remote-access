# Architecture Overview

## Two-Server Design

The system now uses two separate FastAPI servers running on the host (no Docker required for testing):

```
┌─────────────────┐
│   Browser       │
│  (localhost)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  UI Server      │  Port 8000
│  (FastAPI)      │  - Serves HTML/JS/CSS
│                 │  - No auth required
└────────┬────────┘
         │ AJAX calls
         ↓
┌─────────────────┐
│  Agent API      │  Port 8001
│  (FastAPI)      │  - HTTP Basic Auth
│                 │  - /api/chat endpoint
│                 │  - /api/sessions endpoint
└────────┬────────┘
         │ subprocess
         ↓
┌─────────────────┐
│  Claude CLI     │
│  (claude -p)    │
└─────────────────┘
```

## Directory Structure

```
agent-remote-access/
├── agent-api/              # Port 8001 - Agent communication API
│   ├── main.py            # FastAPI server
│   ├── auth.py            # HTTP Basic Auth
│   ├── claude_wrapper.py  # Claude CLI subprocess wrapper
│   └── config.py          # Configuration
│
├── ui-server/             # Port 8000 - UI server
│   ├── main.py            # FastAPI static file server
│   ├── config.py          # Configuration
│   └── static/
│       ├── index.html     # Chat interface
│       ├── app.js         # Frontend logic
│       └── styles.css     # Styling
│
├── start.sh               # Start both servers
├── stop.sh                # Stop both servers
├── logs/                  # Server logs
│   ├── agent-api.log
│   ├── ui-server.log
│   ├── agent-api.pid
│   └── ui-server.pid
│
└── .env                   # Configuration

```

## Key Features

1. **Clean Separation**: UI and API are completely decoupled
2. **No Docker Dependency**: Runs directly on host for local testing
3. **Stateless**: No session management - user provides session_id to resume
4. **Direct CLI Execution**: Agent API calls `claude -p` via subprocess
5. **Session Listing**: Can list and resume existing Claude Code sessions
6. **Easy Management**: Simple start/stop scripts

## Usage

### Start Both Servers
```bash
./start.sh
```

### Stop Both Servers
```bash
./stop.sh
```

### Access
- UI: http://localhost:8000
- Agent API: http://localhost:8001

## API Endpoints

### Agent API (Port 8001)

**POST /api/chat**
```json
Request:
{
  "message": "What is 2+2?",
  "session_id": "optional-uuid"  // omit for new session
}

Response:
{
  "response": "2+2 equals 4",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "cost": 0.0012,
  "turns": 1,
  "success": true,
  "error": null
}
```

**GET /api/sessions**
```json
Response:
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "display": "Implementing dark mode toggle",
      "project": "/Users/name/my-project",
      "timestamp": 1702234567
    }
  ]
}
```

## Authentication

- Agent API requires HTTP Basic Auth
- Credentials configured in `.env` file
- UI prompts for credentials and stores in localStorage

## Configuration (.env)

```bash
# Auth credentials
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password

# Project path for Claude context
CLAUDE_PROJECT_PATH=/path/to/your/project

# Server ports (optional)
AGENT_API_PORT=8001
UI_SERVER_PORT=8000
```

## Benefits of This Architecture

1. **Better Decoupling**: UI can be swapped out (React, Vue, etc.)
2. **Reusable API**: Agent API can serve multiple frontends
3. **Local Testing**: No Docker complexity for development
4. **Vendor Agnostic**: Easy to add support for other AI CLIs
5. **Simple Deployment**: Can run both servers or just the API
