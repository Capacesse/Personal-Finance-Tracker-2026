# Personal Finance Engine — Project Milestones

## Status Legend
- ✅ Complete
- 🔄 In Progress  
- ⬜ Not Started

---

## Milestone 1 — Data Integrity & Pipeline Hardening
**Goal:** The database contains clean, deduplicated, correctly-categorised data.
Nothing built on top of bad data is trustworthy, so this is the foundation.

### Deliverables
- [ ] `BIDIRECTIONAL_CODES` logic — FAST/GIRO inbound → Income, outbound → Transfers
- [ ] Transaction deduplication — `transaction_hash` UNIQUE column on `Transactions`
      so re-importing the same CSV never creates duplicate rows
- [ ] Merchant normalisation — strip reference numbers, collapse variants
      (e.g. `GRAB*00123`, `GRAB*FOOD SG`, `GRABFOOD` → `GRAB`)
- [ ] Expand `MERCHANT_CATEGORY_MAP` with real-world DBS description patterns
- [ ] Migrate `etl.py` and `app.py` to import from `core/` exclusively
      (no logic duplicated outside the package)

### Acceptance Criteria
- Re-running `etl.py --reset` twice produces identical row counts
- Income shows realistic salary amounts (not $0.44)
- Transfers < 15% of total transaction count
- Uncategorised < 10% of total transaction count
- Unique merchant count meaningfully lower than transaction count

---

## Milestone 2 — Category & Classification Quality
**Goal:** Every transaction lands in a specific, useful budget category.

### Deliverables
- [ ] Split `Transfers` into subcategories:
      `PayNow & FAST`, `Cash Withdrawals`, `Internal Transfers`
- [ ] Add manual override table (`MerchantOverrides`) — lets users pin a merchant
      to a specific category that persists across re-imports
- [ ] Category confidence scoring — tag each transaction with how its category
      was resolved (tier1/tier2/tier3/tier4) for auditability
- [ ] Budget limits per category — store monthly targets in a `Budgets` table
      and surface warnings when exceeded

### Acceptance Criteria
- No single category holds > 30% of transaction count (excluding Income)
- Every transaction has a non-null confidence tier tag
- User can override a merchant category and it survives `--reset`

---

## Milestone 3 — Personal Dashboard Completion (`dashboard.py`)
**Goal:** Your own dashboard is fully accurate and feature-complete.

### Deliverables
- [ ] Net Flow bug fix ✅ (already done)
- [ ] Budget vs Actual bar chart — side-by-side planned vs spent per category
- [ ] Running monthly total line — cumulative spend curve for the current month
- [ ] Year-to-date summary panel
- [ ] CSV export button — download filtered transactions as a CSV from the UI
- [ ] Inline category editor — click a transaction in the log table and reassign
      its category without touching the code

### Acceptance Criteria
- All KPI numbers match a manual calculation from the raw CSV
- Dashboard loads in < 2 seconds on a full year of data

---

## Milestone 4 — Shared App Hardening (`app.py`)
**Goal:** Friends can use the app reliably with their own bank exports,
including banks other than DBS.

### Deliverables
- [ ] Multi-bank CSV detection — auto-detect column formats for DBS, OCBC,
      UOB, Citibank exports and normalise them before transform()
- [ ] Graceful error handling — if the CSV is malformed, show a clear message
      telling the user exactly which columns are missing
- [ ] "How to export" guide — expandable instructions per bank within the app
- [ ] Session comparison — upload two CSVs (e.g. Jan + Feb) and compare them
      side by side
- [ ] Shareable summary card — one-click image export of the month KPIs

### Acceptance Criteria
- App handles malformed CSV without crashing (shows user-friendly error)
- Successfully processes exports from at least 2 bank formats
- No data persists between sessions (verified by server restart test)

---

## Milestone 5 — Deployment & Distribution
**Goal:** Friends can access the app via a URL without installing anything.

### Deliverables
- [ ] `README.md` — setup instructions, project structure, how to export from DBS
- [ ] Streamlit Community Cloud deployment — public URL for `app.py`
- [ ] Environment config — `secrets.toml` pattern for any future API keys
- [ ] Automated CSV validation on upload — reject files that don't meet the
      expected schema before running ETL
- [ ] Basic rate-limiting awareness — warn if file is very large (> 5000 rows)

### Acceptance Criteria
- A friend with zero Python knowledge can use the app via the URL
- `README.md` covers local setup in under 10 steps
- App is live at a stable Streamlit Cloud URL

---

## Milestone 6 — Intelligence Layer (Stretch Goals)
**Goal:** The engine gets smarter over time and reduces manual categorisation work.

### Deliverables
- [ ] Fuzzy merchant clustering — `rapidfuzz` groups near-identical merchant
      names automatically (e.g. `MCDONALD'S` variants → one merchant)
- [ ] Recurring transaction detection — flag subscriptions and regular bills
      automatically based on amount + merchant pattern
- [ ] Anomaly alerts — flag transactions that are unusually large compared to
      that merchant's historical average
- [ ] Natural language query interface — type "show me food spending in March"
      and get a filtered view (Claude API integration)

### Acceptance Criteria
- Fuzzy clustering reduces unique merchant count by > 20%
- Recurring transactions detected with > 90% precision on test data
- NL query correctly interprets at least 10 common query patterns

---

## Current Position
**Starting Milestone 1.** Milestones are sequential — each one's acceptance
criteria must pass before the next begins.
