# E2E (Playwright)

This folder contains browser-level E2E tests using Playwright.

## Run (Docker, Recommended)

1. Build frontend assets:

```bash
npm --prefix frontend run build
```

2. Start services (backend + web + playwright runner):

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml up -d --build web
```

3. Run Playwright tests:

```bash
docker compose -f docker-compose.yml -f docker-compose.e2e.yml run --rm playwright
```

Notes:
- `docker-compose.e2e.yml` forces `USE_OKX_TRADING=false` for deterministic paper trading.
- The `web` reverse-proxies `/api/*` and `/api/trading/ws/*` to the backend containers.

## Run (Local)

If you prefer running Playwright on the host:

```bash
npm --prefix e2e install --no-audit --no-fund
E2E_BASE_URL=http://localhost:8081 npm --prefix e2e test
```
