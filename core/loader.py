"""
core/loader.py
==============
Schema init, code seeding, and row insertion.
Works with any sqlite3.Connection — on-disk (etl.py) or in-memory (app.py).
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from core.categoriser import categorise

log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_schema_path() -> Path:
    return _SCHEMA_PATH


def initialise_schema(conn: sqlite3.Connection,
                      schema_path: Path | None = None) -> None:
    """Apply DDL. Safe to call on every run (all statements use IF NOT EXISTS)."""
    path = schema_path or _SCHEMA_PATH
    conn.executescript(path.read_text())
    log.info("Schema applied.")


def build_code_cache(conn: sqlite3.Connection) -> dict[str, str]:
    """Load TransactionCodes → category_name into a dict for O(1) lookup."""
    rows = conn.execute(
        """
        SELECT tc.code, c.name
        FROM   TransactionCodes tc
        JOIN   Categories       c ON tc.category_id = c.category_id
        """
    ).fetchall()
    cache = {code.upper(): cat for code, cat in rows}
    log.info("Code cache: %d entries.", len(cache))
    return cache


def load_transactions(conn: sqlite3.Connection,
                      df: pd.DataFrame,
                      code_cache: dict[str, str]) -> tuple[int, int]:
    """
    Insert cleaned rows into Categories → Merchants → Transactions.

    Uses INSERT OR IGNORE on transaction_hash so re-importing the same
    CSV never creates duplicate rows.

    Returns (inserted, skipped) counts.
    """
    inserted = skipped = 0

    for _, row in df.iterrows():
        code     = row["transaction_code"]
        category = categorise(
            code, row["description"], row["amount"], code_cache
        )

        category_id = _get_or_create(
            conn, "Categories", "name", "category_id", category
        )
        merchant_id = _get_or_create(
            conn, "Merchants", "name", "merchant_id", row["merchant_name"],
            extra={"category_id": category_id},
        )

        # Only store code as FK if it's confirmed in TransactionCodes
        code_fk = (
            code if (isinstance(code, str) and code in code_cache) else None
        )

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO Transactions
                (transaction_date, amount, description,
                 merchant_id, transaction_code, transaction_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["transaction_date"],
                row["amount"],
                row["description"],
                merchant_id,
                code_fk,
                row["transaction_hash"],
            ),
        )
        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1   # hash already existed — duplicate silently ignored

    log.info("Load complete: %d inserted, %d duplicate(s) skipped.",
             inserted, skipped)
    return inserted, skipped


def _get_or_create(conn, table, name_col, id_col, name, extra=None):
    """Fetch PK by name or insert and return the new PK."""
    extra = extra or {}
    row = conn.execute(
        f"SELECT {id_col} FROM {table} WHERE {name_col} = ?", (name,)
    ).fetchone()
    if row:
        return row[0]
    cols  = name_col + (", " + ", ".join(extra) if extra else "")
    marks = "?" + (", ?" * len(extra))
    cur   = conn.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({marks})",
        (name, *extra.values()),
    )
    return cur.lastrowid
