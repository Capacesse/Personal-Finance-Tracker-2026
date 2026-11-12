"""
First-run setup: a missing database is built from the sample CSV.
"""

import sqlite3
from pathlib import Path

import pytest

from core.bootstrap import ensure_database


def row_count(path: str) -> int:
    conn = sqlite3.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM Transactions").fetchone()[0]
    conn.close()
    return n


def test_missing_database_is_created_with_sample_data(tmp_path):
    path = str(tmp_path / "new.db")
    assert ensure_database(path) is True
    assert row_count(path) == 13


def test_existing_database_is_left_alone(tmp_path):
    path = str(tmp_path / "new.db")
    ensure_database(path)

    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM Transactions WHERE amount > 0")
    conn.commit()
    conn.close()
    before = row_count(path)

    assert ensure_database(path) is False
    assert row_count(path) == before


def test_demo_database_has_transaction_codes(tmp_path):
    path = str(tmp_path / "new.db")
    ensure_database(path)
    conn = sqlite3.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM TransactionCodes").fetchone()[0]
    conn.close()
    assert n > 100


def test_failed_setup_leaves_no_half_built_database(tmp_path):
    path = str(tmp_path / "new.db")
    with pytest.raises(Exception):
        ensure_database(path, sample_csv=tmp_path / "does_not_exist.csv")
    assert not Path(path).exists()
