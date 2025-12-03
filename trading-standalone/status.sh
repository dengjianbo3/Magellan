#!/bin/bash
# ===========================================
# Magellan Trading Standalone - Status Script
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Magellan Trading Standalone - Status     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Detect docker compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Docker service status
echo -e "${CYAN}=== Docker Services ===${NC}"
$DOCKER_COMPOSE ps
echo ""

# Check trading status
echo -e "${CYAN}=== Trading Status ===${NC}"
trading_status=$(curl -s http://localhost:8000/api/trading/status 2>/dev/null)

if [ -n "$trading_status" ]; then
    echo "$trading_status" | python3 -m json.tool 2>/dev/null || echo "$trading_status"
else
    echo -e "${YELLOW}Trading service not responding${NC}"
fi
echo ""

# Check scheduler status
echo -e "${CYAN}=== Scheduler Status ===${NC}"
scheduler_status=$(curl -s http://localhost:8000/api/trading/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"State: {d.get('scheduler',{}).get('state','unknown')}\"); print(f\"Next Run: {d.get('scheduler',{}).get('next_run','N/A')}\"); print(f\"Last Run: {d.get('scheduler',{}).get('last_run','N/A')}\"); print(f\"Run Count: {d.get('scheduler',{}).get('run_count',0)}\")" 2>/dev/null)

if [ -n "$scheduler_status" ]; then
    echo "$scheduler_status"
else
    echo -e "${YELLOW}Unable to get scheduler status${NC}"
fi
echo ""

# Check position
echo -e "${CYAN}=== Current Position ===${NC}"
position=$(curl -s http://localhost:8000/api/trading/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('position',{}); print(f\"Side: {p.get('side','None')}\"); print(f\"Size: {p.get('size',0)}\"); print(f\"Entry: \${p.get('entry_price',0):,.2f}\" if p.get('entry_price') else 'Entry: N/A'); print(f\"PnL: {p.get('unrealized_pnl',0):+.2f} USDT ({p.get('pnl_percent',0):+.2f}%)\" if p.get('unrealized_pnl') else 'PnL: N/A')" 2>/dev/null)

if [ -n "$position" ]; then
    echo "$position"
else
    echo -e "${YELLOW}No position data${NC}"
fi
echo ""

# Resource usage
echo -e "${CYAN}=== Resource Usage ===${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "trading|NAME"
echo ""

# Recent logs
echo -e "${CYAN}=== Recent Activity (last 5 lines) ===${NC}"
$DOCKER_COMPOSE logs --tail=5 trading_service 2>/dev/null | grep -v "^$" | tail -5
