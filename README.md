# Claude Code Remote Access

A system for remotely accessing Claude Code CLI sessions from mobile devices via HTTPS.

## Overview

This project creates a **remote access bridge** to interact with Claude Code CLI sessions from your mobile device. It's built with FastAPI and provides:

1. **Web-based chat interface** - Mobile-friendly UI served by FastAPI
2. **HTTP API endpoints** - RESTful API for sending messages to Claude Code
3. **Session management** - Tracks multiple conversations with context persistence
4. **Secure tunnel** - Ngrok exposes local server to internet via HTTPS

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ MOBILE DEVICE                                                       │
│                                                                     │
│  Browser → Chat UI (HTML/JS/CSS)                                   │
│            ↓                                                        │
│  HTTPS Requests to API:                                            │
│    • POST /api/chat {"message": "...", "conv_id": "default"}       │
│    • GET  /api/sessions (list all conversations)                   │
│    • POST /api/reset (start new conversation)                      │
└─────────────────────────────────────────────────────────────────────┘
                             ↓
                    HTTPS (Encrypted)
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ NGROK TUNNEL (https://abc123.ngrok.io)                             │
│  • Provides public HTTPS URL                                        │
│  • Handles SSL/TLS termination                                      │
│  • Forwards to localhost:8000                                       │
└─────────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│ YOUR LAPTOP (localhost:8000)                                        │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ FASTAPI SERVER (Python)                                       │   │
│ │                                                               │   │
│ │  1. Serves Frontend (/, /app.js, /styles.css)                │   │
│ │  2. API Endpoints (/api/*)                                    │   │
│ │  3. HTTP Basic Auth Middleware                                │   │
│ │  4. Session Manager (tracks conversation IDs → session UUIDs) │   │
│ │  5. Claude CLI Wrapper (subprocess executor)                  │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                             ↓                                       │
│              Spawns subprocess for each request:                    │
│              `claude -p "message" --resume <UUID> --output-format json` │
│                             ↓                                       │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ CLAUDE CODE CLI (Headless Mode)                              │   │
│ │  • Executes in project directory (CLAUDE_PROJECT_PATH)        │   │
│ │  • Has access to local files, git, tools                      │   │
│ │  • Returns JSON response with result + session UUID           │   │
│ │  • Session stored in ~/.claude/ for continuity                │   │
│ └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Points:

- **FastAPI** serves BOTH the frontend UI AND the HTTP API endpoints
- Each API request spawns a `claude -p` subprocess (headless mode)
- The FastAPI server acts as a **stateless proxy** - it doesn't maintain conversation context
- **Claude Code itself** maintains conversation context via session UUIDs (stored in `~/.claude/`)
- The **session manager** just tracks which UUID belongs to which conversation ID
- Multiple conversations can run simultaneously (each gets its own UUID)

## Features

- **Remote Access**: Chat with Claude Code from any mobile browser
- **Multiple Sessions**: Dropdown to select and switch between conversations
- **Session Persistence**: Each conversation maintains full context across requests
- **Last Message Preview**: See the last message from each conversation
- **Secure Access**: HTTP Basic Authentication + HTTPS via ngrok
- **Mobile-Responsive UI**: Clean chat interface optimized for mobile devices
- **Cost Tracking**: Monitor API usage and conversation turns per session
- **Auto-Approved Permissions**: Pre-configured to allow file editing and git operations

## Prerequisites

- Python 3.8 or higher
- Claude Code CLI installed and authenticated
- ngrok account (free tier works fine)

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/rgasiorek/agent-remote-access.git
cd agent-remote-access

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
. venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install ngrok

```bash
# macOS (with Homebrew)
brew install ngrok

# Or download directly for macOS (ARM64)
curl -Lo ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip
unzip ngrok.zip
chmod +x ngrok

# For other platforms, visit: https://ngrok.com/download
```

**Setup ngrok authentication:**

1. Sign up for free at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Configure ngrok:

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### 3. Configure Environment

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
. venv/bin/activate

# Start the server
python -m server.main
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
. venv/bin/activate
python -m server.main

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
