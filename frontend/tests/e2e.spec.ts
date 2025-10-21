// tests/e2e.spec.ts
import { test, expect } from '@playwright/test';

// Define the base URL for the frontend application
const VITE_URL = 'http://localhost:5173';

test.describe('AI Investment Agent E2E Test (WebSocket)', () => {
  
  test('should display real-time steps and complete the journey to the interactive report', async ({ page }) => {
    // Increase the timeout for the entire test
    test.setTimeout(120000); // 2 minutes

    // 1. Navigate to the application
    await page.goto(VITE_URL);
    await expect(page.locator('text=您好！我是您的AI投资分析师。')).toBeVisible();

    // 2. Start a new session, which will trigger the WebSocket connection
    await page.locator('input[placeholder*="开始分析"]').fill('Apple');
    await page.locator('input[placeholder*="开始分析"]').press('Enter');

    // 3. Verify the real-time steps appear one by one
    await expect(page.locator('div.node-header:has-text("Fetching user persona")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('div.node-header:has-text("Fetching public data for \'Apple\'")')).toBeVisible();

    // 4. Handle the first HITL node (Ambiguity Resolution)
    const optionButton = page.locator('button:has-text("Apple Inc"):has-text("(AAPL)")');
    await expect(optionButton).toBeVisible({ timeout: 30000 });
    await optionButton.click();

    // 5. Verify continuation and subsequent real-time steps
    await expect(page.locator('div.node-header:has-text("Fetching confirmed data for AAPL")')).toBeVisible();
    await expect(page.locator('div.node-header:has-text("Generating initial analysis with Gemini")')).toBeVisible({ timeout: 45000 });
    await expect(page.locator('div.node-header:has-text("Fetching financial summary for chart")')).toBeVisible({ timeout: 45000 });
    await expect(page.locator('div.node-header:has-text("Generating key follow-up questions")')).toBeVisible({ timeout: 45000 });

    // 6. Wait for the second HITL node (Follow-up Questions)
    const viewReportButton = page.locator('button:has-text("立即查看报告")');
    await expect(viewReportButton).toBeVisible({ timeout: 30000 });
    
    // 7. Click the button to view the interactive report
    await viewReportButton.click();

    // 8. Verify the view has switched to the Interactive Report Dashboard
    await expect(page.locator('h1:has-text("投资分析报告: AAPL")')).toBeVisible();
    
    // 9. Verify the key sections of the report are present
    await expect(page.locator('h2:has-text("Preliminary Analysis")')).toBeVisible();
    await expect(page.locator('h2:has-text("Financial Analysis")')).toBeVisible();
    await expect(page.locator('h3:has-text("Agent 助手")')).toBeVisible();
    await expect(page.locator('h4:has-text("关键追问")')).toBeVisible();

    // 10. Verify the ECharts chart has been rendered in the correct section
    const financialSection = page.locator('div.report-section:has(h2:has-text("Financial Analysis"))');
    const chartCanvas = financialSection.locator('canvas');
    await expect(chartCanvas).toBeVisible();
    await expect(chartCanvas).toHaveAttribute('data-zr-dom-id');
  });

});
