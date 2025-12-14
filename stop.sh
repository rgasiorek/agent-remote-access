#!/bin/bash

# Stop script for Claude Code Remote Access
# Stops both UI server and Agent API server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Claude Code Remote Access (Application Services)${NC}"
echo "=========================================================="

# Try to kill from PID files first
KILLED=false

if [ -f logs/agent-api.pid ]; then
    AGENT_PID=$(cat logs/agent-api.pid)
    if ps -p $AGENT_PID > /dev/null 2>&1; then
        echo "Killing Agent API (PID: $AGENT_PID)..."
        kill $AGENT_PID 2>/dev/null && KILLED=true
        rm -f logs/agent-api.pid
    else
        echo "Agent API PID file exists but process not running"
        rm -f logs/agent-api.pid
    fi
fi

if [ -f logs/portal-ui.pid ]; then
    UI_PID=$(cat logs/portal-ui.pid)
    if ps -p $UI_PID > /dev/null 2>&1; then
        echo "Killing Agent Portal UI (PID: $UI_PID)..."
        kill $UI_PID 2>/dev/null && KILLED=true
        rm -f logs/portal-ui.pid
    else
        echo "Agent Portal UI PID file exists but process not running"
        rm -f logs/portal-ui.pid
    fi
fi

# Also try to kill by port (in case PID files are missing)
AGENT_API_PID=$(lsof -ti:8001 2>/dev/null || true)
UI_SERVER_PID=$(lsof -ti:8000 2>/dev/null || true)

if [ -n "$AGENT_API_PID" ]; then
    echo "Found Agent API on port 8001 (PID: $AGENT_API_PID), killing..."
    kill $AGENT_API_PID 2>/dev/null && KILLED=true
fi

if [ -n "$UI_SERVER_PID" ]; then
    echo "Found Agent Portal UI on port 8000 (PID: $UI_SERVER_PID), killing..."
    kill $UI_SERVER_PID 2>/dev/null && KILLED=true
fi

# Wait a moment for processes to die
if [ "$KILLED" = true ]; then
    sleep 1
    echo -e "${GREEN}✓ Services stopped${NC}"
else
    echo -e "${YELLOW}No running services found${NC}"
fi

echo ""
