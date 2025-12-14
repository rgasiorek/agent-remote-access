#!/bin/bash

# Start script for Claude Code Remote Access
# Starts both UI server and Agent API server

set -e

# Remember the directory where the script was called from (the project path)
PROJECT_DIR="$(pwd)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export project path for the servers to use (where the script was called from)
export CLAUDE_PROJECT_PATH="$PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Claude Code Remote Access${NC}"
echo "=================================="

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}Error: Nginx is not installed${NC}"
    echo "Please install Nginx:"
    echo "  macOS: brew install nginx"
    echo "  Ubuntu/Debian: sudo apt-get install nginx"
    echo "  CentOS/RHEL: sudo yum install nginx"
    exit 1
fi
echo -e "${GREEN}✓ Nginx found${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your credentials"
    exit 1
fi

# Check if Claude is authenticated
if [ ! -f "$HOME/.claude.json" ]; then
    echo -e "${RED}Error: Claude CLI is not authenticated${NC}"
    echo "Please run 'claude login' in your terminal first to authenticate"
    exit 1
fi
echo -e "${GREEN}✓ Claude authentication found${NC}"

# Check for running processes
AGENT_API_PID=$(lsof -ti:8001 2>/dev/null || true)
UI_SERVER_PID=$(lsof -ti:8000 2>/dev/null || true)
NGINX_PID=$(lsof -ti:80 2>/dev/null || true)

if [ -n "$AGENT_API_PID" ] || [ -n "$UI_SERVER_PID" ] || [ -n "$NGINX_PID" ]; then
    echo -e "${YELLOW}Warning: Servers are already running on ports 80, 8000, or 8001${NC}"
    echo "PIDs found: Nginx=$NGINX_PID, Agent API=$AGENT_API_PID, Portal UI=$UI_SERVER_PID"
    read -p "Do you want to kill them and restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -n "$NGINX_PID" ]; then
            echo "Killing Nginx (PID: $NGINX_PID)..."
            kill $NGINX_PID 2>/dev/null || true
            sleep 1
        fi
        if [ -n "$AGENT_API_PID" ]; then
            echo "Killing Agent API (PID: $AGENT_API_PID)..."
            kill $AGENT_API_PID 2>/dev/null || true
            sleep 1
        fi
        if [ -n "$UI_SERVER_PID" ]; then
            echo "Killing Agent Portal UI (PID: $UI_SERVER_PID)..."
            kill $UI_SERVER_PID 2>/dev/null || true
            sleep 1
        fi
    else
        echo "Exiting without starting new servers"
        exit 0
    fi
fi

# Check Python dependencies
echo "Checking Python dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip3 install -q -r requirements.txt
fi

# Start Agent API server in background
echo -e "${GREEN}Starting Agent API server on port 8001...${NC}"
cd agent-api
python3 main.py > ../logs/agent-api.log 2>&1 &
AGENT_PID=$!
echo $AGENT_PID > ../logs/agent-api.pid
cd ..

sleep 2

# Check if Agent API started successfully
if ! ps -p $AGENT_PID > /dev/null; then
    echo -e "${RED}Failed to start Agent API server${NC}"
    echo "Check logs/agent-api.log for details"
    exit 1
fi

# Start Agent Portal UI in background
echo -e "${GREEN}Starting Agent Portal UI on port 8000...${NC}"
cd portal-ui
python3 main.py > ../logs/portal-ui.log 2>&1 &
UI_PID=$!
echo $UI_PID > ../logs/portal-ui.pid
cd ..

sleep 2

# Check if Agent Portal UI started successfully
if ! ps -p $UI_PID > /dev/null; then
    echo -e "${RED}Failed to start Agent Portal UI${NC}"
    echo "Check logs/portal-ui.log for details"
    echo "Killing Agent API server..."
    kill $AGENT_PID 2>/dev/null || true
    exit 1
fi

# Start Nginx as API gateway
echo -e "${GREEN}Starting Nginx API Gateway on port 80...${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Nginx with our custom config
nginx -c "$SCRIPT_DIR/nginx.conf" -p "$SCRIPT_DIR"
NGINX_EXIT_CODE=$?

if [ $NGINX_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Failed to start Nginx${NC}"
    echo "Check logs/nginx-error.log for details"
    echo "Killing backend servers..."
    kill $AGENT_PID 2>/dev/null || true
    kill $UI_PID 2>/dev/null || true
    exit 1
fi

# Get Nginx PID
NGINX_PID=$(lsof -ti:80 2>/dev/null || echo "unknown")
if [ "$NGINX_PID" != "unknown" ]; then
    echo $NGINX_PID > logs/nginx.pid
fi

sleep 1

echo ""
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo "=================================="
echo -e "Main Application: ${GREEN}http://localhost${NC} ${YELLOW}(or http://127.0.0.1)${NC}"
echo ""
echo "Backend Services (internal):"
echo "  Portal UI:  http://localhost:8000"
echo "  Agent API:  http://localhost:8001"
echo ""
echo "PIDs:"
echo "  Nginx Gateway: $NGINX_PID (saved to logs/nginx.pid)"
echo "  Agent API: $AGENT_PID (saved to logs/agent-api.pid)"
echo "  Portal UI: $UI_PID (saved to logs/portal-ui.pid)"
echo ""
echo "To view logs:"
echo "  tail -f logs/nginx-access.log"
echo "  tail -f logs/nginx-error.log"
echo "  tail -f logs/agent-api.log"
echo "  tail -f logs/portal-ui.log"
echo ""
echo "To stop all services:"
echo "  ./stop.sh"
echo ""
echo -e "${YELLOW}Note: All requests should go to http://localhost (port 80)${NC}"
echo -e "${YELLOW}Nginx will route /api/* to agent-api and everything else to portal-ui${NC}"
echo ""
