# Testing

## Approach

The app has two layers, and each is tested where it is cheapest to test.

| Layer | Tested with | Why |
| ----- | ----------- | --- |
| Data logic (`core/`, `dashboard/data.py`) | pytest | Pure functions on DataFrames and SQLite. Fast, and a failure points at one function. |
| The running dashboard | Playwright | Only a real browser shows whether the pieces work together: upload, rerun, cache, widgets. |

Most checks sit in the unit layer (94 tests, about 5 seconds). The browser layer is kept small (26 tests, about two minutes) and covers user journeys rather than repeating the unit checks.

Expected values are worked out by hand from `bank_export_sample.csv`, not copied from the app's output. For example, total spend of SGD 548.45 is the sum of the eleven withdrawal rows in that file.

## Running the tests

```bash
# Unit tests
pip install -r requirements-dev.txt
pytest

# Browser tests
cd e2e
npm install
npx playwright install chromium     # first time only
npx playwright test                 # headless
npx playwright test --headed        # watch the browser
npx playwright test --ui            # step through tests interactively
npx playwright show-report          # open the last HTML report
```

On macOS or Linux, where Python is `python3`, run the browser tests as `PYTHON=python3 npx playwright test`.

## How the browser tests are set up

- **The suite starts and stops the app itself** (`global-setup.ts`) on port 8601, pointed at a throwaway database in `e2e/.tmp/`. A real `finance.db` is never touched. Server output is written to `e2e/.tmp/server.log`.
- **Every run starts from the same data.** `global-setup.ts` deletes the test database, and the app rebuilds it from the sample CSV on first load.
- **Tests run one at a time, in file-name order.** They share one server and one database, and two spec files change data. The read-only specs (`01` to `03`) run first; `04` restores what it changes; `05` adds rows; `06` saves a budget and runs last.
- **Selectors live in one place.** `e2e/pages/dashboard.ts` is a page object. Tests say what the user does; the page object knows which element to click.
- **The transaction table is a canvas.** Playwright cannot read pixels, so the tests read the hidden HTML table the grid keeps for screen readers, and edit cells by keyboard the way a keyboard user would.

## Defect log

Defects found while writing these tests. All are fixed, and each has a regression test that fails on the old code.

| # | Defect | Impact | Found by | Fix |
| - | ------ | ------ | -------- | --- |
| 1 | **ISO dates read as day-first on pandas 3.** `2025-01-02` became 1 February. Did not occur on pandas 2.2, and `requirements.txt` allowed either. | The 13 January sample transactions were spread across twelve months. Any ISO-dated export would be silently wrong. | `test_iso_date_is_not_read_as_day_first` and 11 other unit tests | ISO dates are parsed as written, other formats day-first (`_parse_dates`). Versions pinned. |
| 2 | **Upload error replaced by a success message.** The cleanup, "Database updated successfully" and page rerun sat inside the `except` block. | A rejected file showed a green success message, so the user believed bad data had loaded. | `05-upload.spec.ts`: rejected file | Error handling restructured: errors stay on screen, success is only reported on success. |
| 3 | **Dashboard not refreshed after a successful upload.** Same misplaced block: the cache clear and rerun only ran on failure. | New transactions did not appear until the 60-second cache expired. | `05-upload.spec.ts`: valid statement | Cache cleared and page rerun on success. |
| 4 | **Uploaded statement left on disk.** `temp_upload.csv` was only deleted on failure, and had been committed to the repository. | A user's bank statement stayed in the project folder in plain text. | Code review while fixing 2 and 3 | Uploads are read from memory. No temp file is written. |
| 5 | **Two identical purchases on one day stored as one.** The deduplication hash used date, amount and description only. | Two SGD 1.09 bus rides on the same day became a single transaction, so spend was under-reported. | `test_two_identical_purchases_on_one_day_are_both_kept` | Repeats within a file get an occurrence number that is part of the hash. Re-imports still add nothing, and existing databases keep working. |
| 6 | **App unusable on first run.** With no database the app stopped at an error before the upload box was drawn. | A fresh clone or cloud deployment could not be used without the command line. | `01-dashboard.spec.ts`: first load | Demo database is built from the sample CSV when none exists (`core/bootstrap.py`). |
| 7 | **Budget save confirmation never shown.** The page reran immediately after displaying "Budgets successfully updated!", wiping the message before it could be seen. | The budget was saved, but the user got no feedback and could not tell whether the save had worked. | Writing `06-budgets.spec.ts`: the test had nothing on screen to wait for after pressing Save | The confirmation is stored and shown after the rerun. |

## Known limitation

**A row that a bank export genuinely duplicates is now counted twice.** Keeping identical same-day purchases (defect 5) means the pipeline can no longer tell a real repeat purchase from a faulty export that lists one transaction twice. Real repeat purchases are common and faulty exports are not, so the pipeline keeps both and logs how many repeats it saw.

## Not covered

- **Chart contents.** The tests check that all seven charts render, and the numbers behind them are unit tested, but nothing checks the drawn bars.
- **Tables longer than one screen.** The canvas grid only exposes rows scrolled into view, so the table helpers work for roughly the first eleven rows. Row counts use the "N rows shown" caption instead.
- **Banks other than DBS/POSB.** The OCBC and UOB mappings are placeholders and have no tests.
- **Browsers other than Chromium.**
