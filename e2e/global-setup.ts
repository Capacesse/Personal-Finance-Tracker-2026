import fs from 'fs';
import path from 'path';

/**
 * Runs once before the test run. Removes the previous run's test database so
 * the app rebuilds it from the sample CSV. SQLite may leave -wal and -shm
 * side files next to the database, so those are removed too.
 */
export default function globalSetup(): void {
  const dir = path.join(__dirname, '.tmp');
  fs.mkdirSync(dir, { recursive: true });
  for (const name of ['e2e.db', 'e2e.db-wal', 'e2e.db-shm']) {
    fs.rmSync(path.join(dir, name), { force: true });
  }
}
