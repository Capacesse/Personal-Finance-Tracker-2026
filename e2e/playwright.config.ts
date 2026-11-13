import { defineConfig, devices } from '@playwright/test';
import { BASE_URL } from './global-setup';

/**
 * The tests run against a real Streamlit server, started and stopped by
 * global-setup.ts.
 *
 * The server uses a throwaway database (e2e/.tmp/e2e.db) that is deleted
 * before every run and rebuilt by the app from the bundled sample CSV. Every
 * run therefore starts from the same 13 transactions, and a real finance.db
 * is never touched.
 */

export default defineConfig({
  testDir: './tests',
  globalSetup: './global-setup.ts',

  // All tests share one server and one database, and some tests change data
  // (category edit, upload). They run one at a time, in file-name order, so
  // the read-only checks always see the untouched sample data.
  fullyParallel: false,
  workers: 1,

  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list'], ['html', { open: 'never' }]],

  timeout: 60_000,
  expect: { timeout: 15_000 }, // Streamlit reruns the whole script on each interaction

  use: {
    baseURL: BASE_URL,
    viewport: { width: 1400, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1400, height: 1000 } } }],
});
