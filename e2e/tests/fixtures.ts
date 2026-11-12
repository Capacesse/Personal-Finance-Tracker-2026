import { test as base } from '@playwright/test';
import { DashboardPage } from '../pages/dashboard';

/**
 * Custom fixture: every test that asks for `dashboard` gets the page object
 * with the dashboard already loaded, so no test repeats that setup.
 */
export const test = base.extend<{ dashboard: DashboardPage }>({
  dashboard: async ({ page }, use) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await use(dashboard);
  },
});

export { expect } from '@playwright/test';

/** Expected values, worked out by hand from bank_export_sample.csv. */
export const SAMPLE = {
  totalTransactions: 13,
  totalSpent: 'SGD 548.45',
  totalIncome: 'SGD 3,501.20',
  netFlow: 'SGD 2,952.75',
  // Expense rows excluding transfers and cash withdrawals
  expenseRows: 9,
  // Expense rows including the PayLah top-up and the ATM withdrawal
  expenseRowsWithTransfers: 11,
  // All rows including the salary and interest credits
  allRows: 13,
};
