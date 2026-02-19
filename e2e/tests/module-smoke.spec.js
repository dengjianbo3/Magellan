import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `e2e_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

async function assertJsonApi(request, path, headers, allowedStatus = [200]) {
  const res = await request.get(path, { headers });
  expect(allowedStatus).toContain(res.status());
  const contentType = res.headers()['content-type'] || '';
  expect(contentType).toContain('application/json');
  await res.json();
}

test('Module smoke: core APIs and pages are reachable after login', async ({ page, request }) => {
  const email = uniqueEmail();
  const password = 'Password123!';

  // Register and land in authenticated pages
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

  // API smoke by module
  await assertJsonApi(request, '/api/dashboard/stats', authHeaders);
  await assertJsonApi(request, '/api/reports', authHeaders);
  await assertJsonApi(request, '/api/v2/analysis/scenarios', authHeaders);
  await assertJsonApi(request, '/api/roundtable/history?limit=5', authHeaders);
  await assertJsonApi(request, '/api/agents', authHeaders);
  await assertJsonApi(request, '/api/knowledge/stats', authHeaders, [200, 503]);
  await assertJsonApi(request, '/api/trading/status', authHeaders);
  await assertJsonApi(request, '/api/trading/config', authHeaders);
  await assertJsonApi(request, '/api/auth/me', authHeaders);

  // UI smoke: pages should render and stay authenticated
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(String(err)));

  const routes = [
    '/',
    '/reports',
    '/analysis',
    '/roundtable',
    '/agents',
    '/knowledge',
    '/trading',
    '/settings',
  ];

  for (const route of routes) {
    await page.goto(route, { waitUntil: 'domcontentloaded' });
    await expect(page).not.toHaveURL(/\/login$/);
    await expect(page.locator('h1').first()).toBeVisible();
  }

  expect(pageErrors).toHaveLength(0);
});
