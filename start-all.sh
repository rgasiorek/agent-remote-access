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
echo "Press Ctrl+C to stop everything"
echo ""

# Start TryCloudflare tunnel in foreground (Ctrl+C will kill everything)
exec cloudflared tunnel --url http://localhost:8000
