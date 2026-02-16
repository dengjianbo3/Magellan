import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `e2e_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

test('Analysis V2: scenario list is real (no mock fallback) and can proceed', async ({ page }) => {
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

  // Analysis wizard
  await page.goto('/analysis');

  // Ensure we do not show the old demo/mock warning banner.
  await expect(page.getByText(/demo data/i)).toHaveCount(0);

  // At least one scenario card exists (early-stage should be available).
  await expect(page.getByText(/早期.*投资|Early.*Stage/i)).toBeVisible();

  // Select the first scenario card and proceed.
  await page.getByText(/早期.*投资|Early.*Stage/i).first().click();
  await page.getByRole('button', { name: /下一步|Next/i }).click();

  // Next step should render some input fields (best-effort).
  await expect(page.locator('input').first()).toBeVisible();
});
