# Claude Code Remote Access

Remote HTTPS access to Claude Code CLI from mobile devices. Submit tasks via REST API, bypass Cloudflare timeouts with async polling.

## Quick Start

```bash
# 1. Authenticate Claude CLI
claude login

# 2. Clone and configure
git clone https://github.com/rgasiorek/agent-remote-access.git
cd agent-remote-access
cp .env.example .env
# Edit .env: set AUTH_USERNAME, AUTH_PASSWORD, CLAUDE_PROJECT_PATH

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start services (local only, no tunnel)
./start_all.sh --no-tunnel

# Access at: http://localhost
```

**For remote access via Cloudflare:**
```bash
./start_all.sh  # Auto-starts tunnel if cloudflared installed
# Or manually: cloudflared tunnel --url http://localhost
```

## REST API

All endpoints require HTTP Basic Auth (except `/health`, `/api/config`):
```http
Authorization: Basic base64(username:password)
```

### Async Chat API

Polling pattern bypasses Cloudflare ~100s timeout. Tasks run indefinitely.

```http
POST /api/sessions/{session_id}/chat
```
- Path: `session_id` = UUID or `"new"`
- Request: `{"message": "string"}`
- Response: `{"task_id": "uuid", "status": "processing"}`

```http
GET /api/sessions/{session_id}/tasks/{task_id}
```
- Response: `{"status": "processing"}` or `{"status": "completed", "result": {...}}`
- Poll every 5s until completed

```http
DELETE /api/sessions/{session_id}/tasks/{task_id}
```
- Response: `{"status": "cleaned"}`
- Call after displaying result

### Session Management

```http
GET /api/sessions
```
- Response: `{"sessions": [{"session_id": "...", "display": "...", "project": "...", "timestamp": 0}]}`
- Filtered by `CLAUDE_PROJECT_PATH`, newest first, max 20

```http
GET /api/config
```
- Response: `{"project_path": "/path/to/project"}`

### Sync API

```http
POST /api/chat
```
- Request: `{"message": "...", "session_id": "optional-uuid"}`
- Response: `{"response": "...", "session_id": "...", "cost": 0.05, "turns": 2, "success": true}`
- Blocks until complete, times out after ~100s via Cloudflare

## Architecture

```
Mobile Browser
    ↓ HTTPS
Cloudflare Tunnel
    ↓ HTTP
Nginx (port 80)
    ├─→ /api/*  → Agent API (port 8001)
    └─→ /*      → Portal UI (port 8000)
                      ↓
            Claude Code CLI (subprocess)
```

**Components:**

- **Nginx** - Routes requests to backend services
- **Portal UI** - Static HTML/JS chat interface
- **Agent API** - FastAPI backend that:
  - Authenticates requests (HTTP Basic Auth)
  - Spawns Claude CLI: `claude -p "..." --resume {session_id} --output-format json`
  - For async: redirects stdout to `/tmp/claude_task_{task_id}.json`
  - For sync: blocks on `subprocess.run()`
- **Claude CLI** - Runs in project directory, maintains session state in `~/.claude/`

**Async Pattern Details:**
1. `POST /api/sessions/{id}/chat` → `subprocess.Popen()` with `stdout=/tmp/file`
2. Returns task_id immediately
3. Browser polls `GET /tasks/{task_id}` → reads file, checks if complete
4. When done, browser calls `DELETE /tasks/{task_id}` → removes temp file

No subprocess tracking needed - files persist in `/tmp`, OS handles process lifecycle.

## Installation

### Prerequisites

- Python 3.8+
- Nginx: `brew install nginx` (macOS) or `apt install nginx` (Linux)
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- Cloudflared: `brew install cloudflared` or download from https://github.com/cloudflare/cloudflared/releases

### Setup

```bash
# 1. Authenticate Claude CLI (required)
claude login

# 2. Clone repository
git clone https://github.com/rgasiorek/agent-remote-access.git
cd agent-remote-access

# 3. Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env:
#   AUTH_USERNAME=your_username
#   AUTH_PASSWORD=your_secure_password
#   CLAUDE_PROJECT_PATH=/path/to/your/project
```

### Run Locally

```bash
# Start application services only (Portal UI + Agent API)
./start.sh

# Start everything (app + Nginx + Cloudflare tunnel)
./start_all.sh

# Stop
./stop.sh        # Apps only
./stop_all.sh    # Everything
```

