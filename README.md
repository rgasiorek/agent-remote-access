# Claude Code Remote Access

A system for remotely accessing Claude Code CLI sessions from mobile devices via HTTPS.

## Overview

This project creates a bridge between your mobile device and local Claude Code CLI sessions running on your laptop. It exposes a web-based chat interface that forwards messages to Claude Code using its headless mode (`claude -p`), maintaining conversation continuity through session management.

## Architecture

```
Mobile Browser (HTTPS)
    ↓
Ngrok Tunnel (HTTPS)
    ↓
FastAPI Server (Python)
    ├─ HTTP Basic Auth
    ├─ Session Manager
    └─ Claude CLI Wrapper
        ↓
    claude -p --resume <session-id>
        ↓
    Local Project Context
```

## Features

- **Remote Access**: Chat with Claude Code from any mobile browser
- **Session Persistence**: Conversations maintain context across requests
- **Secure Access**: HTTP Basic Authentication + HTTPS via ngrok
- **Simple UI**: Mobile-responsive chat interface
- **Session Management**: Track multiple conversations with session IDs
- **Cost Tracking**: Monitor API usage and conversation turns

## Prerequisites

- Python 3.8 or higher
- Claude Code CLI installed and authenticated
- ngrok account (free tier works fine)

## Installation

### 1. Clone and Setup

```bash
cd /Users/montrosesoftware/Workspace/agent-remote-access

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set:
# - AUTH_USERNAME: Your chosen username
# - AUTH_PASSWORD: Your secure password
# - CLAUDE_PROJECT_PATH: Path to the project you want Claude to work in (optional)
```

Example `.env`:
```bash
AUTH_USERNAME=myusername
AUTH_PASSWORD=supersecurepassword123
CLAUDE_PROJECT_PATH=/Users/you/my-project
HOST=127.0.0.1
PORT=8000
```

## Usage

### Starting the Server

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Start the server
python server/main.py
```

The server will start on `http://127.0.0.1:8000`

### Exposing via Ngrok

In a new terminal:

```bash
ngrok http 8000
```

Ngrok will provide an HTTPS URL like: `https://abc123.ngrok.io`

### Accessing from Mobile

1. Open the ngrok HTTPS URL in your mobile browser
2. Enter your HTTP Basic Auth credentials (from `.env`)
3. Start chatting with Claude Code!

## Project Structure

```
agent-remote-access/
├── server/
│   ├── main.py              # FastAPI application and routes
│   ├── auth.py              # HTTP Basic Authentication
│   ├── session_manager.py   # Session persistence logic
│   ├── claude_wrapper.py    # Claude CLI wrapper
│   └── config.py            # Configuration management
├── frontend/
│   ├── index.html           # Chat UI
│   ├── app.js              # Frontend JavaScript
│   └── styles.css          # Styling
├── sessions/
│   └── sessions.json        # Session storage (auto-created)
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .env                    # Your credentials (gitignored)
└── README.md               # This file
```

## API Endpoints

### Public Endpoints

- `GET /health` - Health check (no auth required)
- `GET /` - Chat UI

### Protected Endpoints (require Basic Auth)

- `POST /api/chat` - Send message to Claude
  - Request: `{"message": "string", "session_id": "optional-uuid", "conv_id": "default"}`
  - Response: `{"response": "string", "session_id": "uuid", "cost": float, "turns": int}`

- `POST /api/reset` - Reset conversation
  - Query param: `conv_id` (default: "default")
  - Response: `{"message": "...", "conv_id": "..."}`

- `GET /api/sessions` - Get all sessions (debug)

## How It Works

1. User sends message from mobile browser
2. Browser authenticates with HTTP Basic Auth
3. FastAPI server receives the request
4. Server checks for existing session ID
5. Executes `claude -p "message" --resume <session-id> --output-format json`
6. Parses JSON response from Claude CLI
7. Saves session ID for next request
8. Returns response to mobile browser

## Session Management

Sessions are stored in `sessions/sessions.json`:

```json
{
  "conversations": {
    "default": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-07T10:30:00Z",
      "last_message_at": "2025-12-07T10:35:00Z",
      "turn_count": 5
    }
  }
}
```

Each conversation maintains:
- Session UUID (used for `claude --resume`)
- Creation timestamp
- Last message timestamp
- Turn count

## Security Considerations

**Implemented:**
- HTTP Basic Authentication
- HTTPS via ngrok
- Credentials stored in `.env` (gitignored)
- Session IDs are UUIDs (not guessable)

**Limitations:**
- Basic Auth credentials sent with each request (over HTTPS)
- Ngrok free tier has URL changes on restart
- No rate limiting implemented
- Session file is plaintext on disk

**Production Recommendations:**
- Use JWT tokens instead of Basic Auth
- Implement rate limiting
- Use proper SSL certificates (not ngrok)
- Encrypt session data at rest
- Add IP whitelisting

## Troubleshooting

### "AUTH_USERNAME and AUTH_PASSWORD must be set"
- Copy `.env.example` to `.env` and configure credentials

### "claude: command not found"
- Ensure Claude Code CLI is installed and in PATH
- Run `claude --version` to verify

### Authentication prompt keeps appearing
- Verify credentials in `.env` match what you're entering
- Check for typos in username/password

### Session not persisting
- Check `sessions/` directory exists and is writable
- Look for errors in server logs

### Long response times
- Claude Code can take time for complex requests
- Default timeout is 5 minutes (configurable in `claude_wrapper.py`)

## Development

### Running Locally

```bash
# Terminal 1: Start server
source venv/bin/activate
python server/main.py

# Terminal 2 (optional): Start ngrok
ngrok http 8000

# Access at: http://localhost:8000
```

### Testing Authentication

```bash
# Test without auth (should fail)
curl http://localhost:8000/api/chat

# Test with auth
curl -u username:password http://localhost:8000/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello Claude!"}'
```

### Viewing Sessions

```bash
# Via API
curl -u username:password http://localhost:8000/api/sessions

# Via file
cat sessions/sessions.json
```

## Future Enhancements

- [ ] JWT authentication
- [ ] Rate limiting per user
- [ ] Multiple project switching
- [ ] WebSocket support for streaming responses
- [ ] Conversation history export
- [ ] Mobile app (native)
- [ ] Session encryption
- [ ] Multi-user support

## License

MIT License - feel free to modify and use as needed.

## Support

For issues with:
- Claude Code CLI: https://github.com/anthropics/claude-code/issues
- This project: Open an issue in this repository

## Notes

- This uses Claude Code's headless mode (`-p`), spawning a new process per request
- Session state is managed by Claude Code itself (stored in `~/.claude/`)
- This server only tracks which session UUID to resume
- Project context is determined by `CLAUDE_PROJECT_PATH` environment variable
- Each request is independent - long-running tasks may timeout

## Credits

Built to enable remote access to Claude Code CLI sessions from mobile devices.
