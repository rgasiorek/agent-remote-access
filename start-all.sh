#!/bin/bash

# Start everything: Local servers + Cloudflare Tunnel
# This is a convenience script to start the complete stack

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting Complete Agent Remote Access Stack${NC}"
echo "============================================="
echo ""

# Start local servers
echo "Step 1: Starting local servers..."
./start.sh || exit 1

echo ""
echo "Step 2: Starting Cloudflare tunnel (TryCloudflare - free public URL)..."
echo ""
echo "Look for the URL in the output below like:"
echo "  https://random-words.trycloudflare.com"
echo ""
echo "An email notification will be sent when the tunnel is ready."
echo ""
echo "Press Ctrl+C to stop everything"
echo ""

# Start TryCloudflare and capture/email the URL
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

            # Send email notification (async)
            python3 "$SCRIPT_DIR/send-tunnel-email.py" "$TUNNEL_URL" &
        fi
    fi
done
