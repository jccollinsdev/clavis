#!/bin/bash
# Start Clavis development environment

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd $SCRIPT_DIR

echo "Starting Clavis services..."

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "Warning: backend/.env not found. Copy .env.example to .env and fill in your keys."
fi

# Start docker services
echo "Starting Docker containers..."
docker compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 3

# Check status
echo ""
echo "Services status:"
docker compose ps

echo ""
echo "Clavis is running!"
echo "  - Backend API: http://localhost:8000"
echo "  - Backend docs: http://localhost:8000/docs"
echo "  - MiroFish: http://localhost:8001"
echo ""
echo "To start Cloudflare Tunnel (for mobile testing on cellular):"
echo "  cloudflared tunnel --config ~/.cloudflared/config.yml run"
echo ""
echo "To view logs:"
echo "  docker compose logs -f backend"
