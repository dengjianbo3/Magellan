#!/bin/bash
# ===========================================
# Magellan Trading Standalone - Stop Script
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Magellan Trading Standalone - Stop       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# First, try to stop trading gracefully
echo -e "${YELLOW}Stopping trading...${NC}"
curl -s -X POST http://localhost:8000/api/trading/stop 2>/dev/null || true
sleep 2

# Stop Docker services
echo -e "${YELLOW}Stopping Docker services...${NC}"
docker-compose down

echo ""
echo -e "${GREEN}All services stopped.${NC}"
