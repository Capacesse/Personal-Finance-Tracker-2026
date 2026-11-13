# Personal Finance Tracker — Project Milestones

## Status Legend

- ✅ Complete
- 🔄 In Progress
- ⬜ Not Started

---

## Milestone 1 — Data Integrity & Pipeline Hardening ✅

**Goal:** The database contains clean, deduplicated, correctly-categorised data.
Nothing built on top of bad data is trustworthy, so this is the foundation.

### Deliverables

- [x] `BIDIRECTIONAL_CODES` logic — FAST/GIRO inbound → Income, outbound → PayNow & FAST
- [x] Transaction deduplication — `transaction_hash` UNIQUE column on `Transactions` so re-importing the same CSV never creates duplicate rows, while genuine identical purchases on the same day are kept
- [x] Merchant normalisation — strip reference numbers, collapse variants (Regex cleaning in `transformer.py`)
- [x] Expand `MERCHANT_CATEGORY_MAP` with real-world DBS description patterns (Achieved 100% coverage)
- [x] Migrate `etl.py` and `app.py` to import from `core/` exclusively

### Acceptance Criteria

- [x] Re-running `etl.py --reset` twice produces identical row counts
- [x] Income shows realistic salary amounts
- [x] Transfers < 15% of total transaction count
- [x] Uncategorised < 10% of total transaction count (Currently 0%)
- [x] Unique merchant count meaningfully lower than transaction count

---

## Milestone 2 — Category & Classification Quality ✅

**Goal:** Every transaction lands in a specific, useful budget category.

### Deliverables

- [x] Split `Transfers` into subcategories: `PayNow & FAST`, `Cash Withdrawals`, `Internal Transfers`
- [x] Add manual overrides — handled via Tier 0/2 dictionary mappings in `categoriser.py`
- [x] Category confidence scoring — implemented via the 5-Tier Confidence System architecture
- [x] Budget limits per category — store monthly targets in a `Budgets` table and surface warnings when exceeded

### Acceptance Criteria

- [x] No single category holds > 30% of transaction count (excluding Income)
- [x] Every transaction is processed through a strict confidence tier
- [x] User can override a merchant category and it survives `--reset`

---

## Milestone 3 — Personal Dashboard Completion (`app.py`) ✅

**Goal:** Your own dashboard is fully accurate and feature-complete.

### Deliverables

- [x] Net Flow bug fix
- [x] Modular dashboard architecture (`dashboard/` package)
- [x] Daily spending and month-on-month trend charts
- [x] Budget vs Actual bar chart — side-by-side planned vs spent per category
- [x] Running monthly total line — cumulative spend curve for the current month
- [x] CSV export button — download filtered transactions as a CSV from the UI
- [x] Inline category editor — click a transaction in the log table and reassign its category directly from the UI

### Acceptance Criteria

- [x] All KPI numbers match a manual calculation from the raw CSV
- [x] Dashboard loads efficiently with clean UI component separation

---

## Milestone 4 — Upload Hardening ✅

**Goal:** The in-app upload handles good and bad files predictably.

### Deliverables

- [x] Graceful error handling — a malformed or unsupported CSV shows a clear message naming the missing columns
- [x] CSV validation on upload — files that do not match a supported bank format are rejected and nothing is written
- [x] Dashboard refreshes immediately after a successful upload
- [x] Uploads are read from memory; no copy of the statement is left on disk

### Acceptance Criteria

- [x] App handles a malformed CSV without crashing (shows a user-friendly error)
- [x] Uploading the same statement twice adds no rows

---

## Milestone 5 — Deployment ✅

**Goal:** Anyone can try the app via a URL without installing anything.

### Deliverables

- [x] `README.md` — setup instructions, project structure, how to export from DBS
- [x] First-run demo data — with no database, the app builds one from the sample CSV
- [x] Streamlit Community Cloud deployment — https://julius-finance-tracker.streamlit.app/
- [x] Pinned dependency versions in `requirements.txt`

### Acceptance Criteria

- [x] `README.md` covers local setup clearly
- [x] App is live at a stable Streamlit Cloud URL
- [x] A visitor with zero Python knowledge can explore the dashboard via the URL

**Scope note:** the hosted app is a demo on made-up sample data. All visitors share one database, so it is not suitable for real statements. Real use is local.

---

## Milestone 6 — Test Automation & CI ✅

**Goal:** Every change is checked automatically, and known defects cannot quietly return.

### Deliverables

- [x] pytest unit suite for the pipeline, categoriser, loader and dashboard data layer
- [x] Playwright (TypeScript) browser suite for the running dashboard
- [x] GitHub Actions workflow running both suites on every push
- [x] `TESTING.md` — test approach, defect log, known limitations, what is not covered

### Acceptance Criteria

- [x] Expected values are calculated by hand from the sample CSV, not copied from the app
- [x] Every defect found has a regression test that fails on the old code
- [x] Both CI jobs pass on `main`

---

## Backlog (not scheduled)

Ideas that are parked. None are in progress.

**Multi-user and multi-bank**

- [ ] Per-visitor data isolation on the hosted app, so friends can upload their own statements safely
- [ ] OCBC and UOB export formats (needs real sample files)
- [ ] Session comparison — upload two CSVs and compare them side by side
- [ ] Shareable summary card — one-click image export of the month KPIs

**Intelligence layer**

- [ ] Fuzzy merchant clustering — `rapidfuzz` groups near-identical merchant names automatically
- [ ] Recurring transaction detection — flag subscriptions and regular bills automatically
- [ ] Anomaly alerts — flag transactions that are unusually large compared to historical averages
- [ ] Natural language query interface — type "show me food spending in March" and get a filtered view

---

## Current Progress

**Milestones 1 to 6 complete.** The app is deployed, tested and under CI. Remaining ideas are in the backlog.
