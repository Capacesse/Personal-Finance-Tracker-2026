import { test, expect } from './fixtures';

test.describe('Budget editor', () => {
  test('saved budget is still there after the page is reloaded', async ({ dashboard, page }) => {
    await dashboard.expectBudget('Transport', 0);
    await dashboard.setBudget('Transport', 30);
    await dashboard.saveBudgets();
    
    // Reload to prove the change is in the database, not just on screen.
    await page.reload();
    await expect(dashboard.heading).toBeVisible();
    await dashboard.expectBudget('Transport', 30);
  });
});
