#!/bin/bash

# Stop script for ALL services (Application + Infrastructure)
# Stops application services, Nginx, and Cloudflare tunnel

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping ALL Services${NC}"
echo "====================="

KILLED=false

# Stop Nginx
if [ -f logs/nginx.pid ]; then
    NGINX_PID=$(cat logs/nginx.pid)
    if ps -p $NGINX_PID > /dev/null 2>&1; then
        echo "Killing Nginx (PID: $NGINX_PID)..."
        kill $NGINX_PID 2>/dev/null && KILLED=true
        rm -f logs/nginx.pid
    else
        echo "Nginx PID file exists but process not running"
        rm -f logs/nginx.pid
    fi
fi

# Also try to kill by port (in case PID file is missing)
NGINX_PID=$(lsof -ti:80 2>/dev/null || true)
if [ -n "$NGINX_PID" ]; then
    echo "Found Nginx on port 80 (PID: $NGINX_PID), killing..."
    kill $NGINX_PID 2>/dev/null && KILLED=true
fi

# Stop application services
echo ""
./stop.sh

# Stop Cloudflare tunnel if running
if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
    echo ""
    echo "Stopping Cloudflare tunnel..."
    pkill -f "cloudflared tunnel"
    echo -e "${GREEN}✓ Cloudflare tunnel stopped${NC}"
    KILLED=true
fi

echo ""
if [ "$KILLED" = true ]; then
    echo -e "${GREEN}✓ All services stopped${NC}"
else
    echo -e "${YELLOW}No services were running${NC}"
fi
echo ""
