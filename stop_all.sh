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
if command -v nginx &> /dev/null; then
    # Check if Nginx is running
    if lsof -ti:80 >/dev/null 2>&1; then
        echo "Stopping Nginx..."
        nginx -c "$SCRIPT_DIR/nginx.conf" -p "$SCRIPT_DIR" -s stop 2>/dev/null
        if [ $? -eq 0 ]; then
            KILLED=true
            echo -e "${GREEN}✓ Nginx stopped${NC}"
        else
            # Fallback to force kill if graceful stop fails
            NGINX_PIDS=$(lsof -ti:80 2>/dev/null || true)
            if [ -n "$NGINX_PIDS" ]; then
                echo "Force killing Nginx processes..."
                kill -9 $NGINX_PIDS 2>/dev/null && KILLED=true
            fi
        fi
        rm -f logs/nginx.pid
    fi
fi

# Stop application services
echo ""
./stop.sh

# Stop Cloudflare tunnel
if [ -f logs/cloudflared.pid ]; then
    TUNNEL_PID=$(cat logs/cloudflared.pid)
    if ps -p $TUNNEL_PID > /dev/null 2>&1; then
        echo ""
        echo "Killing Cloudflare tunnel (PID: $TUNNEL_PID)..."
        kill $TUNNEL_PID 2>/dev/null && KILLED=true
        rm -f logs/cloudflared.pid
    else
        echo "Cloudflare tunnel PID file exists but process not running"
        rm -f logs/cloudflared.pid
    fi
fi

# Also try to kill by process name (in case PID file is missing)
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
