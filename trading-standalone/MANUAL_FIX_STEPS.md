# Manual Fix Steps for Remote Server

If `remote_fix_and_deploy.sh` doesn't work, run these commands manually:

## Step 1: Stop Everything
```bash
cd /root/trading-standalone
docker-compose down -v
```

## Step 2: Complete Redis Cleanup
```bash
# Delete Redis data files
find . -name "dump.rdb" -delete
find . -name "appendonly.aof" -delete

# Remove Redis data directory
rm -rf data/redis
mkdir -p data/redis
chmod 755 data/redis

# Clean Docker volumes
docker volume ls -q | grep redis | xargs docker volume rm 2>/dev/null
docker system prune -f --volumes
```

## Step 3: Pull Latest Code
```bash
# Check current status
git status
git log --oneline -3

# Pull latest from exp branch
git fetch origin exp
git pull origin exp

# Verify updates
git log --oneline -3
# Should show:
# 89300a5 - Tool description improvements
# e87aa54 - Leader tools reduction
# bad3a1d - Status.html improvements
# 87f3772 - TP/SL display fix
```

## Step 4: Verify status.html Updated
```bash
# Check for "Recent Signals" (not "Recent Trades")
grep "Recent Signals" status.html

# Check for TP/SL fix
grep "take_profit_price" status.html

# Both should return matching lines if updated correctly
```

## Step 5: Start Services
```bash
./start.sh
```

## Step 6: Wait and Check Status
```bash
# Wait for services to start
sleep 15

# Check all containers
docker-compose ps

# Should see all services "Up" and "healthy"
```

## Step 7: Check Redis Specifically
```bash
# Check Redis container
docker ps | grep redis

# Check Redis logs (should show "Ready to accept connections")
docker logs trading-redis --tail 20
```

## Step 8: Check Trading Service
```bash
# Check trading service logs
docker logs trading-service --tail 20

# Should NOT show errors about Redis connection
```

## Step 9: Test Dashboard
```bash
# Test API
curl -s http://localhost:8000/api/trading/status | python3 -m json.tool

# Test dashboard HTML
curl -s http://localhost:8000/api/trading/dashboard | grep "Recent Signals"

# Should return a line containing "Recent Signals"
```

## Step 10: Verify in Browser
1. Open: http://45.76.159.149:8000/api/trading/dashboard
2. Press `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac) to hard refresh
3. Verify:
   - Title says "Recent Signals" (not "Recent Trades")
   - TP/SL shows numbers like "$95000 / $85000" (not "$N/A / $N/A")
   - Confidence shows "55%" (not "5500%" or wrong format)

---

## If Redis Still Fails

### Check Redis Logs for Specific Error
```bash
docker logs trading-redis 2>&1 | tail -50
```

### Common Issues:

#### Issue 1: "Wrong signature trying to load DB from file"
**Solution**: Redis database file corrupted, need deeper cleanup
```bash
docker-compose down -v
find /root/trading-standalone -name "*.rdb" -o -name "*.aof" | xargs rm -f
find /var/lib/docker/volumes -name "*.rdb" 2>/dev/null | xargs sudo rm -f 2>/dev/null
docker system prune -af --volumes
./start.sh
```

#### Issue 2: "Permission denied"
**Solution**: Fix data directory permissions
```bash
sudo chown -R 999:999 data/redis
chmod 755 data/redis
docker-compose restart redis
```

#### Issue 3: "Address already in use"
**Solution**: Kill process using Redis port
```bash
lsof -i :6379
# Note the PID
kill -9 <PID>
docker-compose restart redis
```

#### Issue 4: "Volume is in use"
**Solution**: Force remove volumes
```bash
docker-compose down
docker volume rm $(docker volume ls -q | grep redis) -f
./start.sh
```

---

## Verification Checklist

After all steps:

- [ ] `docker-compose ps` shows all services "Up (healthy)"
- [ ] `docker logs trading-redis` shows "Ready to accept connections"
- [ ] `docker logs trading-service` has NO Redis connection errors
- [ ] `curl localhost:8000/api/trading/status` returns JSON
- [ ] `curl localhost:8000/api/trading/dashboard | grep "Recent Signals"` returns match
- [ ] Browser shows "Recent Signals" section
- [ ] Browser shows TP/SL with numbers (not N/A)
- [ ] Browser shows correct confidence percentage

---

## If Dashboard Still Shows Old Version

### Solution 1: Clear Browser Cache
1. Open Developer Tools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Solution 2: Use Incognito/Private Mode
1. Open incognito/private browsing window
2. Navigate to http://45.76.159.149:8000/api/trading/dashboard
3. Should show updated version

### Solution 3: Restart Trading Service
```bash
docker-compose restart trading-service
sleep 5
curl http://localhost:8000/api/trading/dashboard | head -50
```

### Solution 4: Check if status.html is correct file
```bash
# Find where status.html is being served from
docker exec trading-service find / -name "status.html" 2>/dev/null

# Compare with your local version
md5sum status.html
docker exec trading-service md5sum /path/to/status.html
# Checksums should match
```

---

## After Everything Works

Test that Leader only has 4 tools:
```bash
# Restart report_orchestrator to apply trading_agents.py changes
docker-compose restart report_orchestrator

# Wait for startup
sleep 10

# Check logs for tool registration
docker-compose logs report_orchestrator | grep "Registered.*tools"

# Should see:
# "Registered 11 analysis tools to TechnicalAnalyst"
# "Registered 11 analysis tools to MacroEconomist"
# ...
# "Registered 4 execution tools to Leader (no analysis tools needed)"
```

Then test DeepSeek compatibility (optional):
```bash
# Backup current config
cp .env .env.gemini

# Change to DeepSeek
sed -i 's/DEFAULT_LLM_PROVIDER=gemini/DEFAULT_LLM_PROVIDER=deepseek/' .env

# Restart
docker-compose restart report_orchestrator
sleep 10

# Trigger analysis
curl -X POST http://localhost:8000/api/trading/trigger

# Wait and check for 500 errors
sleep 45
docker-compose logs --tail=100 report_orchestrator | grep -E "500|error|Leader"

# If still fails, revert to Gemini
cp .env.gemini .env
docker-compose restart report_orchestrator
```
