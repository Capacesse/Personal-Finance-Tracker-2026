import { spawn, spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * Runs once before the tests, and returns a function that runs once after.
 *
 * Before: delete the previous run's test database, start the Streamlit app
 * on a throwaway database, and wait until it answers.
 * After: stop the app.
 *
 * The server is managed here, not by Playwright's built-in `webServer`
 * option, because on Windows that option left the Streamlit process running
 * after the tests finished. The next run then failed with "port already
 * used". Here the process is started directly and its whole process tree is
 * killed by id, which works the same on Windows, macOS and Linux.
 */

export const PORT = 8601;
export const BASE_URL = `http://127.0.0.1:${PORT}`;

const REPO_ROOT = path.resolve(__dirname, '..');
const TMP_DIR = path.join(__dirname, '.tmp');
const TEST_DB = path.join(TMP_DIR, 'e2e.db');
const PID_FILE = path.join(TMP_DIR, 'server.pid');
const LOG_FILE = path.join(TMP_DIR, 'server.log');

// "python" on Windows and in CI. Override with PYTHON=python3 on macOS/Linux.
const PYTHON = process.env.PYTHON ?? 'python';

/** Stop a process and everything it started. Safe to call on a dead pid. */
function killTree(pid: number): void {
  try {
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(pid), '/T', '/F'], { stdio: 'ignore' });
    } else {
      process.kill(pid, 'SIGTERM');
    }
  } catch {
    // Already gone.
  }
}

async function isServerUp(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/_stcore/health`);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitUntil(condition: () => Promise<boolean>, timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await condition()) return true;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

export default async function globalSetup(): Promise<() => Promise<void>> {
  fs.mkdirSync(TMP_DIR, { recursive: true });

  // A run stopped with Ctrl+C never reaches the teardown below, so its
  // server may still be alive. Its id was saved; stop it now.
  if (fs.existsSync(PID_FILE)) {
    killTree(Number(fs.readFileSync(PID_FILE, 'utf-8')));
    fs.rmSync(PID_FILE, { force: true });
    await waitUntil(async () => !(await isServerUp()), 10_000);
  }

  if (await isServerUp()) {
    throw new Error(
      `Something is already running on port ${PORT} and it was not started by this test suite.\n` +
        'Close it and run the tests again. On Windows PowerShell:\n' +
        `  Get-NetTCPConnection -LocalPort ${PORT} -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`,
    );
  }

  // Fresh database: the app rebuilds it from the sample CSV on first load.
  // SQLite may leave -wal and -shm side files, so those go too.
  for (const name of ['e2e.db', 'e2e.db-wal', 'e2e.db-shm']) {
    fs.rmSync(path.join(TMP_DIR, name), { force: true });
  }

  // Server output goes to a log file, which is the first place to look if
  // the app fails to start.
  const log = fs.openSync(LOG_FILE, 'w');
  const server = spawn(
    PYTHON,
    [
      '-m', 'streamlit', 'run', 'app.py',
      '--server.port', String(PORT),
      '--server.headless', 'true',
      '--browser.gatherUsageStats', 'false',
      '--server.fileWatcherType', 'none',
      '--', '--db', TEST_DB,
    ],
    { cwd: REPO_ROOT, stdio: ['ignore', log, log], windowsHide: true },
  );
  fs.writeFileSync(PID_FILE, String(server.pid));

  const teardown = async (): Promise<void> => {
    if (server.pid) killTree(server.pid);
    fs.rmSync(PID_FILE, { force: true });
    fs.closeSync(log);
  };

  let exitedEarly = false;
  server.once('exit', () => { exitedEarly = true; });
  server.once('error', () => { exitedEarly = true; });

  const started = await waitUntil(async () => exitedEarly || (await isServerUp()), 60_000);
  if (!started || exitedEarly) {
    await teardown();
    throw new Error(
      `The Streamlit app did not start. See ${LOG_FILE} for its output.\n` +
        `Command used: ${PYTHON} -m streamlit run app.py (set PYTHON=python3 if "python" is not found).`,
    );
  }

  return teardown;
}
