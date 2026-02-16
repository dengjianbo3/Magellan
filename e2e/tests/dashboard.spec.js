import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `e2e_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

test('Dashboard: stats and recent reports reflect real reports API', async ({ page, request }) => {
  const email = uniqueEmail();
  const password = 'Password123!';

  // Register
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

  // Create a report via API
  const saveRes = await request.post('/api/reports', {
    data: {
      session_id: `dd_e2e_${Date.now()}`,
      project_name: 'E2E Report',
      company_name: 'E2E Co',
      analysis_type: 'due-diligence',
      steps: [],
      status: 'completed'
    }
  });
  expect(saveRes.ok()).toBeTruthy();

  // Reload dashboard so it refetches.
  await page.goto('/');

  // Assert stats card shows at least 1 report.
  const heading = page.getByRole('heading', { name: /总报告数|Total Reports/i });
  await expect(heading).toBeVisible();
  const card = heading.locator('xpath=ancestor::div[contains(@class,\"glass-card\")][1]');
  const value = card.locator('p').first();
  await expect(value).not.toHaveText('-');
  await expect(value).not.toHaveText('0');

  // Recent reports section should exist.
  await expect(page.getByRole('heading', { name: /最近报告|Recent Reports/i })).toBeVisible();
});
