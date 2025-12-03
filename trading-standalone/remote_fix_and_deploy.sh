#!/bin/bash

echo "=== Remote Server Fix and Deployment Script ==="
echo ""

# Step 1: Stop all services
echo "Step 1: Stopping all services..."
docker-compose down -v
sleep 3

# Step 2: Find and remove all Redis data files
echo ""
echo "Step 2: Cleaning Redis data files..."
find . -name "dump.rdb" -type f -delete 2>/dev/null
find . -name "appendonly.aof" -type f -delete 2>/dev/null
echo "Deleted Redis database files"

# Step 3: Remove Redis data directory completely
echo ""
echo "Step 3: Removing Redis data directory..."
rm -rf data/redis
mkdir -p data/redis
chmod 755 data/redis
echo "Redis data directory recreated"

# Step 4: Check for Redis volumes and remove them
echo ""
echo "Step 4: Cleaning Docker volumes..."
docker volume ls -q | grep -i redis | xargs -r docker volume rm 2>/dev/null || echo "No Redis volumes found"
docker system prune -f --volumes 2>&1 | grep -E "Total|deleted"

# Step 5: Verify git status and pull latest code
echo ""
echo "Step 5: Updating code from git..."
git fetch origin exp
git status
echo ""
echo "Current commits:"
git log --oneline -3
echo ""

read -p "Do you want to pull latest code? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git pull origin exp
    echo "Code updated"
else
    echo "Skipped git pull"
fi

# Step 6: Verify status.html was updated
echo ""
echo "Step 6: Verifying status.html contains fixes..."
if grep -q "Recent Signals" status.html; then
    echo "✅ status.html contains 'Recent Signals' (GOOD)"
else
    echo "❌ status.html still has old version (BAD)"
fi

if grep -q "take_profit_price" status.html; then
    echo "✅ status.html has TP/SL fix (GOOD)"
else
    echo "❌ status.html missing TP/SL fix (BAD)"
fi

# Step 7: Start services
echo ""
echo "Step 7: Starting services..."
./start.sh

# Wait for services to start
echo ""
echo "Waiting 15 seconds for services to start..."
sleep 15

# Step 8: Check service health
echo ""
echo "Step 8: Checking service status..."
docker-compose ps

echo ""
echo "=== Redis Container Status ==="
docker ps -a | grep redis
echo ""
docker logs trading-redis --tail 10

# Step 9: Verify trading service
echo ""
echo "=== Trading Service Status ==="
docker logs trading-service --tail 10 2>&1 | grep -E "Starting|error|Error|Listening"

# Step 10: Test API endpoints
echo ""
echo "Step 9: Testing API endpoints..."
echo "Testing /api/trading/status:"
curl -s http://localhost:8000/api/trading/status | python3 -c "import sys,json; data=json.load(sys.stdin); print(f\"  Enabled: {data.get('enabled')}\")" 2>/dev/null || echo "  ❌ API not responding"

echo ""
echo "Testing /api/trading/dashboard (status.html):"
DASHBOARD=$(curl -s http://localhost:8000/api/trading/dashboard)
if echo "$DASHBOARD" | grep -q "Recent Signals"; then
    echo "  ✅ Dashboard shows 'Recent Signals'"
else
    echo "  ❌ Dashboard still shows old version"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Open browser: http://45.76.159.149:8000/api/trading/dashboard"
echo "2. Press Ctrl+Shift+R to hard refresh"
echo "3. Verify you see:"
echo "   - 'Recent Signals' section (not 'Recent Trades')"
echo "   - TP/SL values showing numbers (not N/A)"
echo "   - Confidence showing correct percentage"
echo ""
echo "If dashboard still shows old version:"
echo "  - Clear browser cache completely"
echo "  - Try incognito/private browsing mode"
echo "  - Check docker logs trading-service for errors"
