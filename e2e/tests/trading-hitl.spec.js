import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `e2e_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

async function waitForPositionOpen(request, headers, timeoutMs = 15_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const res = await request.get('/api/trading/position', { headers });
    if (res.ok()) {
      const body = await res.json();
      if (body?.has_position) return body;
    }
    await new Promise(r => setTimeout(r, 250));
  }
  throw new Error('Timed out waiting for position to open');
}

test('Trading HITL: pending -> confirm -> TP close', async ({ page, request }) => {
  // Avoid flakiness from public Binance endpoints used by the UI for benchmarks.
  await page.route('https://api.binance.com/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/api/v3/ticker/price')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ symbol: 'BTCUSDT', price: '40000.00' })
      });
    }
    if (url.includes('/api/v3/klines')) {
      // Minimal 1h kline response format: [openTime, open, high, low, close, volume, ...]
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([[Date.now() - 3600_000, '40000.00', '40100.00', '39900.00', '40050.00', '0']])
      });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  const email = uniqueEmail();
  const password = 'Password123!';

  // Register via UI (also validates auth UI + proxy).
  await page.goto('/register');
  await page.locator('#name').fill('E2E User');
  await page.locator('#email').fill(email);
  await page.locator('#organization').fill('E2E');
  await page.locator('#password').fill(password);
  await page.locator('#confirmPassword').fill(password);
  await page.locator('#terms').check();
  await page.locator('form button[type="submit"]').click();

  // Land in authenticated area.
  await expect(page).not.toHaveURL(/\/register$/);
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();
  const authHeaders = { Authorization: `Bearer ${token}` };

  // Clean state for determinism.
  await request.post('/api/trading/reset', { headers: authHeaders, data: {} });

  // Trading page.
  await page.goto('/trading');
  await expect(page.getByText('当前持仓')).toBeVisible();

  // Create a pending trade through the backend mock hook.
  const createRes = await request.post(
    '/api/trading/mock/create-pending?symbol=BTC-USDT-SWAP&direction=long&leverage=2&amount_percent=0.2&tp_percent=1.0&sl_percent=1.0',
    { headers: authHeaders },
  );
  expect(createRes.ok()).toBeTruthy();
  const created = await createRes.json();
  expect(created.success).toBeTruthy();

  // Pending trades alert appears and opens decision modal.
  const pendingBtn = page.getByRole('button').filter({ hasText: '待办' });
  await expect(pendingBtn).toBeVisible();
  await pendingBtn.click();

  await expect(page.getByText('AI 投资委员会决策')).toBeVisible();
  await page.getByRole('button', { name: '确认执行' }).click();

  // Backend confirms position opened (UI can lag due to WS/polling).
  await waitForPositionOpen(request, authHeaders, 20_000);

  // Position should open.
  const positionPanel = page.getByText('当前持仓').locator('xpath=ancestor::div[contains(@class,\"glass-panel\")][1]');
  await expect(positionPanel.getByText('BTC-USDT-SWAP')).toBeVisible({ timeout: 30_000 });
  await expect(positionPanel.getByText('LONG 2x')).toBeVisible({ timeout: 30_000 });

  // Simulate TP hit to close the position.
  const tpRes = await request.post('/api/trading/mock/test-tp-sl?trigger_type=tp', { headers: authHeaders, data: {} });
  expect(tpRes.ok()).toBeTruthy();
  const tpPayload = await tpRes.json();
  expect(tpPayload.success).toBeTruthy();

  await expect(page.getByText('No open position')).toBeVisible();
});
