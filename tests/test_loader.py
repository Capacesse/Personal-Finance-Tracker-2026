"""
Load step: rows reach the database once, and only once.
"""

import pytest

from core.loader import load_transactions
from tests.conftest import run_transform


def count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TestLoad:
    def test_all_sample_rows_are_inserted(self, conn, sample_df, code_cache):
        inserted, skipped = load_transactions(conn, sample_df, code_cache)
        assert (inserted, skipped) == (13, 0)
        assert count(conn, "Transactions") == 13

    def test_reimporting_the_same_file_adds_nothing(self, conn, sample_df, code_cache):
        """Acceptance criterion from MILESTONES.md: re-import is idempotent."""
        load_transactions(conn, sample_df, code_cache)
        inserted, skipped = load_transactions(conn, sample_df, code_cache)
        assert (inserted, skipped) == (0, 13)
        assert count(conn, "Transactions") == 13

    def test_overlapping_file_adds_only_new_rows(self, conn, sample_df, code_cache):
        load_transactions(conn, sample_df, code_cache)
        overlap = run_transform(
            "2025-01-02,FAIRPRICE XTRA JURONG SI SGP 02JAN 5264-7110-0000-0000 000000,45.30,,POS",
            "2025-02-01,SPOTIFY P1D2E3F4 SI SGP 01FEB 5264-7110-0000-0000 000000,9.99,,MST",
        )
        inserted, skipped = load_transactions(conn, overlap, code_cache)
        assert (inserted, skipped) == (1, 1)
        assert count(conn, "Transactions") == 14

    def test_identical_purchases_load_once_each_and_reimport_adds_nothing(
        self, conn, code_cache
    ):
        rows = ["2025-01-02,BUS/MRT 12345,1.09,,POS"] * 2
        assert load_transactions(conn, run_transform(*rows), code_cache) == (2, 0)
        assert load_transactions(conn, run_transform(*rows), code_cache) == (0, 2)
        assert count(conn, "Transactions") == 2

    def test_later_export_with_one_more_identical_purchase_adds_one(
        self, conn, code_cache
    ):
        """Morning export has two rides; evening export of the same day has three."""
        row = "2025-01-02,BUS/MRT 12345,1.09,,POS"
        load_transactions(conn, run_transform(row, row), code_cache)
        assert load_transactions(conn, run_transform(row, row, row), code_cache) == (1, 2)
        assert count(conn, "Transactions") == 3

    def test_same_merchant_twice_creates_one_merchant_row(self, conn, code_cache):
        df = run_transform(
            "2025-01-02,WATSONS SINGAPORE SI SGP 02JAN 5264-7110-0000-0000 000000,10.00,,POS",
            "2025-01-09,WATSONS SINGAPORE SI SGP 09JAN 5264-7110-0000-0000 000000,12.00,,POS",
        )
        load_transactions(conn, df, code_cache)
        assert count(conn, "Transactions") == 2
        assert count(conn, "Merchants") == 1

    def test_unknown_code_is_stored_as_null(self, conn, code_cache):
        """A code missing from TransactionCodes must not break the foreign key."""
        df = run_transform("2025-01-02,ZZZ SHOP,10.00,,QQQQ")
        load_transactions(conn, df, code_cache)
        stored = conn.execute("SELECT transaction_code FROM Transactions").fetchone()[0]
        assert stored is None


class TestDatabaseTotals:
    def test_totals_in_database_match_the_csv(self, conn, sample_df, code_cache):
        load_transactions(conn, sample_df, code_cache)
        spent, income = conn.execute(
            """
            SELECT SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END),
                   SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)
            FROM Transactions
            """
        ).fetchone()
        assert spent == pytest.approx(-548.45)
        assert income == pytest.approx(3501.20)

    def test_view_returns_one_row_per_transaction(self, conn, sample_df, code_cache):
        load_transactions(conn, sample_df, code_cache)
        assert count(conn, "v_transactions_full") == 13

    def test_category_totals_from_sample(self, conn, sample_df, code_cache):
        load_transactions(conn, sample_df, code_cache)
        rows = conn.execute(
            """
            SELECT category, COUNT(*), ROUND(SUM(amount), 2)
            FROM v_transactions_full GROUP BY category
            """
        ).fetchall()
        totals = {r[0]: (r[1], r[2]) for r in rows}
        assert totals == {
            "Cash Withdrawals":  (1, -200.00),
            "Utilities":         (1, -145.00),
            "Food & Drink":      (2, -67.70),
            "Transfers":         (1, -50.00),
            "Transport":         (2, -32.70),
            "Subscriptions":     (3, -29.95),
            "Health & Wellness": (1, -23.10),
            "Income":            (2, 3501.20),
        }
