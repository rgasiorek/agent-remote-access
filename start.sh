#!/bin/bash

# Start script for Claude Code Remote Access
# Starts both UI server and Agent API server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Claude Code Remote Access${NC}"
echo "=================================="

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

if [ -n "$AGENT_API_PID" ] || [ -n "$UI_SERVER_PID" ]; then
    echo -e "${YELLOW}Warning: Servers are already running on ports 8000 or 8001${NC}"
    echo "PIDs found: Agent API=$AGENT_API_PID UI Server=$UI_SERVER_PID"
    read -p "Do you want to kill them and restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -n "$AGENT_API_PID" ]; then
            echo "Killing Agent API (PID: $AGENT_API_PID)..."
            kill $AGENT_API_PID 2>/dev/null || true
            sleep 1
        fi
        if [ -n "$UI_SERVER_PID" ]; then
            echo "Killing UI Server (PID: $UI_SERVER_PID)..."
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
pip3 list | grep -q fastapi || {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip3 install -r requirements.txt
}

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

# Start UI server in background
echo -e "${GREEN}Starting UI server on port 8000...${NC}"
cd ui-server
python3 main.py > ../logs/ui-server.log 2>&1 &
UI_PID=$!
echo $UI_PID > ../logs/ui-server.pid
cd ..

sleep 2

# Check if UI server started successfully
if ! ps -p $UI_PID > /dev/null; then
    echo -e "${RED}Failed to start UI server${NC}"
    echo "Check logs/ui-server.log for details"
    echo "Killing Agent API server..."
    kill $AGENT_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Both servers started successfully!${NC}"
echo "=================================="
echo -e "UI Server:        ${GREEN}http://localhost:8000${NC}"
echo -e "Agent API:        ${GREEN}http://localhost:8001${NC}"
echo ""
echo "PIDs:"
echo "  Agent API: $AGENT_PID (saved to logs/agent-api.pid)"
echo "  UI Server: $UI_PID (saved to logs/ui-server.pid)"
echo ""
echo "To view logs:"
echo "  tail -f logs/agent-api.log"
echo "  tail -f logs/ui-server.log"
echo ""
echo "To stop servers:"
echo "  ./stop.sh"
echo ""
