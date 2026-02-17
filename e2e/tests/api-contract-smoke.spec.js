import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `e2e_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

async function assertJsonApi(request, path, headers, allowedStatus = [200]) {
  const res = await request.get(path, { headers });
  expect(allowedStatus).toContain(res.status());
  const contentType = res.headers()['content-type'] || '';
  expect(contentType).toContain('application/json');
  const body = await res.json();
  expect(body).toBeTruthy();
}

test('API contracts: core frontend APIs always return JSON (not HTML fallback)', async ({ page, request }) => {
  const email = uniqueEmail();
  const password = 'Password123!';

  await page.goto('/register', { waitUntil: 'domcontentloaded' });
  await page.locator('#name').fill('E2E User');
  await page.locator('#email').fill(email);
  await page.locator('#organization').fill('E2E');
  await page.locator('#password').fill(password);
  await page.locator('#confirmPassword').fill(password);
  await page.locator('#terms').check();
  await page.locator('form button[type="submit"]').click();
  await expect(page).not.toHaveURL(/\/register$/);

  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();
  const authHeaders = { Authorization: `Bearer ${token}` };

  await assertJsonApi(request, '/api/dashboard/stats', authHeaders);
  await assertJsonApi(request, '/api/reports', authHeaders);
  await assertJsonApi(request, '/api/v2/analysis/scenarios', authHeaders);
  await assertJsonApi(request, '/api/agents', authHeaders);

  // Knowledge APIs may degrade when vector service is unavailable; but must still be JSON.
  await assertJsonApi(request, '/api/knowledge/documents', authHeaders, [200, 503]);
  await assertJsonApi(request, '/api/knowledge/stats', authHeaders, [200, 503]);
});
