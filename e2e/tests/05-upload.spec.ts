import { test, expect, SAMPLE } from './fixtures';

// These tests add rows to the shared database. They run last (file name order)
// and in sequence, because each one builds on the state the previous one left.
test.describe.configure({ mode: 'serial' });

test.describe('Uploading a bank statement', () => {
  test('a file that is not a bank statement is rejected with a clear message', async ({ dashboard, page }) => {
    await dashboard.uploadStatement('not_a_bank_statement.csv');

    // Regression check: this error used to be replaced straight away by a
    // green "Database updated successfully" message.
    await expect(page.getByText(/Unsupported CSV format/)).toBeVisible();
    await expect(page.getByText(/updated successfully|Processed successfully/)).toHaveCount(0);
    await expect(dashboard.totalTransactions).toHaveText(
      new RegExp(`${SAMPLE.totalTransactions} total transactions`),
    );
  });

  test('a valid statement adds its rows and the dashboard updates at once', async ({ dashboard, page }) => {
    await dashboard.uploadStatement('february_statement.csv');

    await expect(page.getByText('3 new transactions added. (0 duplicates skipped)')).toBeVisible();

    // Regression check: the dashboard used to keep showing old data after a
    // successful upload until its cache expired a minute later.
    await expect(dashboard.totalTransactions).toHaveText(/16 total transactions/);
    await expect(dashboard.selectedTags('Month(s)')).toHaveText(['2025-01', '2025-02']);
    await expect(dashboard.kpi('Total Income')).toHaveText('SGD 7,001.20');
  });

  test('uploading the same statement again adds nothing', async ({ dashboard, page }) => {
    await dashboard.uploadStatement('february_statement.csv');

    await expect(page.getByText('0 new transactions added. (3 duplicates skipped)')).toBeVisible();
    await expect(dashboard.totalTransactions).toHaveText(/16 total transactions/);
  });

  test('selecting one month shows only that month', async ({ dashboard }) => {
  // Arrange: the database now holds January (sample) and February (uploaded)
  await expect(dashboard.selectedTags('Month(s)')).toHaveText(['2025-01', '2025-02']);

  // Act: deselect January, leaving February only
  await dashboard.removeTag('Month(s)', '2025-01');

  // Assert: figures worked out by hand from fixtures/february_statement.csv
  //   spent  = 7.80 + 32.50 = 40.30
  //   income = 3,500.00
  await expect(dashboard.kpi('Total Spent')).toHaveText('SGD 40.30');
  await expect(dashboard.kpi('Total Income')).toHaveText('SGD 3,500.00');
  await expect(dashboard.summaryCaption).toContainText('Showing 2 expense transactions');
  });
});
