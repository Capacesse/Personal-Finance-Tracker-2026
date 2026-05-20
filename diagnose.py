"""
diagnose.py
===========
Run this against your local finance.db to surface the root causes
of each data quality issue.  Output is safe to share — it shows
categories and codes but not full transaction descriptions.

Usage:
    python diagnose.py
    python diagnose.py --db path/to/finance.db
"""

import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--db", default="finance.db")
args = parser.parse_args()

conn = sqlite3.connect(args.db)
conn.row_factory = sqlite3.Row


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── 1. What codes are landing in Transfers? ───────────────────────────────────
section("1. TRANSFERS — breakdown by transaction code")
rows = conn.execute("""
    SELECT t.transaction_code,
           COUNT(*)                     AS n,
           ROUND(SUM(t.amount), 2)      AS total,
           ROUND(AVG(t.amount), 2)      AS avg_amt
    FROM   Transactions t
    JOIN   Merchants    m ON t.merchant_id  = m.merchant_id
    JOIN   Categories   c ON m.category_id  = c.category_id
    WHERE  c.name = 'Transfers'
    GROUP  BY t.transaction_code
    ORDER  BY n DESC
    LIMIT  20
""").fetchall()
print(f"  {'CODE':<16} {'COUNT':>6}  {'TOTAL':>12}  {'AVG':>10}")
print(f"  {'-'*50}")
for r in rows:
    code = r['transaction_code'] or '(none)'
    print(f"  {code:<16} {r['n']:>6}  {r['total']:>12.2f}  {r['avg_amt']:>10.2f}")


# ── 2. Sample of Transfers descriptions (first 20 chars only for privacy) ─────
section("2. TRANSFERS — sample descriptions (truncated)")
rows = conn.execute("""
    SELECT SUBSTR(t.description, 1, 40) AS desc_preview,
           t.transaction_code,
           t.amount
    FROM   Transactions t
    JOIN   Merchants    m ON t.merchant_id  = m.merchant_id
    JOIN   Categories   c ON m.category_id  = c.category_id
    WHERE  c.name = 'Transfers'
    ORDER  BY t.amount ASC
    LIMIT  25
""").fetchall()
for r in rows:
    code = r['transaction_code'] or '(none)'
    print(f"  [{code:<10}] {r['amount']:>10.2f}  {r['desc_preview']}")


# ── 3. What codes are landing in PayNow & FAST? ───────────────────────────────
section("3. PAYNOW & FAST — breakdown by code")
rows = conn.execute("""
    SELECT t.transaction_code,
           COUNT(*)                AS n,
           ROUND(SUM(t.amount),2)  AS total
    FROM   Transactions t
    JOIN   Merchants m ON t.merchant_id=m.merchant_id
    JOIN   Categories c ON m.category_id=c.category_id
    WHERE  c.name = 'PayNow & FAST'
    GROUP  BY t.transaction_code ORDER BY n DESC
""").fetchall()
for r in rows:
    code = r['transaction_code'] or '(none)'
    print(f"  {code:<16} {r['n']:>5} txns   {r['total']:>12.2f}")


# ── 4. Uncategorised — grouped by code and description prefix ────────────────
section("4. UNCATEGORISED — top patterns")
rows = conn.execute("""
    SELECT t.transaction_code,
           SUBSTR(t.description, 1, 35) AS desc_prefix,
           COUNT(*)                      AS n,
           ROUND(SUM(t.amount), 2)       AS total
    FROM   Transactions t
    JOIN   Merchants    m ON t.merchant_id  = m.merchant_id
    JOIN   Categories   c ON m.category_id  = c.category_id
    WHERE  c.name = 'Uncategorised'
    GROUP  BY t.transaction_code, SUBSTR(t.description,1,35)
    ORDER  BY n DESC, total ASC
    LIMIT  30
""").fetchall()
print(f"  {'CODE':<14} {'N':>4}  {'TOTAL':>10}  DESCRIPTION PREFIX")
print(f"  {'-'*65}")
for r in rows:
    code = r['transaction_code'] or '(none)'
    print(f"  {code:<14} {r['n']:>4}  {r['total']:>10.2f}  {r['desc_prefix']}")


# ── 5. Merchant normalisation — worst offenders ───────────────────────────────
section("5. MERCHANT DEDUP — merchants with only 1 transaction (sample)")
rows = conn.execute("""
    SELECT m.name AS merchant, COUNT(t.transaction_id) AS txn_count
    FROM   Merchants m
    LEFT JOIN Transactions t ON m.merchant_id = t.merchant_id
    GROUP  BY m.merchant_id
    HAVING txn_count = 1
    ORDER  BY m.name
    LIMIT  30
""").fetchall()
total_single = conn.execute("""
    SELECT COUNT(*) FROM Merchants m
    LEFT JOIN Transactions t ON m.merchant_id=t.merchant_id
    GROUP BY m.merchant_id HAVING COUNT(t.transaction_id)=1
""").fetchall()
print(f"  {len(total_single)} merchants appear only once — sample:")
for r in rows:
    print(f"  {r['merchant']}")


# ── 6. Date format — what formats are in the raw data ────────────────────────
section("6. DATE FORMAT SAMPLE — first 10 distinct dates")
rows = conn.execute("""
    SELECT DISTINCT transaction_date FROM Transactions
    ORDER BY transaction_date LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r['transaction_date']}")


# ── 7. Code coverage breakdown ────────────────────────────────────────────────
section("7. CODE COVERAGE — transactions without a code by category")
rows = conn.execute("""
    SELECT c.name,
           COUNT(*) AS no_code_count
    FROM   Transactions t
    JOIN   Merchants    m ON t.merchant_id  = m.merchant_id
    JOIN   Categories   c ON m.category_id  = c.category_id
    WHERE  t.transaction_code IS NULL
    GROUP  BY c.name
    ORDER  BY no_code_count DESC
""").fetchall()
for r in rows:
    print(f"  {r['name']:<28} {r['no_code_count']:>4} transactions without a code")


# ── 8. Income sanity check ────────────────────────────────────────────────────
section("8. INCOME — breakdown by code")
rows = conn.execute("""
    SELECT t.transaction_code,
           COUNT(*)                AS n,
           ROUND(SUM(t.amount),2)  AS total
    FROM   Transactions t
    JOIN   Merchants m ON t.merchant_id=m.merchant_id
    JOIN   Categories c ON m.category_id=c.category_id
    WHERE  c.name = 'Income'
    GROUP  BY t.transaction_code ORDER BY total DESC
""").fetchall()
for r in rows:
    code = r['transaction_code'] or '(none)'
    print(f"  {code:<16} {r['n']:>4} txns   SGD {r['total']:>10,.2f}")

conn.close()
print("\n" + "="*60)
print("  Paste this full output back to continue diagnosis.")
print("="*60 + "\n")
