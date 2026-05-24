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

- [x] `BIDIRECTIONAL_CODES` logic — FAST/GIRO inbound → Income, outbound → Transfers
- [x] Transaction deduplication — `transaction_hash` UNIQUE column on `Transactions` so re-importing the same CSV never creates duplicate rows
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

## Milestone 2 — Category & Classification Quality 🔄

**Goal:** Every transaction lands in a specific, useful budget category.

### Deliverables

- [x] Split `Transfers` into subcategories: `PayNow & FAST`, `Cash Withdrawals`, `Internal Transfers`
- [x] Add manual overrides — handled via Tier 0/2 dictionary mappings in `categoriser.py`
- [x] Category confidence scoring — implemented via the 5-Tier Confidence System architecture
- [ ] Budget limits per category — store monthly targets in a `Budgets` table and surface warnings when exceeded

### Acceptance Criteria

- [x] No single category holds > 30% of transaction count (excluding Income)
- [x] Every transaction is processed through a strict confidence tier
- [x] User can override a merchant category and it survives `--reset`

---

## Milestone 3 — Personal Dashboard Completion (`app.py`) 🔄

**Goal:** Your own dashboard is fully accurate and feature-complete.

### Deliverables

- [x] Net Flow bug fix
- [x] Modular dashboard architecture (`dashboard/` package)
- [x] Daily spending and month-on-month trend charts
- [ ] Budget vs Actual bar chart — side-by-side planned vs spent per category
- [ ] Running monthly total line — cumulative spend curve for the current month
- [ ] CSV export button — download filtered transactions as a CSV from the UI
- [ ] Inline category editor — click a transaction in the log table and reassign its category directly from the UI

### Acceptance Criteria

- [x] All KPI numbers match a manual calculation from the raw CSV
- [x] Dashboard loads efficiently with clean UI component separation

---

## Milestone 4 — Shared App Hardening

**Goal:** Friends can use the app reliably with their own bank exports, including banks other than DBS.

### Deliverables

- [ ] Multi-bank CSV detection — auto-detect column formats for OCBC, UOB, Citibank exports and normalise them
- [ ] Graceful error handling — if the CSV is malformed, show a clear message telling the user exactly which columns are missing
- [ ] Session comparison — upload two CSVs (e.g. Jan + Feb) and compare them side by side
- [ ] Shareable summary card — one-click image export of the month KPIs

### Acceptance Criteria

- [ ] App handles malformed CSV without crashing (shows user-friendly error)
- [ ] Successfully processes exports from at least 2 bank formats

---

## Milestone 5 — Deployment & Distribution 🔄

**Goal:** Friends can access the app via a URL without installing anything.

### Deliverables

- [x] `README.md` — setup instructions, project structure, how to export from DBS
- [ ] Streamlit Community Cloud deployment — public URL for `app.py`
- [ ] Environment config — `.env` or `secrets.toml` pattern for any future API keys
- [ ] Automated CSV validation on upload — reject files that don't meet the expected schema

### Acceptance Criteria

- [ ] A friend with zero Python knowledge can use the app via the URL
- [x] `README.md` covers local setup clearly
- [ ] App is live at a stable Streamlit Cloud URL

---

## Milestone 6 — Intelligence Layer (Stretch Goals) ⬜

**Goal:** The engine gets smarter over time and reduces manual categorisation work.

### Deliverables

- [ ] Fuzzy merchant clustering — `rapidfuzz` groups near-identical merchant names automatically
- [ ] Recurring transaction detection — flag subscriptions and regular bills automatically
- [ ] Anomaly alerts — flag transactions that are unusually large compared to historical averages
- [ ] Natural language query interface — type "show me food spending in March" and get a filtered view

### Acceptance Criteria

- [ ] Fuzzy clustering reduces unique merchant count by > 20%
- [ ] Recurring transactions detected with > 90% precision
- [ ] NL query correctly interprets common query patterns

---

## Current Progress

**Milestone 1 Complete.** Working on Budgets Table (Milestone 2) and Dashboard Refinements (Milestone 3).