**Ports:**
- Portal UI: 8000 (internal)
- Agent API: 8001 (internal)
- Nginx: 80 (public, routes to above)

### Expose via Cloudflare

**Option 1: Quick testing (URL changes on restart)**
```bash
cloudflared tunnel --url http://localhost
# Output: https://random-words.trycloudflare.com
```

**Option 2: Persistent domain (requires Cloudflare account + domain)**

1. Create tunnel:
```bash
cloudflared tunnel login
cloudflared tunnel create agent-remote-access
```

2. Configure DNS (in Cloudflare dashboard):
```
CNAME: remote-agent.yourdomain.com → <tunnel-id>.cfargotunnel.com
```

3. Create `~/.cloudflared/config.yml`:
```yaml
tunnel: agent-remote-access
credentials-file: /path/to/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: remote-agent.yourdomain.com
    service: http://localhost:80
  - service: http_status:404
```

4. Run tunnel:
```bash
cloudflared tunnel run
```

Or use `start_all.sh` which handles tunnel automatically.

## Project Structure

```
agent-remote-access/
├── agent-api/
│   ├── main.py              # FastAPI app, REST endpoints
│   ├── auth.py              # HTTP Basic Auth
│   ├── claude_wrapper.py    # Claude CLI wrapper
│   └── config.py            # Environment config
├── portal-ui/
│   ├── main.py              # Static file server
│   └── static/
│       ├── index.html       # Chat UI
│       ├── app.js           # Frontend (polling logic)
│       └── styles.css
├── nginx.conf               # Reverse proxy config
├── start.sh                 # Start apps
├── start_all.sh             # Start apps + Nginx + tunnel
├── stop.sh / stop_all.sh
├── requirements.txt
├── .env.example
└── README.md
```

## Features

- **Remote Access** - Chat with Claude from any mobile browser
- **Async Tasks** - Bypass Cloudflare timeout, tasks run indefinitely
- **Session Persistence** - Resume conversations across requests
- **Multiple Sessions** - Dropdown to switch between conversations
- **Secure** - HTTPS via Cloudflare + HTTP Basic Auth
- **Mobile-Responsive** - Clean chat interface for mobile
- **Cost Tracking** - Monitor API usage per session

## Troubleshooting

### "claude: command not found"
```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

### "Not authenticated" error
```bash
claude login
# Creates ~/.claude.json with credentials
```

### "AUTH_USERNAME must be set"
```bash
cp .env.example .env
# Edit .env and set credentials
```

### Cloudflare 524 timeout
Use async API instead of sync. Async polling bypasses timeout.

### Session dropdown empty
Sessions are created after first message. Use "new" session initially.

### Nginx won't start
```bash
# Check if port 80 is already in use
lsof -i :80
# Kill existing process or change nginx.conf port
```

### Task not found
Temp files in `/tmp` may be deleted by OS. Submit a new task.

## Security Notes

**Current implementation:**
- HTTP Basic Auth (credentials in every request header)
- HTTPS via Cloudflare Tunnel
- `.env` credentials (gitignored)
- Session UUIDs (not guessable)

**For production:**
- Replace Basic Auth with JWT tokens
- Implement rate limiting
- Add IP whitelisting
- Encrypt session data at rest

## Development

### Testing API Locally

```bash
# Health check
curl http://localhost:8001/health

# Submit async task
curl -u user:pass http://localhost:8001/api/sessions/new/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Claude"}'

# Poll status
curl -u user:pass http://localhost:8001/api/sessions/new/tasks/{task_id}

# Cleanup
curl -u user:pass -X DELETE http://localhost:8001/api/sessions/new/tasks/{task_id}
```

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=agent-api --cov-report=term-missing
```

## Notes

- Each request spawns a new `claude -p` subprocess
- Session state managed by Claude Code in `~/.claude/`
- Project context from `CLAUDE_PROJECT_PATH` environment variable
- Temp files in `/tmp` cleaned up by browser after rendering
- Orphaned processes handled by OS (no manual cleanup needed)

## License

MIT License - modify and use freely.

## Support

- Claude Code CLI: https://github.com/anthropics/claude-code/issues
- This project: Open an issue in this repository
