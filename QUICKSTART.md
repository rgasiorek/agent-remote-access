# Quick Start Guide

Get up and running with Claude Code Remote Access in 5 minutes.

## Step 1: Install Dependencies (1 minute)

```bash
# Clone and navigate to directory
git clone https://github.com/rgasiorek/agent-remote-access.git
cd agent-remote-access

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
. venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure (1 minute)

```bash
# Create .env file
cp .env.example .env

# Edit .env - set your credentials
nano .env
```

Set these values:
```
AUTH_USERNAME=yourname
AUTH_PASSWORD=yourpassword
CLAUDE_PROJECT_PATH=/path/to/your/project
```

## Step 3: Start Server (30 seconds)

```bash
python -m server.main
```

You should see:
```
Starting Claude Code Remote Access Server...
Project path: /path/to/your/project
Server URL: http://127.0.0.1:8000
```

## Step 4: Test Locally (1 minute)

Open browser: `http://localhost:8000`
- Enter your credentials when prompted
- Type a message and send
- You should get a response from Claude!

## Step 5: Expose via Ngrok (1 minute)

In a NEW terminal:

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## Step 6: Access from Mobile (30 seconds)

- Open the ngrok URL on your phone
- Enter credentials
- Start chatting!

## Verify It's Working

Test message: "What files are in this project?"

Claude should respond with information about your project files.

## Common Issues

**"AUTH_USERNAME must be set"**
→ You didn't create `.env` file. Run: `cp .env.example .env`

**"claude: command not found"**
→ Install Claude Code CLI first

**Authentication keeps prompting**
→ Check username/password in `.env` match what you're typing

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [API documentation](#api-endpoints) in README
- Customize the frontend in `frontend/` directory

## Stopping the Server

Press `Ctrl+C` in the terminal running the server.

To deactivate Python environment:
```bash
deactivate
```
