#!/bin/bash
# Test Trading API endpoints
# 测试交易API端点

SERVER="http://45.76.159.149:8000"

echo "=== Testing Trading API ==="
echo ""

echo "1. Account Info:"
curl -s "$SERVER/api/trading/account" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Balance: \${data.get('available_balance', 0):,.2f}\")
print(f\"  Equity:  \${data.get('total_equity', 0):,.2f}\")
print(f\"  Used Margin: \${data.get('used_margin', 0):,.2f}\")
print(f\"  Unrealized PnL: \${data.get('unrealized_pnl', 0):,.2f}\")
"
echo ""

echo "2. Current Position:"
curl -s "$SERVER/api/trading/position" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('has_position'):
    print(f\"  Direction: {data.get('direction', 'N/A').upper()}\")
    print(f\"  Entry: \${data.get('entry_price', 0):,.2f}\")
    print(f\"  Current: \${data.get('current_price', 0):,.2f}\")
    print(f\"  TP: \${data.get('take_profit_price', 0):,.2f}\")
    print(f\"  SL: \${data.get('stop_loss_price', 0):,.2f}\")
    print(f\"  Unrealized PnL: \${data.get('unrealized_pnl', 0):,.2f} ({data.get('unrealized_pnl_percent', 0):.2f}%)\")
else:
    print('  No position')
"
echo ""

echo "3. Recent Signals:"
curl -s "$SERVER/api/trading/history?limit=5" | python3 -c "
import sys, json
from datetime import datetime
data = json.load(sys.stdin)
signals = data.get('signals', [])
if signals:
    for s in signals[-3:]:  # Last 3 signals
        ts = s.get('timestamp', '').split('.')[0] if s.get('timestamp') else 'N/A'
        sig = s.get('signal', {})
        direction = sig.get('direction', 'N/A') if sig else 'N/A'
        confidence = sig.get('confidence', 0) if sig else 0
        status = s.get('status', 'N/A')
        print(f\"  [{ts}] {direction.upper()} @ {confidence}% - {status}\")
else:
    print('  No signals yet')
"
echo ""

echo "4. Closed Trades:"
curl -s "$SERVER/api/trading/history?limit=5" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
if trades:
    for t in trades:
        direction = t.get('direction', 'N/A')
        pnl = t.get('pnl', 0)
        print(f\"  {direction.upper()}: PnL = \${pnl:,.2f}\")
else:
    print('  No closed trades yet')
"
echo ""

echo "=== Test Complete ==="
