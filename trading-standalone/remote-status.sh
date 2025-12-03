#!/bin/bash
# ===========================================
# Magellan Trading Remote Status Viewer
# ===========================================
# 远程查看服务器交易状态的脚本

SERVER="45.76.159.149"
PORT="8000"
BASE_URL="http://${SERVER}:${PORT}/api/trading"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Magellan Trading - Remote Status                     ║${NC}"
echo -e "${BLUE}║  Server: ${SERVER}:${PORT}                          ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check connectivity
echo -e "${YELLOW}Checking server connectivity...${NC}"
if ! curl -s --connect-timeout 5 "${BASE_URL}/status" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to server ${SERVER}:${PORT}${NC}"
    echo "Please check:"
    echo "  1. Server is running"
    echo "  2. Port 8000 is open in firewall"
    echo "  3. Network connectivity"
    exit 1
fi
echo -e "${GREEN}Connected!${NC}"
echo ""

# ===== System Status =====
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  1. SYSTEM STATUS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
status=$(curl -s "${BASE_URL}/status" 2>/dev/null)
if [ -n "$status" ]; then
    echo "$status" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f\"  Initialized:    {d.get('initialized', 'N/A')}\")
    print(f\"  Enabled:        {d.get('enabled', 'N/A')}\")
    print(f\"  Demo Mode:      {d.get('demo_mode', 'N/A')}\")
    print(f\"  Symbol:         {d.get('symbol', 'N/A')}\")
    print(f\"  Trader Type:    {d.get('trader_type', 'N/A')}\")

    scheduler = d.get('scheduler', {})
    if scheduler:
        print(f\"  Scheduler:      {scheduler.get('state', 'N/A')}\")
        print(f\"  Next Run:       {scheduler.get('next_run', 'N/A')}\")
        print(f\"  Run Count:      {scheduler.get('run_count', 0)}\")

    cooldown = d.get('cooldown', {})
    if cooldown:
        print(f\"  In Cooldown:    {cooldown.get('in_cooldown', False)}\")
        print(f\"  Consec Losses:  {cooldown.get('consecutive_losses', 0)}\")
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null || echo "$status" | python3 -m json.tool 2>/dev/null || echo "$status"
else
    echo -e "  ${RED}Unable to get status${NC}"
fi
echo ""

# ===== Account Info =====
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  2. ACCOUNT INFO${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
account=$(curl -s "${BASE_URL}/account" 2>/dev/null)
if [ -n "$account" ]; then
    echo "$account" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    balance = d.get('balance', d.get('total_balance', 0))
    available = d.get('available_balance', d.get('available', 0))
    equity = d.get('equity', d.get('total_equity', balance))
    pnl = d.get('unrealized_pnl', 0)
    print(f\"  Balance:        \${balance:,.2f} USDT\")
    print(f\"  Available:      \${available:,.2f} USDT\")
    print(f\"  Equity:         \${equity:,.2f} USDT\")
    print(f\"  Unrealized PnL: \${pnl:+,.2f} USDT\")
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null || echo "$account" | python3 -m json.tool 2>/dev/null || echo "$account"
else
    echo -e "  ${RED}Unable to get account info${NC}"
fi
echo ""

# ===== Current Position =====
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  3. CURRENT POSITION${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
position=$(curl -s "${BASE_URL}/position" 2>/dev/null)
if [ -n "$position" ]; then
    echo "$position" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    has_pos = d.get('has_position', False)
    if has_pos:
        direction = d.get('direction', d.get('side', 'N/A'))
        entry = d.get('entry_price', 0)
        current = d.get('current_price', d.get('mark_price', 0))
        size = d.get('size', d.get('position_size', 0))
        leverage = d.get('leverage', 1)
        pnl = d.get('unrealized_pnl', 0)
        pnl_pct = d.get('unrealized_pnl_percent', d.get('pnl_percent', 0))
        pos_pct = d.get('position_percent', 0)
        tp = d.get('take_profit_price', d.get('tp_price', 'N/A'))
        sl = d.get('stop_loss_price', d.get('sl_price', 'N/A'))

        color = '\\033[0;32m' if pnl >= 0 else '\\033[0;31m'
        nc = '\\033[0m'

        print(f\"  Direction:      {direction.upper()}\")
        print(f\"  Entry Price:    \${entry:,.2f}\")
        print(f\"  Current Price:  \${current:,.2f}\")
        print(f\"  Size:           {size}\")
        print(f\"  Leverage:       {leverage}x\")
        print(f\"  Position:       {pos_pct:.1f}%\")
        print(f\"  Take Profit:    \${tp:,.2f}\" if isinstance(tp, (int, float)) else f\"  Take Profit:    {tp}\")
        print(f\"  Stop Loss:      \${sl:,.2f}\" if isinstance(sl, (int, float)) else f\"  Stop Loss:      {sl}\")
        print(f\"  Unrealized PnL: {color}\${pnl:+,.2f} ({pnl_pct:+.2f}%){nc}\")
    else:
        print('  No open position')
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null || echo "$position" | python3 -m json.tool 2>/dev/null || echo "$position"
else
    echo -e "  ${RED}Unable to get position${NC}"
fi
echo ""

# ===== Trade History =====
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  4. TRADE HISTORY (Last 10)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
history=$(curl -s "${BASE_URL}/history?limit=10" 2>/dev/null)
if [ -n "$history" ]; then
    echo "$history" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    trades = d.get('trades', [])
    signals = d.get('signals', [])

    if trades:
        print('  === Closed Trades ===')
        for i, t in enumerate(trades[-10:], 1):
            direction = t.get('direction', t.get('side', 'N/A'))
            entry = t.get('entry_price', 0)
            exit_p = t.get('exit_price', t.get('close_price', 0))
            pnl = t.get('pnl', t.get('realized_pnl', 0))
            reason = t.get('reason', t.get('close_reason', 'N/A'))
            ts = t.get('timestamp', t.get('close_time', 'N/A'))

            color = '\\033[0;32m' if pnl >= 0 else '\\033[0;31m'
            nc = '\\033[0m'

            print(f\"  {i}. {direction.upper():5} | Entry: \${entry:,.2f} -> Exit: \${exit_p:,.2f} | {color}PnL: \${pnl:+,.2f}{nc} | {reason}\")
    else:
        print('  No closed trades yet')

    print('')

    if signals:
        print('  === Recent Signals ===')
        for i, s in enumerate(signals[-5:], 1):
            sig = s.get('signal', {})
            direction = sig.get('direction', 'N/A')
            confidence = sig.get('confidence', 0)
            status = s.get('status', 'N/A')
            ts = s.get('timestamp', 'N/A')[:19] if s.get('timestamp') else 'N/A'
            print(f\"  {i}. {direction.upper():5} | Confidence: {confidence:.0%} | Status: {status} | {ts}\")
    else:
        print('  No signals recorded yet')

except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null || echo "$history" | python3 -m json.tool 2>/dev/null || echo "$history"
else
    echo -e "  ${RED}Unable to get trade history${NC}"
fi
echo ""

# ===== Equity History =====
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  5. EQUITY TREND${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
equity=$(curl -s "${BASE_URL}/equity?limit=20" 2>/dev/null)
if [ -n "$equity" ]; then
    echo "$equity" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    data = d.get('data', [])
    if data:
        first = data[0].get('equity', data[0].get('value', 0)) if data else 0
        last = data[-1].get('equity', data[-1].get('value', 0)) if data else 0
        change = last - first
        change_pct = (change / first * 100) if first > 0 else 0

        color = '\\033[0;32m' if change >= 0 else '\\033[0;31m'
        nc = '\\033[0m'

        print(f\"  Data Points:    {len(data)}\")
        print(f\"  Start Equity:   \${first:,.2f}\")
        print(f\"  Current Equity: \${last:,.2f}\")
        print(f\"  Change:         {color}\${change:+,.2f} ({change_pct:+.2f}%){nc}\")
    else:
        print('  No equity data yet')
except Exception as e:
    print(f'  Error parsing: {e}')
" 2>/dev/null || echo "  No equity data"
else
    echo -e "  ${RED}Unable to get equity history${NC}"
fi
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Local Time:  $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BLUE}  UTC Time:    $(date -u '+%Y-%m-%d %H:%M:%S UTC')${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Note: Next Run time is in server timezone (likely UTC)${NC}"
