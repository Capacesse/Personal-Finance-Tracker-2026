"""
Shared fixtures.

Every test gets its own throwaway SQLite database in a temporary folder, so
tests never touch a real finance.db and never depend on each other.
"""

import sqlite3
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from core.loader import build_code_cache, initialise_schema, load_transactions
from core.transformer import extract, transform
from transaction_codes_loader import parse_codes_file, seed_transaction_codes

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "bank_export_sample.csv"
CODES_TXT = ROOT / "DBS Transaction Codes & Descriptions.txt"

DBS_HEADER = "Transaction Date,Description,Withdrawal Amount,Deposit Amount,Transaction Code"


def make_csv(*rows: str, header: str = DBS_HEADER) -> StringIO:
    """Build an in-memory DBS-format CSV from row strings."""
    return StringIO("\n".join([header, *rows]) + "\n")


def run_transform(*rows: str, header: str = DBS_HEADER) -> pd.DataFrame:
    """Extract and transform rows given as CSV strings."""
    return transform(extract(make_csv(*rows, header=header)))


@pytest.fixture
def db_path(tmp_path) -> str:
    """Path to an empty database with the schema and DBS codes loaded."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    initialise_schema(conn)
    seed_transaction_codes(conn, parse_codes_file(str(CODES_TXT)))
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def conn(db_path):
    """Open connection to the empty test database."""
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    yield c
    c.close()


@pytest.fixture
def code_cache(conn) -> dict[str, str]:
    return build_code_cache(conn)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """The bundled sample CSV after extract + transform."""
    return transform(extract(str(SAMPLE_CSV)))


@pytest.fixture
def loaded_db(db_path, sample_df) -> str:
    """Database with the sample CSV loaded. Returns its path."""
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    load_transactions(c, sample_df, build_code_cache(c))
    c.commit()
    c.close()
    return db_path
