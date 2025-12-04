#!/bin/bash
# Trading Service Diagnostic Script

echo "=== Trading Service Diagnostics ==="
echo ""

echo "1. Docker Container Status:"
docker ps -a | grep -E "CONTAINER|trading|redis|llm|web"
echo ""

echo "2. Trading Service Container Status:"
TRADING_CONTAINER=$(docker ps -a --filter "name=trading_service" --format "{{.ID}}")
if [ -z "$TRADING_CONTAINER" ]; then
    echo "❌ Trading service container not found!"
else
    echo "Container ID: $TRADING_CONTAINER"
    echo "Status: $(docker inspect -f '{{.State.Status}}' $TRADING_CONTAINER)"
    echo "Exit Code: $(docker inspect -f '{{.State.ExitCode}}' $TRADING_CONTAINER)"
fi
echo ""

echo "3. Trading Service Logs (last 50 lines):"
docker logs --tail 50 trading_service 2>&1 || echo "❌ Failed to get logs"
echo ""

echo "4. Port 8000 Status:"
netstat -tlnp | grep 8000 || echo "❌ Port 8000 not listening"
echo ""

echo "5. Redis Status:"
docker exec redis redis-cli ping 2>&1 || echo "❌ Redis not responding"
echo ""

echo "6. All Container Health:"
docker inspect --format='{{.Name}}: {{.State.Health.Status}}' $(docker ps -q) 2>/dev/null || echo "No health checks configured"
echo ""

echo "7. Recent Docker Events:"
docker events --since 5m --until 0s 2>&1 | tail -20 || echo "No recent events"
echo ""

echo "=== Quick Fix Suggestions ==="
echo "If trading_service crashed:"
echo "  1. Check logs: docker logs trading_service"
echo "  2. Restart: docker restart trading_service"
echo "  3. Full restart: ./stop.sh && ./start.sh"
echo ""
echo "If syntax error in Python code:"
echo "  1. Check recent commits: git log --oneline -3"
echo "  2. Check diff: git diff HEAD~1"
echo "  3. Rollback if needed: git reset --hard HEAD~1"
