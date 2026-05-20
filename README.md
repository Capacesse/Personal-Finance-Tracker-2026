# 💳 Personal Finance Tracker

A local, automated personal finance pipeline that extracts your DBS/POSB bank
transaction history, categorises merchants intelligently, and displays an
interactive Streamlit dashboard.

---

## Project Structure

```
PersonalFinanceProject/
│
├── core/                          # Shared business logic (imported by all tools)
│   ├── categoriser.py             # 5-tier categorisation system + keyword map
│   ├── transformer.py             # Extract & Transform (cleaning, hashing, normalisation)
│   ├── loader.py                  # Schema init, code seeding, DB insertion
│   └── schema.sql                 # SQLite DDL (tables, indexes, views)
│
├── app.py                         # Streamlit upload-based app (for sharing with friends)
├── dashboard.py                   # Streamlit dashboard (your persistent personal view)
├── etl.py                         # CLI pipeline — run this to load new bank exports
├── transaction_codes_loader.py    # Seeds DBS transaction codes into the DB
├── diagnose.py                    # Diagnostic tool — audits data quality issues
│
├── DBS Transaction Codes & Descriptions.txt   # DBS/POSB reference codes
├── bank_export_sample.csv         # Sample CSV showing expected column format
├── requirements.txt
├── MILESTONES.md                  # Project roadmap and progress tracker
└── README.md
```

---

## Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/PersonalFinanceProject.git
cd PersonalFinanceProject
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your bank export
Download your transaction history from DBS iBanking:
> Accounts → Transaction History → Download → **CSV format**

Save it as `bank_export.csv` in the project root. See `bank_export_sample.csv`
for the expected column format.

### 5. Run the ETL pipeline
```bash
# First run (or to reload from scratch)
python etl.py --csv bank_export.csv --reset

# Append new transactions without wiping existing data
python etl.py --csv bank_export.csv
```

### 6. Launch the dashboard
```bash
# Your personal persistent dashboard
streamlit run dashboard.py

# Upload-based app (for friends, no local DB required)
streamlit run app.py
```

---

## How to Export from DBS iBanking

1. Log in at **internet banking.dbs.com.sg**
2. Go to **My Accounts** → select your account
3. Click **Download** (top right of transaction list)
4. Select date range (up to 12 months at a time)
5. Choose **CSV** format — this includes the `Transaction Code` column
   ⚠️ Excel format omits the Transaction Code; always use CSV

---

## Categorisation System

The engine uses a 5-tier confidence system to assign each transaction a category:

| Tier | Logic | Example |
|---|---|---|
| 1a | Cash withdrawal code (`AWL`, `WDL`) | Always → `Cash Withdrawals` |
| 1b | Bidirectional code + amount sign | `ICT` positive → `Income`, negative → `PayNow & FAST` |
| 2  | High-signal code (not generic) | `PAY` → `Income` |
| 3  | Merchant keyword match | `"spotify"` in description → `Subscriptions` |
| 4  | Generic code fallback | `POS` at unknown merchant → `Shopping` |
| 5  | Default | → `Uncategorised` |

To improve categorisation, add keywords to `MERCHANT_CATEGORY_MAP` in
`core/categoriser.py`.

---

## Privacy

Your financial data is **never committed to this repository**. The `.gitignore`
excludes:
- `bank_export.csv` and all `*.csv` files
- `finance.db`
- `.env` and any secrets files

---

## Milestones

See [MILESTONES.md](MILESTONES.md) for the full project roadmap.

---

## Requirements

- Python 3.11+
- pandas, streamlit, plotly (see `requirements.txt`)
