import { setTimeout as delay } from 'node:timers/promises';

async function waitForHttpOk(url, timeoutMs = 60_000) {
  const start = Date.now();
  let lastErr = null;
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { method: 'GET' });
      if (res.ok) return;
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
  await waitForHttpOk(`${baseURL}/`);

  // Backend reachable via proxy
  await waitForHttpOk(`${baseURL}/api/trading/status`);
}
