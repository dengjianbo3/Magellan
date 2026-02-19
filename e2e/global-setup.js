import { setTimeout as delay } from 'node:timers/promises';

async function waitForHttpStatus(url, acceptedStatuses = [200], timeoutMs = 60_000) {
  const start = Date.now();
  let lastErr = null;
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { method: 'GET' });
      if (acceptedStatuses.includes(res.status)) return;
      lastErr = new Error(`Non-OK ${res.status} for ${url}`);
    } catch (e) {
      lastErr = e;
    }
    await delay(500);
  }
  throw lastErr || new Error(`Timeout waiting for ${url}`);
}

export default async function globalSetup() {
  const baseURL = process.env.E2E_BASE_URL || 'http://localhost:8081';

  // Web (SPA) reachable
  await waitForHttpStatus(`${baseURL}/`, [200]);

  // Backend reachable via proxy (401 means endpoint is up and auth is enforced).
  await waitForHttpStatus(`${baseURL}/api/trading/status`, [200, 401]);
}
