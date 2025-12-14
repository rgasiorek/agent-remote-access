#!/bin/bash

# Start script for ALL services (Application + Infrastructure)
# Starts application services AND Nginx gateway
#
# Usage:
#   ./start_all.sh             # Start everything including Cloudflare tunnel
#   ./start_all.sh --no-tunnel # Start without Cloudflare tunnel (local only)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
SKIP_TUNNEL=false
for arg in "$@"; do
    case $arg in
        --no-tunnel)
            SKIP_TUNNEL=true
            shift
            ;;
    esac
done

echo -e "${GREEN}Starting ALL Services (Application + Infrastructure)${NC}"
echo "====================================================="

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

# Check if cloudflared is installed (unless --no-tunnel specified)
if [ "$SKIP_TUNNEL" = true ]; then
    echo -e "${YELLOW}Skipping Cloudflare tunnel (--no-tunnel flag)${NC}"
elif ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}Warning: cloudflared is not installed${NC}"
    echo "Cloudflare tunnel will not be started"
    echo "Install with: brew install cloudflared"
    SKIP_TUNNEL=true
else
    echo -e "${GREEN}✓ cloudflared found${NC}"
fi

# Start application services
echo ""
echo "Starting application services..."
./start.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start application services${NC}"
    exit 1
fi

echo ""
echo "Waiting for application services to be ready..."
sleep 2

# Start Nginx
echo -e "${GREEN}Starting Nginx API Gateway on port 80...${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Nginx with our custom config
nginx -c "$SCRIPT_DIR/nginx.conf" -p "$SCRIPT_DIR"
NGINX_EXIT_CODE=$?

if [ $NGINX_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Failed to start Nginx${NC}"
    echo "Check logs/nginx-error.log for details"
    echo "Stopping application services..."
    ./stop.sh
    exit 1
fi

# Get Nginx PID
NGINX_PID=$(lsof -ti:80 2>/dev/null || echo "unknown")
if [ "$NGINX_PID" != "unknown" ]; then
    echo $NGINX_PID > logs/nginx.pid
fi

sleep 1

# Start Cloudflare tunnel
if [ "$SKIP_TUNNEL" = false ]; then
    echo ""
    echo -e "${GREEN}Starting Cloudflare Tunnel...${NC}"

    # Check if tunnel is already running
    if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
        echo -e "${YELLOW}Cloudflare tunnel is already running${NC}"
    else
        # Start tunnel in background and capture output
        cloudflared tunnel --url http://localhost > logs/cloudflared.log 2>&1 &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > logs/cloudflared.pid

        # Wait for tunnel to start and get URL
        echo "Waiting for tunnel to connect..."
        sleep 5

        # Extract tunnel URL from logs
        TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' logs/cloudflared.log | head -1)

        if [ -n "$TUNNEL_URL" ]; then
            echo -e "${GREEN}✓ Cloudflare tunnel started${NC}"
            echo -e "Tunnel URL: ${GREEN}${TUNNEL_URL}${NC}"
        else
            echo -e "${YELLOW}Tunnel started but URL not yet available${NC}"
            echo "Check logs/cloudflared.log for tunnel URL"
        fi
    fi
fi

echo ""
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo "======================================="
echo -e "Local access:  ${GREEN}http://localhost${NC}"
if [ "$SKIP_TUNNEL" = false ] && [ -n "$TUNNEL_URL" ]; then
    echo -e "Remote access: ${GREEN}${TUNNEL_URL}${NC}"
fi
echo ""
echo "Services running:"
echo "  Nginx Gateway:  port 80"
echo "  Portal UI:      port 8000 (internal)"
echo "  Agent API:      port 8001 (internal)"
if [ "$SKIP_TUNNEL" = false ]; then
    echo "  Cloudflare Tunnel: $TUNNEL_URL"
fi
echo ""
echo "To view logs:"
echo "  tail -f logs/nginx-access.log"
echo "  tail -f logs/nginx-error.log"
echo "  tail -f logs/portal-ui.log"
echo "  tail -f logs/agent-api.log"
if [ "$SKIP_TUNNEL" = false ]; then
    echo "  tail -f logs/cloudflared.log"
fi
echo ""
echo "To stop all services:"
echo "  ./stop_all.sh"
echo ""
