import { test, expect, SAMPLE } from './fixtures';

test.describe('Sidebar filters', () => {
  test('transfers and cash are hidden from spend by default', async ({ dashboard }) => {
    await expect(dashboard.summaryCaption).toContainText(`Showing ${SAMPLE.expenseRows} expense transactions`);
  });

  test('"Include Transfers" adds the top-up and the ATM withdrawal', async ({ dashboard }) => {
    await dashboard.setCheckbox('Include Transfers / PayNow', true);

    await expect(dashboard.summaryCaption).toContainText(
      `Showing ${SAMPLE.expenseRowsWithTransfers} expense transactions`,
    );
    await expect(dashboard.kpi('Unique Merchants')).toHaveText(String(SAMPLE.expenseRowsWithTransfers));
  });

  test('removing a category narrows the spend view', async ({ dashboard }) => {
    // The sample has three subscription payments: Spotify, Netflix, YouTube.
    await dashboard.removeTag('Categories', 'Subscriptions');

    await expect(dashboard.summaryCaption).toContainText(`Showing ${SAMPLE.expenseRows - 3} expense transactions`);
    await expect(dashboard.kpi('Unique Merchants')).toHaveText(String(SAMPLE.expenseRows - 3));
  });

  test('category filter does not change the income and spend totals', async ({ dashboard }) => {
    // By design the top-row totals follow the month filter only, so hiding
    // a category must not make income or total outflow look smaller.
    await dashboard.removeTag('Categories', 'Subscriptions');

    await expect(dashboard.kpi('Total Spent')).toHaveText(SAMPLE.totalSpent);
    await expect(dashboard.kpi('Total Income')).toHaveText(SAMPLE.totalIncome);
  });

  test('"Include Income" adds credits to the transaction log', async ({ dashboard }) => {
    await dashboard.openTransactionLog();
    await dashboard.expectLogRowCount(SAMPLE.expenseRowsWithTransfers);

    await dashboard.setCheckbox('Include Income & Credits', true);
    await dashboard.expectLogRowCount(SAMPLE.allRows);
  });

  test('removing a category hides its rows in the transaction log', async ({ dashboard }) => {
    // Arrange: open the log
    await dashboard.openTransactionLog();

    // Act: remove the 'Subscriptions' tag from 'Categories'
    await dashboard.removeTag('Categories', 'Subscriptions');

    // Assert: the log now shows 8 rows
    await dashboard.expectLogRowCount(8);
  });

  test('clearing the month filter shows all months', async ({ dashboard }) => {
  // Act
  await dashboard.removeTag('Month(s)', '2025-01');

  // Assert: same figures as on first load
  await expect(dashboard.summaryCaption).toContainText(`Showing ${SAMPLE.expenseRows} expense transactions`);
  await expect(dashboard.kpi('Total Spent')).toHaveText(SAMPLE.totalSpent);
  await expect(dashboard.kpi('Total Income')).toHaveText(SAMPLE.totalIncome);
  });
});
