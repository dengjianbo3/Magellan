# Deployment Instructions

## 1. System Requirements Check

Ensure the remote server environment is ready:

- Docker & Docker Compose installed
- Python 3.11+ (if running outside Docker)
- Git access to the repository

## 2. Update Code

SSH into the remote server and pull the latest `dev` branch:

```bash
cd /path/to/magellan
git checkout dev
git pull origin dev
```

## 3. Configuration Check

Verify your `.env` file contains necessary keys for new features (no new keys strictly required, but ensure existing ones are valid):

```bash
# Verify API keys
cat .env | grep -E "OKX|GOOGLE|DEEPSEEK"
```

*Note: New `langgraph` dependency is handled inside Docker build.*

## 4. Rebuild and Restart Services

Since new dependencies (`langgraph`, `redis`) were added, you **MUST** rebuild the Docker images.

```bash
# Navigate to the standalone directory
cd trading-standalone

# Stop existing services
./stop.sh

# Rebuild and start (using --build is critical here)
docker compose up -d --build

# Verify startup
./status.sh
```

## 5. Validation

Check logs to ensure new modules initialized correctly:

```bash
# Should show "All Phase 1-4 modules imported" or similar initialization logs
./logs.sh trading | grep -E "SafetyGuard|TradeExecutor|TradingGraph"
```

## 6. Access Dashboard

Visit your server's dashboard (default port 8888) to confirm system status is "Running".

---

### Troubleshooting

If you see `ImportError: no module named langgraph`:

- You didn't rebuild the image. Run `docker compose build --no-cache` and try again.

If you see Redis connection errors:

- Ensure the `trading-redis` container is healthy: `docker compose ps`
