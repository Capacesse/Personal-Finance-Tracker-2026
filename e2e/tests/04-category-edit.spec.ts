import { test, expect } from './fixtures';

// These tests change data in the shared database, so they run in order and
// the last one puts the original value back.
test.describe.configure({ mode: 'serial' });

test.describe('Editing a category in the transaction log', () => {
  test('a new category is saved and survives a page reload', async ({ dashboard, page }) => {
    await dashboard.openTransactionLog();
    await dashboard.expectCategory('WATSONS', 'Health & Wellness');

    await dashboard.changeCategory('WATSONS', 'Shopping');

    // Reload to prove the change is in the database, not just on screen.
    await page.reload();
    await expect(dashboard.heading).toBeVisible();
    await dashboard.openTransactionLog();
    await dashboard.expectCategory('WATSONS', 'Shopping');
  });

  test('the new category appears in the sidebar filter', async ({ dashboard }) => {
    await expect(dashboard.selectedTags('Categories').filter({ hasText: 'Shopping' })).toHaveCount(1);
    await expect(dashboard.selectedTags('Categories').filter({ hasText: 'Health & Wellness' })).toHaveCount(0);
  });

  test('clean up: restore the original category', async ({ dashboard, page }) => {
    await dashboard.openTransactionLog();
    await dashboard.changeCategory('WATSONS', 'Health & Wellness');

    await page.reload();
    await expect(dashboard.heading).toBeVisible();
    await dashboard.openTransactionLog();
    await dashboard.expectCategory('WATSONS', 'Health & Wellness');
  });
});
