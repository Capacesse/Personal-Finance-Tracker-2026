import { test, expect, SAMPLE } from './fixtures';

test.describe('Dashboard on first load', () => {
  test('builds demo data and loads without errors', async ({ dashboard }) => {
    // No database exists when the server starts. The app must create one
    // from the sample CSV instead of stopping at "No database found".
    await expect(dashboard.heading).toBeVisible();
    await expect(dashboard.totalTransactions).toHaveText(
      new RegExp(`${SAMPLE.totalTransactions} total transactions`),
    );
  });

  test('KPI tiles match values calculated from the sample CSV', async ({ dashboard }) => {
    await expect(dashboard.kpi('Total Spent')).toHaveText(SAMPLE.totalSpent);
    await expect(dashboard.kpi('Total Income')).toHaveText(SAMPLE.totalIncome);
    await expect(dashboard.kpi('Net Flow')).toHaveText(SAMPLE.netFlow);
    await expect(dashboard.kpi('Unique Merchants')).toHaveText(String(SAMPLE.expenseRows));
  });

  test('sample data is dated January 2025 only', async ({ dashboard }) => {
    // Regression check for the date bug: ISO dates were read day-first,
    // which spread these January transactions across twelve months.
    await expect(dashboard.selectedTags('Month(s)')).toHaveText(['2025-01']);
    await expect(dashboard.summaryCaption).toContainText('2025-01');
  });

  test('every transaction is categorised', async ({ dashboard, page }) => {
    await expect(page.getByText('All transactions are categorised.')).toBeVisible();
  });

  test('all charts render', async ({ page, dashboard }) => {
    const charts = page.getByTestId('stPlotlyChart');
    await expect(charts).toHaveCount(7);
    await expect(charts.first().locator('.main-svg').first()).toBeVisible();
  });
});
