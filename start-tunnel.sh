#!/bin/bash

# Start Cloudflare Tunnel for agent-remote-access
# This exposes the local server (http://localhost:8000) to the internet

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Cloudflare Tunnel${NC}"
echo "=============================="

# Check if local servers are running
if ! lsof -ti:8000 >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: No server detected on port 8000${NC}"
    echo "Make sure to run ./start.sh first in another terminal"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Check if cloudflared is already running
if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
    echo -e "${YELLOW}Cloudflared tunnel is already running${NC}"
    read -p "Kill it and restart? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "cloudflared tunnel"
        sleep 2
    else
        echo "Exiting"
        exit 0
    fi
fi

echo -e "${GREEN}Starting tunnel with TryCloudflare (free public URL)...${NC}"
echo ""
echo "The tunnel will give you a public URL like:"
echo "  https://random-words.trycloudflare.com"
echo ""
echo "Extracting tunnel URL and sending email notification..."
echo ""

# Run TryCloudflare and capture output
cloudflared tunnel --url http://localhost:8000 2>&1 | tee /tmp/cloudflared-output.log | while IFS= read -r line; do
    echo "$line"

    # Extract tunnel URL from output
    if echo "$line" | grep -q "https://.*\.trycloudflare\.com"; then
        TUNNEL_URL=$(echo "$line" | grep -o "https://[^[:space:]]*\.trycloudflare\.com")
        if [ -n "$TUNNEL_URL" ]; then
            echo ""
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}Tunnel URL: $TUNNEL_URL${NC}"
            echo -e "${GREEN}========================================${NC}"
            echo ""

            # Send email notification (async, don't block tunnel)
            python3 "$SCRIPT_DIR/send-tunnel-email.py" "$TUNNEL_URL" &
        fi
    fi
done
