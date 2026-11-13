import fs from 'fs';
import { test, expect, SAMPLE } from './fixtures';

test.describe('Transaction log', () => {
  test.beforeEach(async ({ dashboard }) => {
    await dashboard.openTransactionLog();
  });

  test('newest transaction is listed first', async ({ dashboard }) => {
    await expect(dashboard.logCell(0, 0)).toHaveText('2025-01-15');
    await expect(dashboard.logCell(3, 0)).toHaveText('FOOD PANDA');
  });

  test('search filters by merchant, ignoring case', async ({ dashboard }) => {
    await dashboard.logSearch.fill('spotify');
    await dashboard.logSearch.press('Enter');

    await dashboard.expectLogRowCount(1);
    await expect(dashboard.logCell(3, 0)).toContainText('SPOTIFY');
  });

  test('search with no match shows an empty table', async ({ dashboard }) => {
    await dashboard.logSearch.fill('no such merchant');
    await dashboard.logSearch.press('Enter');

    await dashboard.expectLogRowCount(0);
  });

  test('export downloads the rows currently shown', async ({ dashboard, page }) => {
    const downloadPromise = page.waitForEvent('download');
    await dashboard.exportButton.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toBe('filtered_transactions.csv');

    const lines = fs.readFileSync(await download.path(), 'utf-8').trim().split(/\r?\n/);
    expect(lines[0]).toBe('Date,Amount (SGD),Code,Merchant,Category,Description');
    expect(lines).toHaveLength(1 + SAMPLE.expenseRowsWithTransfers); // header + rows
  });

  test('export respects the search box', async ({ dashboard, page }) => {
    await dashboard.logSearch.fill('netflix');
    await dashboard.logSearch.press('Enter');
    await dashboard.expectLogRowCount(1);

    const downloadPromise = page.waitForEvent('download');
    await dashboard.exportButton.click();
    const download = await downloadPromise;

    const lines = fs.readFileSync(await download.path(), 'utf-8').trim().split(/\r?\n/);
    expect(lines).toHaveLength(2);
    expect(lines[1]).toContain('NETFLIX.COM');
    expect(lines[1]).toContain('-15.98');
  });

  test('search finds a transaction by its description, not only its merchant name', async ({ dashboard }) => {
    // "xtra" is in the raw description only; the cleaned merchant name is just FAIRPRICE
    await dashboard.logSearch.fill('xtra');
    await dashboard.logSearch.press('Enter');

    await dashboard.expectLogRowCount(1);
    await expect(dashboard.logCell(3, 0)).toHaveText('FAIRPRICE');
    await expect(dashboard.logCell(5, 0)).toContainText('XTRA');
  });
});
