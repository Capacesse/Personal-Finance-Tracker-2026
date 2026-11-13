import { expect, type Locator, type Page } from '@playwright/test';
import path from 'path';

/**
 * Page object for the dashboard.
 *
 * Tests describe WHAT the user does ("filter out a category"). This class
 * knows HOW to do it on the page (which element to click). If Streamlit
 * changes its HTML, only this file needs updating, not every test.
 */
export class DashboardPage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly heading: Locator;
  readonly summaryCaption: Locator;
  readonly transactionLog: Locator;
  readonly logGrid: Locator;
  readonly logSearch: Locator;
  readonly exportButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = page.getByTestId('stSidebar');
    this.heading = page.getByRole('heading', { name: /Personal Finance Tracker/ });
    this.summaryCaption = page.getByText(/Showing [\d,]+ expense transactions/);
    this.transactionLog = page.getByTestId('stExpander').filter({ hasText: 'Full Transaction Log' });
    this.logGrid = this.transactionLog.getByTestId('stDataFrame');
    this.logSearch = this.transactionLog.getByPlaceholder('e.g. Grab, Spotify…');
    this.exportButton = this.transactionLog.getByRole('button', { name: /Export to CSV/ });
  }

  // ── Navigation ─────────────────────────────────────────────────────────────

  async goto(): Promise<void> {
    await this.page.goto('/');
    await expect(this.heading).toBeVisible({ timeout: 30_000 });
    await this.expectNoError();
  }

  /** Streamlit shows uncaught Python errors in a red box. There should be none. */
  async expectNoError(): Promise<void> {
    await expect(this.page.getByTestId('stException')).toHaveCount(0);
  }

  // ── KPI tiles ──────────────────────────────────────────────────────────────

  /** The value shown on a KPI tile, found by its label (e.g. "Total Spent"). */
  kpi(label: string): Locator {
    return this.page
      .getByTestId('stMetric')
      .filter({ hasText: label })
      .getByTestId('stMetricValue');
  }

  /** Sidebar footer text, e.g. "13 total transactions". */
  get totalTransactions(): Locator {
    return this.sidebar.getByText(/[\d,]+ total transactions/);
  }

  // ── Sidebar filters ────────────────────────────────────────────────────────

  async setCheckbox(label: string, checked: boolean): Promise<void> {
    const box = this.sidebar.getByTestId('stCheckbox').filter({ hasText: label });
    const input = box.getByRole('checkbox');
    if ((await input.isChecked()) !== checked) {
      // The real <input> is visually hidden, so click the visible label.
      await box.locator('label').click();
    }
    await expect(input).toBeChecked({ checked });
  }

  /** A multiselect in the sidebar, found by its label ("Month(s)" or "Categories"). */
  multiselect(label: string): Locator {
    return this.sidebar.getByTestId('stMultiSelect').filter({ hasText: label });
  }

  /** The selected values of a multiselect, shown as removable tags. */
  selectedTags(label: string): Locator {
    return this.multiselect(label).locator('span[data-tag]');
  }

  /** Deselect one value by clicking the x on its tag. */
  async removeTag(label: string, value: string): Promise<void> {
    await this.multiselect(label).getByRole('button', { name: `Remove ${value}`, exact: true }).click();
    await expect(this.selectedTags(label).filter({ hasText: value })).toHaveCount(0);
  }

  // ── Transaction log ────────────────────────────────────────────────────────

  async openTransactionLog(): Promise<void> {
    if (!(await this.logGrid.isVisible())) {
      await this.transactionLog.locator('summary').click();
    }
    await expect(this.logGrid).toBeVisible();
  }

  /**
   * Assert how many rows the log shows, using the "N rows shown" caption
   * under the table.
   *
   * The table itself cannot be counted: it only creates the rows currently
   * scrolled into view, so a long table would look shorter than it is.
   */
  async expectLogRowCount(count: number): Promise<void> {
    await expect(this.transactionLog.getByText(/[\d,]+ rows shown/)).toHaveText(`${count} rows shown`);
  }

  /**
   * One cell of the log table. Columns: 0 Date, 1 Amount, 2 Code, 3 Merchant,
   * 4 Category, 5 Description.
   *
   * The table is drawn on a <canvas>, which Playwright cannot read. The grid
   * also keeps a hidden HTML table for screen readers, and that is what these
   * locators read. Only rows scrolled into view exist in it (about the first
   * eleven), which is enough for the 13-row sample data.
   */
  logCell(column: number, row: number): Locator {
    return this.logGrid.getByTestId(`glide-cell-${column}-${row}`);
  }

  /** Row index of the first transaction for a merchant. */
  async rowOfMerchant(merchant: string): Promise<number> {
    const cell = this.logGrid.locator('td[aria-colindex="4"]').filter({ hasText: new RegExp(`^${merchant}$`) }).first();
    await expect(cell).toBeAttached();
    const id = await cell.getAttribute('data-testid'); // "glide-cell-<column>-<row>"
    return Number(id!.split('-').pop());
  }

  /** The Category cell on the same row as a merchant. */
  categoryCell(merchant: string): Locator {
    return this.logGrid
      .locator('tbody tr')
      .filter({ has: this.page.locator('td[aria-colindex="4"]', { hasText: new RegExp(`^${merchant}$`) }) })
      .first()
      .locator('td[aria-colindex="5"]');
  }

  /**
   * Assert a merchant's category. toHaveText keeps retrying until the table
   * has finished redrawing, so this is safe straight after a reload.
   */
  async expectCategory(merchant: string, category: string): Promise<void> {
    await expect(this.categoryCell(merchant)).toHaveText(category);
  }

  /**
   * Change a merchant's category in the table and save it.
   *
   * Because the table is a canvas, the cell is reached the way a keyboard
   * user would: click the top-left cell, move down to the merchant's row and
   * right to the Category column, press Enter to open the dropdown, pick the
   * new value.
   */
  async changeCategory(merchant: string, newCategory: string): Promise<void> {
    const HEADER_HEIGHT = 36;
    const ROW_HEIGHT = 35;
    const CATEGORY_COLUMN = 4;

    const row = await this.rowOfMerchant(merchant);
    await this.logGrid.scrollIntoViewIfNeeded();

    // Click the first data cell, then use arrow keys. Only this one click
    // depends on pixel positions; the arrow keys do not.
    await this.logGrid.locator('.dvn-scroller').click({
      position: { x: 30, y: HEADER_HEIGHT + ROW_HEIGHT / 2 },
    });
    await expect(this.logCell(0, 0)).toHaveAttribute('aria-selected', 'true');
    for (let i = 0; i < row; i++) await this.page.keyboard.press('ArrowDown');
    for (let i = 0; i < CATEGORY_COLUMN; i++) await this.page.keyboard.press('ArrowRight');
    await expect(this.logCell(CATEGORY_COLUMN, row)).toHaveAttribute('aria-selected', 'true');

    // Open the dropdown, narrow it by typing, and click the exact option.
    await this.page.keyboard.press('Enter');
    await this.page.keyboard.type(newCategory);
    await this.page.getByRole('option', { name: newCategory, exact: true }).click();

    // The cell must show the new value before anything is saved.
    await expect(this.logCell(CATEGORY_COLUMN, row)).toHaveText(newCategory);

    await expect(this.page.getByText(/You have re-categorised 1 transaction/)).toBeVisible();
    await this.page.getByRole('button', { name: 'Save Category Updates' }).click();

    // Saving reruns the page. When the row count caption is back, the save
    // has been written and the table redrawn.
    await expect(this.transactionLog.getByText(/[\d,]+ rows shown/)).toBeVisible();
    await this.expectCategory(merchant, newCategory);
  }

  // ── Budget editor ──────────────────────────────────────────────────────────

  /** The "Monthly Budget Targets" table at the bottom of the page. */
  get budgetGrid(): Locator {
    // It is the last table on the page; the transaction log is the other one.
    return this.page.getByTestId('stDataFrame').last();
  }

  /** The Monthly Limit cell on the same row as a category. */
  budgetCell(category: string): Locator {
    return this.budgetGrid
      .locator('tbody tr')
      .filter({ has: this.page.locator('td[data-testid^="glide-cell-1-"]', { hasText: new RegExp(`^${category}$`) }) })
      .first()
      .locator('td[data-testid^="glide-cell-2-"]');
  }

  /** Assert the limit shown for a category. The table shows plain numbers: 30, not $ 30.00. */
  async expectBudget(category: string, limit: number): Promise<void> {
    await expect(this.budgetCell(category)).toHaveText(String(limit));
  }

  /**
   * Type a monthly limit for one category. This does NOT save it:
   * call saveBudgets() afterwards.
   *
   * Like the transaction log, this table is a canvas, so the cell is reached
   * by clicking the first limit cell and moving down with the arrow keys.
   */
  async setBudget(category: string, limit: number): Promise<void> {
    const HEADER_HEIGHT = 36;
    const ROW_HEIGHT = 35;

    const cell = this.budgetCell(category);
    await expect(cell).toBeAttached();
    const id = await cell.getAttribute('data-testid'); // "glide-cell-<column>-<row>"
    const row = Number(id!.split('-').pop());

    await this.budgetGrid.scrollIntoViewIfNeeded();
    const box = await this.budgetGrid.boundingBox();
    // The limit column is the right-hand half of the table.
    await this.budgetGrid.locator('.dvn-scroller').click({
      position: { x: box!.width * 0.75, y: HEADER_HEIGHT + ROW_HEIGHT / 2 },
    });
    for (let i = 0; i < row; i++) await this.page.keyboard.press('ArrowDown');
    await expect(cell).toHaveAttribute('aria-selected', 'true');

    // Enter opens a small input box over the cell. Fill it and confirm.
    await this.page.keyboard.press('Enter');
    await this.page.locator('#portal input').fill(String(limit));
    await this.page.keyboard.press('Enter');
    await expect(cell).toHaveText(String(limit));
  }

  /** Press "Save Budget Limits" and wait for the app to confirm the save. */
  async saveBudgets(): Promise<void> {
    await this.page.getByRole('button', { name: 'Save Budget Limits' }).click();
    await expect(this.page.getByText('Budgets successfully updated!')).toBeVisible();
  }

  // ── Upload ─────────────────────────────────────────────────────────────────

  /** Choose a file from e2e/fixtures and press "Process New Transactions". */
  async uploadStatement(fixtureName: string): Promise<void> {
    const file = path.join(__dirname, '..', 'fixtures', fixtureName);
    await this.sidebar.locator('input[type="file"]').setInputFiles(file);
    await expect(this.sidebar.getByTestId('stFileChip').and(this.sidebar.getByLabel(new RegExp(fixtureName)))).toBeVisible();
    await this.sidebar.getByRole('button', { name: 'Process New Transactions' }).click();
  }
}
