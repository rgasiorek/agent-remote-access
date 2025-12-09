# Claude Code Remote Access

A system for remotely accessing Claude Code CLI sessions from mobile devices via HTTPS.

## Overview

This project creates a **remote access bridge** to interact with Claude Code CLI sessions from your mobile device. It's built with FastAPI and provides:

1. **Web-based chat interface** - Mobile-friendly UI served by FastAPI
2. **HTTP API endpoints** - RESTful API for sending messages to Claude Code
3. **Session management** - Tracks multiple conversations with context persistence
4. **Secure tunnel** - Cloudflare Tunnel exposes local server to internet via HTTPS

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
│ CLOUDFLARE TUNNEL (https://remote-agent.yourdomain.com)            │
│  • Provides persistent HTTPS URL on your domain                     │
│  • Handles SSL/TLS termination                                      │
│  • Global CDN network for low latency                               │
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
- **Secure Access**: HTTP Basic Authentication + HTTPS via Cloudflare Tunnel
- **Mobile-Responsive UI**: Clean chat interface optimized for mobile devices
- **Cost Tracking**: Monitor API usage and conversation turns per session
- **Auto-Approved Permissions**: Pre-configured to allow file editing and git operations

## Prerequisites

- Python 3.8 or higher
- Claude Code CLI installed and authenticated
- Cloudflare account (free tier works great)
- **For persistent access**: A domain managed by Cloudflare (see options below)
- **For quick testing**: No domain needed - use TryCloudflare

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

### 2. Install Cloudflare Tunnel

```bash
# macOS (with Homebrew)
brew install cloudflared

# Or download directly for macOS (ARM64)
curl -Lo cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# For other platforms, visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

**Setup Cloudflare Tunnel:**

1. Sign up for free at https://dash.cloudflare.com/sign-up
2. Authenticate cloudflared:

```bash
cloudflared tunnel login
```

This opens a browser window to authorize. Once authorized, create your tunnel:

```bash
# Create tunnel
cloudflared tunnel create agent-remote-access

# This creates a credentials file at ~/.cloudflared/<TUNNEL-ID>.json
# Note the Tunnel ID from the output
```

3. Create a DNS record (replace with your domain):

```bash
# Route your domain to the tunnel
cloudflared tunnel route dns agent-remote-access remote-agent.yourdomain.com
```

Or use Cloudflare's free subdomain:
```bash
cloudflared tunnel route dns agent-remote-access <TUNNEL-ID>.cfargotunnel.com
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

### Exposing via Cloudflare Tunnel

You have two options for exposing your local server:

#### Option 1: Quick Testing with TryCloudflare (No Domain Required)

**Perfect for:** Testing, development, temporary access

```bash
# Start a quick tunnel - gives you a random URL instantly
cloudflared tunnel --url http://localhost:8000
```

This will output something like:
```
https://random-words-here-something.trycloudflare.com
```

**Pros:**
- No domain required
- Works immediately
- Free and simple

**Cons:**
- URL changes every time you restart
- No uptime guarantee (testing only)
- Not suitable for production

#### Option 2: Persistent Named Tunnel (Requires Domain)

**Perfect for:** Production use, consistent URLs, long-term access

In a new terminal:

```bash
# Run your named tunnel (requires Terraform setup - see below)
cloudflared tunnel --config .cloudflared/config.yml run agent-remote-access
```

Or use a config file at `~/.cloudflared/config.yml`:

```yaml
tunnel: agent-remote-access
credentials-file: /Users/yourname/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: remote-agent.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

Then simply run:
```bash
cloudflared tunnel run
```

Your tunnel will be available at: `https://remote-agent.yourdomain.com`

### Accessing from Mobile

1. Open your Cloudflare Tunnel URL in your mobile browser (e.g., `https://remote-agent.yourdomain.com`)
2. Enter your HTTP Basic Auth credentials (from `.env`)
3. Select a session from the dropdown or start a new one
4. Start chatting with Claude Code!

## Domain Options for Persistent Tunnels

**IMPORTANT:** Named Cloudflare Tunnels require a domain. The `.cfargotunnel.com` subdomain is NOT publicly accessible.

### Option A: Buy a Domain (Recommended for Production)

1. **Register a cheap domain** ($1-10/year):
   - Cloudflare Registrar (cheapest, built-in)
   - Namecheap, Porkbun, etc.

2. **Add domain to Cloudflare**:
   - Add site in Cloudflare dashboard
   - Update nameservers at your registrar
   - Wait for DNS propagation (~5-60 minutes)

3. **Use Terraform to automate setup**:
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your Cloudflare credentials and domain
   terraform init
   terraform apply
   ```

This automatically creates:
- Cloudflare Tunnel
- DNS CNAME record pointing to your tunnel
- Local credentials and config files

See [`terraform/README.md`](terraform/README.md) for detailed instructions.

### Option B: Free Subdomain Services

Use a free DNS provider and manually create CNAME records:

**Popular Free Options:**
- **Duck DNS** (duckdns.org) - Simple, reliable
- **FreeDNS** (freedns.afraid.org) - Many TLDs available
- **No-IP** (noip.com) - Free tier available

**Setup Steps:**
1. Create free subdomain (e.g., `myproject.duckdns.org`)
2. Create CNAME record: `<TUNNEL-ID>.cfargotunnel.com`
3. Update your tunnel config with the subdomain
4. Run `cloudflared tunnel run agent-remote-access`

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
├── terraform/               # Cloudflare Tunnel IaC
│   ├── cloudflare.tf        # Main Terraform config
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   └── README.md           # Terraform documentation
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

## Troubleshooting

### Cloudflare Tunnel Connection Issues

If you see "control stream encountered a failure" errors:

1. **Verify FastAPI server is running:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","service":"claude-remote-access"}
   ```

2. **Check cloudflared is using correct config:**
   ```bash
   # When using Terraform-generated config, run:
   cloudflared tunnel --config .cloudflared/config.yml run agent-remote-access
   ```

3. **Validate ingress configuration:**
   ```bash
   cloudflared tunnel --config .cloudflared/config.yml ingress validate
   # Should output: OK
   ```

4. **Check tunnel status:**
   ```bash
   # View tunnel info (requires API token in env)
   export CLOUDFLARE_API_TOKEN=your_token
   cloudflared tunnel info agent-remote-access
   ```

5. **Verify credentials file exists:**
   ```bash
   ls -la .cloudflared/*.json
   # Should show the tunnel credentials file
   ```

6. **Test local connectivity:**
   ```bash
   # Ensure no firewall blocking localhost:8000
   telnet localhost 8000
   # Or:
   nc -zv localhost 8000
   ```

7. **Check for port conflicts:**
   ```bash
   lsof -i :8000
   # Should only show your python process
   ```

### Common Issues

**"Could not resolve host: *.cfargotunnel.com" or tunnel URL not accessible**
- **Problem**: Named tunnels do NOT get public DNS automatically
- **Solution**: You MUST either:
  1. Use TryCloudflare for quick testing: `cloudflared tunnel --url http://localhost:8000`
  2. Add a domain to your Cloudflare account and configure DNS records
  3. Use a free subdomain service (Duck DNS, FreeDNS)
- The `.cfargotunnel.com` subdomain exists but is NOT publicly routable
- See "Domain Options for Persistent Tunnels" section above

**"Cannot determine default origin certificate path"**
- Solution: Always specify `--config` flag with full path to config.yml
- Example: `cloudflared tunnel --config /full/path/to/.cloudflared/config.yml run agent-remote-access`

**"Tunnel not found" or "404" on URL**
- Ensure tunnel is running (`ps aux | grep cloudflared`)
- Verify you're using the correct tunnel URL from Terraform output
- Check tunnel exists: `cloudflared tunnel list`

**"Authentication error (10000)"**
- Your Cloudflare API token needs **Cloudflare Tunnel** permissions
- Regenerate token at: https://dash.cloudflare.com/profile/api-tokens
- Update `terraform/terraform.tfvars` with new token

**Remote Claude can't edit files**
- Add permissions to `.claude/settings.local.json` (see QUICKSTART.md)
- Start a new Claude session after updating permissions
- Old sessions don't pick up new permission settings

**Session dropdown empty**
- Sessions are created after first message
- Check `sessions/sessions.json` exists and is valid JSON
- Restart FastAPI server if file was manually edited

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
