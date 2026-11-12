import { defineConfig, devices } from '@playwright/test';
import path from 'path';

/**
 * The tests run against a real Streamlit server that Playwright starts itself.
 *
 * The server uses a throwaway database (e2e/.tmp/e2e.db). global-setup.ts
 * deletes that file before every run, and the app rebuilds it from the bundled
 * sample CSV on first load. Every run therefore starts from the same 13
 * transactions, and a real finance.db is never touched.
 */

const PORT = 8601;
const REPO_ROOT = path.resolve(__dirname, '..');
export const TEST_DB = path.join(__dirname, '.tmp', 'e2e.db');

// "python" on Windows and in CI. Override with PYTHON=python3 on macOS/Linux.
const PYTHON = process.env.PYTHON ?? 'python';

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
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1400, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1400, height: 1000 } } }],

  webServer: {
    command: [
      `${PYTHON} -m streamlit run app.py`,
      `--server.port ${PORT}`,
      '--server.headless true',
      '--browser.gatherUsageStats false',
      '--server.fileWatcherType none',
      `-- --db "${TEST_DB}"`,
    ].join(' '),
    cwd: REPO_ROOT,
    url: `http://127.0.0.1:${PORT}/_stcore/health`,
    // Always start a fresh server: a reused one could hold cached data from
    // a database that global-setup has since deleted.
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
