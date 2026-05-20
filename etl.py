"""
Personal Finance Tracker — CLI ETL Pipeline
=============================================
All business logic now lives in core/.  
This script is the CLI entry-point only:
- argument parsing, 
- DB connection management, 
- seeding,
- reporting.
 
Usage:
    python etl.py                        # uses defaults
    python etl.py --csv my_export.csv    # custom CSV
    python etl.py --reset                # wipe DB and reload from scratch
"""

import argparse
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.loader import (
    build_code_cache,
    initialise_schema,
    load_transactions,
)
from core.transformer import extract, transform

# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_CSV = "bank_export.csv"
DEFAULT_DB  = "finance.db"
CODES_TXT_FILE = "DBS Transaction Codes & Descriptions.txt"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Database helpers ──────────────────────────────────────────────────────────

@contextmanager
def get_connection(db_path: str):
    """
    Context manager that yields a SQLite connection with best-practice
    settings applied, then commits on success or rolls back on any error.

    Best practices enforced here:
    • PRAGMA foreign_keys = ON   — SQLite disables FK checks by default;
                                   we must enable them every connection.
    • Row factory = sqlite3.Row  — lets us access columns by name, not index.
    • Explicit transaction control (commit / rollback) around the caller's work.
    • Connection is always closed via the finally block.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        log.error("Error detected, transaction rolled back.")
        raise
    finally:
        conn.close()

# ── Code seeding ──────────────────────────────────────────────────────────────
 
def seed_codes(db_path: str, codes_path: str) -> None:
    if not Path(codes_path).exists():
        log.warning("Codes file '%s' not found, code-based categorisation limited.",
                    codes_path)
        return
    try:
        from transaction_codes_loader import load_codes_into_db
        load_codes_into_db(db_path, codes_path)
    except ImportError:
        log.warning("transaction_codes_loader.py not found, skipping.")

# ── Reporting ─────────────────────────────────────────────────────────────────
 
def print_summary(db_path: str) -> None:
    with get_connection(db_path) as conn:
        spend = conn.execute(
            """
            SELECT c.name, COUNT(*) n, ROUND(SUM(t.amount),2) total
            FROM   Transactions t
            JOIN   Merchants    m ON t.merchant_id  = m.merchant_id
            JOIN   Categories   c ON m.category_id  = c.category_id
            GROUP  BY c.name ORDER BY total ASC
            """
        ).fetchall()
        stats = conn.execute(
            """
            SELECT
                COUNT(*)  AS total,
                SUM(CASE WHEN transaction_code IS NOT NULL THEN 1 ELSE 0 END)
                          AS coded,
                COUNT(DISTINCT merchant_id) AS merchants
            FROM Transactions
            """
        ).fetchone()
        uncat = conn.execute(
            """
            SELECT COUNT(*) FROM Transactions t
            JOIN Merchants m ON t.merchant_id=m.merchant_id
            JOIN Categories c ON m.category_id=c.category_id
            WHERE c.name='Uncategorised'
            """
        ).fetchone()[0]
 
    total = stats["total"] or 1
    print("\n" + "─" * 60)
    print(f"  {'CATEGORY':<28} {'TXNs':>5}  {'TOTAL (SGD)':>14}")
    print("─" * 60)
    for r in spend:
        print(f"  {r['name']:<28} {r['n']:>5}  {r['total']:>14.2f}")
    print("─" * 60)
    print(f"  Code coverage   : {stats['coded']}/{total} "
          f"({100*stats['coded']//total}%)")
    print(f"  Unique merchants: {stats['merchants']}")
    print(f"  Uncategorised   : {uncat}/{total} "
          f"({100*uncat//total}%)\n")

# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Personal Finance ETL pipeline")
    p.add_argument("--csv",   default=DEFAULT_CSV,    help="Bank CSV export")
    p.add_argument("--db",    default=DEFAULT_DB,     help="SQLite database path")
    p.add_argument("--codes", default=CODES_TXT_FILE, help="DBS transaction codes txt")
    p.add_argument("--reset", action="store_true",
                   help="Delete the database file before loading (full reload)")
    return p.parse_args()

def main():
    args = parse_args()

    if args.reset and Path(args.db).exists():
        Path(args.db).unlink()
        log.info("Existing database deleted (--reset).")

    # ── Pipeline ─────────────────────────────────────────────────────────────

    with get_connection(args.db) as conn:
        initialise_schema(conn)                          # DDL
 
    seed_codes(args.db, args.codes)                      # seed TransactionCodes
 
    raw_df   = extract(args.csv)                         # Step 1: Extract
    clean_df = transform(raw_df)                         # Step 2: Transform
 
    with get_connection(args.db) as conn:
        code_cache           = build_code_cache(conn)
        inserted, skipped    = load_transactions(        # Step 3: Load
            conn, clean_df, code_cache
        )
 
    log.info("Inserted: %d  |  Skipped (duplicates): %d", inserted, skipped)
    print_summary(args.db)
    log.info("Pipeline complete.")
 
if __name__ == "__main__":
    main()