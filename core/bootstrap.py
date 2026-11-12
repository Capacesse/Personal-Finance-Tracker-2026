"""
core/bootstrap.py
=================
First-run setup. If no database exists yet, build one from the bundled
sample CSV so the dashboard has something to show.

Without this, a fresh clone or a cloud deployment starts with no database
and the app stops at an error before the upload box is ever rendered.
"""

import logging
import sqlite3
from pathlib import Path

from core.loader import build_code_cache, initialise_schema, load_transactions
from core.transformer import extract, transform

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = _ROOT / "bank_export_sample.csv"
CODES_TXT = _ROOT / "DBS Transaction Codes & Descriptions.txt"


def ensure_database(
    db_path: str,
    sample_csv: Path = SAMPLE_CSV,
    codes_path: Path = CODES_TXT,
) -> bool:
    """
    Create and seed the database if it does not exist.

    Returns True if a demo database was created, False if one was already
    there. An existing database is never modified.
    """
    if Path(db_path).exists():
        return False

    log.info("No database at %s, building demo data from %s", db_path, sample_csv)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        initialise_schema(conn)

        if Path(codes_path).exists():
            # Imported here because the module lives at the repo root.
            from transaction_codes_loader import (
                parse_codes_file,
                seed_transaction_codes,
            )
            seed_transaction_codes(conn, parse_codes_file(str(codes_path)))

        clean_df = transform(extract(str(sample_csv)))
        load_transactions(conn, clean_df, build_code_cache(conn))
        conn.commit()
    except Exception:
        conn.close()
        # Do not leave a half-built database behind: the next start would
        # treat it as valid and skip this setup.
        Path(db_path).unlink(missing_ok=True)
        raise
    conn.close()
    return True
