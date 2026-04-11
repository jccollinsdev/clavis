#!/bin/bash
# Clavis Cloudflare Tunnel Setup
# Run this once to create a permanent tunnel for local development

set -e

TUNNEL_NAME="clavis-dev"
CREDENTIALS_FILE="$HOME/.cloudflared/clavis-dev.json"

echo "Creating Cloudflare Tunnel for Clavis local development..."

# Create tunnel
cloudflared tunnel create $TUNNEL_NAME 2>/dev/null || echo "Tunnel already exists or credentials found"

# Get tunnel credentials path
if [ -f "$CREDENTIALS_FILE" ]; then
    echo "Using existing credentials at $CREDENTIALS_FILE"
else
    # Find the credentials file
    CREDENTIALS_FILE=$(find $HOME/.cloudflared -name "*.json" -type f 2>/dev/null | head -1 || echo "")
    if [ -z "$CREDENTIALS_FILE" ]; then
        echo "Error: Could not find tunnel credentials. Run 'cloudflared tunnel create clavis-dev' manually."
        exit 1
    fi
    echo "Found credentials at $CREDENTIALS_FILE"
fi

# Create ingress rules for docker services
mkdir -p $HOME/.cloudflared
cat > $HOME/.cloudflared/config.yml << 'EOF'
tunnel: <TUNNEL_ID>
credentials-file: <CREDENTIALS_FILE>

ingress:
  - hostname: clavis-backend.trycloudflare.com
    service: http://localhost:8000
  - hostname: clavis-mirofish.trycloudflare.com
    service: http://localhost:8001
  - service: http_status:404
EOF

# Replace placeholder with actual tunnel ID
TUNNEL_ID=$(cat $CREDENTIALS_FILE | python3 -c "import sys,json; print(json.load(sys.stdin)['TunnelID'])" 2>/dev/null || echo "")
sed -i.bak "s/<TUNNEL_ID>/$TUNNEL_ID/g" $HOME/.cloudflared/config.yml
sed -i "s|<CREDENTIALS_FILE>|$CREDENTIALS_FILE|g" $HOME/.cloudflared/config.yml
rm -f $HOME/.cloudflared/config.yml.bak

echo ""
echo "Cloudflare Tunnel configured!"
echo ""
echo "To start the tunnel:"
echo "  cloudflared tunnel --config $HOME/.cloudflared/config.yml run"
echo ""
echo "Your services will be available at:"
echo "  - Backend API: https://clavis-backend.trycloudflare.com"
echo "  - MiroFish:   https://clavis-mirofish.trycloudflare.com"
