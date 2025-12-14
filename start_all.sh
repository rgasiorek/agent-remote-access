#!/bin/bash

# Start script for ALL services (Application + Infrastructure)
# Starts application services AND Nginx gateway

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

echo ""
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo "======================================="
echo -e "Access application at: ${GREEN}http://localhost${NC}"
echo ""
echo "Services running:"
echo "  Nginx Gateway:  port 80"
echo "  Portal UI:      port 8000 (internal)"
echo "  Agent API:      port 8001 (internal)"
echo ""
echo "To view logs:"
echo "  tail -f logs/nginx-access.log"
echo "  tail -f logs/nginx-error.log"
echo "  tail -f logs/portal-ui.log"
echo "  tail -f logs/agent-api.log"
echo ""
echo "To stop all services:"
echo "  ./stop_all.sh"
echo ""
