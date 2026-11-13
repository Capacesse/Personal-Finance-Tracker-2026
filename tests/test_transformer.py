"""
Transform step: dates, amounts, merchant names, hashes, input validation.
"""

import pandas as pd
import pytest

from core.transformer import _compute_hash, _normalise_merchant
from tests.conftest import run_transform


# ── Dates ─────────────────────────────────────────────────────────────────────

class TestDates:
    def test_iso_date_is_not_read_as_day_first(self):
        """
        Regression test for a real defect: 2025-01-02 was parsed as
        1 February because day-first parsing was applied to ISO dates.
        """
        df = run_transform("2025-01-02,FAIRPRICE,45.30,,POS")
        assert df.iloc[0]["transaction_date"] == "2025-01-02"
        assert df.iloc[0]["year_month"] == "2025-01"

    def test_sample_csv_is_all_january(self, sample_df):
        """Every row in the sample file is dated January 2025."""
        assert set(sample_df["year_month"]) == {"2025-01"}

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("02/01/2025", "2025-01-02"),   # day-first with slashes
            ("02-01-2025", "2025-01-02"),   # day-first with dashes
            ("02 Jan 2025", "2025-01-02"),  # DBS statement style
            ("15/01/2025", "2025-01-15"),   # day > 12, no ambiguity
            ("2025-12-31", "2025-12-31"),   # ISO at year end
        ],
    )
    def test_supported_date_formats(self, raw, expected):
        df = run_transform(f"{raw},FAIRPRICE,10.00,,POS")
        assert df.iloc[0]["transaction_date"] == expected

    def test_unparseable_date_row_is_dropped(self):
        df = run_transform(
            "not a date,FAIRPRICE,10.00,,POS",
            "2025-01-05,SPOTIFY,9.99,,MST",
        )
        assert len(df) == 1
        assert df.iloc[0]["description"] == "SPOTIFY"


# ── Amounts ───────────────────────────────────────────────────────────────────

class TestAmounts:
    def test_withdrawal_is_negative(self):
        df = run_transform("2025-01-02,FAIRPRICE,45.30,,POS")
        assert df.iloc[0]["amount"] == pytest.approx(-45.30)

    def test_deposit_is_positive(self):
        df = run_transform("2025-01-07,SALARY CREDIT,,3500.00,IBG")
        assert df.iloc[0]["amount"] == pytest.approx(3500.00)

    def test_zero_amount_row_is_dropped(self):
        df = run_transform(
            "2025-01-02,BALANCE ENQUIRY,,,",
            "2025-01-03,SPOTIFY,9.99,,MST",
        )
        assert list(df["description"]) == ["SPOTIFY"]

    def test_sample_totals_match_manual_calculation(self, sample_df):
        """Totals added up by hand from bank_export_sample.csv."""
        spent = sample_df.loc[sample_df["amount"] < 0, "amount"].sum()
        income = sample_df.loc[sample_df["amount"] > 0, "amount"].sum()
        assert spent == pytest.approx(-548.45)
        assert income == pytest.approx(3501.20)


# ── Merchant name cleaning ────────────────────────────────────────────────────

class TestMerchantNames:
    @pytest.mark.parametrize(
        "description, expected",
        [
            # Card terminal suffix is stripped
            ("WATSONS SINGAPORE SI SGP 08JAN 5264-7110-0000-0000 000000", "WATSONS"),
            ("NETFLIX.COM SI SGP 09JAN 5264-7110-0000-0000 000000", "NETFLIX.COM"),
            # Variants collapse to one canonical merchant
            ("FAIRPRICE XTRA JURONG SI SGP 02JAN 5264-7110-0000-0000 000000", "FAIRPRICE"),
            ("NTUC FAIRPRICE CO-OP", "FAIRPRICE"),
            ("FAIRPRICE FINEST BUKIT TIMAH", "FAIRPRICE"),
            # Reference codes are stripped
            ("GRAB* GPC-000000000000 SI SGP 05JAN 5264-7110-0000-0000 000000", "GRAB"),
            ("FP*FOOD PANDA SINGAPORE SGP 15JAN 5264-7110-0000-0000 000000", "FOOD PANDA"),
            ("GOOGLE*YOUTUBEPREMIUM SI SGP 11JAN 5264-7110-0000-0000 000000", "YOUTUBE PREMIUM"),
        ],
    )
    def test_normalise_merchant(self, description, expected):
        assert _normalise_merchant(description) == expected

    def test_lowercase_input_gives_same_merchant(self):
        assert _normalise_merchant("watsons singapore") == _normalise_merchant(
            "WATSONS SINGAPORE"
        )

    def test_merchant_name_is_capped_at_45_characters(self):
        assert len(_normalise_merchant("A" * 80)) <= 45


class TestReadmeExamples:
    """
    The four examples in the README's cleaning table, copied exactly.
    If the README and the code ever disagree again, this fails.
    """

    @pytest.mark.parametrize(
        "raw, cleaned",
        [
            ("GRAB* GPC-3140FD79BA09 SI SGP 25MAR 5264-7110-0715-3382", "GRAB"),
            ("GOOGLE*YOUTUBEPREMIUM G. SGP 30NOV 5264-7110-0715-3382", "YOUTUBE PREMIUM"),
            ("FP*FOOD PANDA SINGAPORE SGP 22APR 5264-7110-0715-3382", "FOOD PANDA"),
            ("AMZNPRIMESG MEMBERSHI SI SGP 22APR 5264-7110-0715-3382", "AMAZON PRIME"),
        ],
    )
    def test_readme_table_row(self, raw, cleaned):
        assert _normalise_merchant(raw) == cleaned

    def test_trailing_initial_is_only_stripped_at_the_end(self):
        # "G." in the middle of a name must survive
        assert _normalise_merchant("G. H. CAFE") == "G. H. CAFE"


# ── Deduplication hash ────────────────────────────────────────────────────────

class TestHash:
    def test_hash_is_deterministic(self):
        a = _compute_hash("2025-01-02", -45.30, "FAIRPRICE")
        b = _compute_hash("2025-01-02", -45.30, "FAIRPRICE")
        assert a == b

    @pytest.mark.parametrize(
        "date, amount, description",
        [
            ("2025-01-03", -45.30, "FAIRPRICE"),  # different date
            ("2025-01-02", -45.31, "FAIRPRICE"),  # different amount
            ("2025-01-02", -45.30, "GIANT"),      # different description
        ],
    )
    def test_hash_changes_when_any_field_changes(self, date, amount, description):
        base = _compute_hash("2025-01-02", -45.30, "FAIRPRICE")
        assert _compute_hash(date, amount, description) != base

    def test_two_identical_purchases_on_one_day_are_both_kept(self):
        """
        Regression test: two SGD 1.09 bus rides on the same day used to be
        merged into one transaction because their hashes were equal.
        """
        row = "2025-01-02,BUS/MRT 12345,1.09,,POS"
        df = run_transform(row, row)
        assert len(df) == 2
        assert df["transaction_hash"].nunique() == 2

    def test_repeat_numbering_is_the_same_on_every_import(self):
        """Same file in, same hashes out, so a re-import can be recognised."""
        rows = ["2025-01-02,BUS/MRT 12345,1.09,,POS"] * 3
        first = run_transform(*rows)["transaction_hash"].tolist()
        second = run_transform(*rows)["transaction_hash"].tolist()
        assert first == second

    def test_first_occurrence_hash_matches_older_databases(self):
        """Occurrence 0 must hash exactly as before the repeat fix."""
        df = run_transform("2025-01-02,FAIRPRICE,45.30,,POS")
        assert df.iloc[0]["transaction_hash"] == _compute_hash(
            "2025-01-02", -45.30, "FAIRPRICE"
        )


# ── Input validation ──────────────────────────────────────────────────────────

class TestInputValidation:
    def test_unknown_bank_format_gives_clear_error(self):
        with pytest.raises(ValueError, match="Unsupported CSV format"):
            run_transform("2025-01-02,hello,1", header="Date,Memo,Value")

    def test_missing_required_column_is_named_in_error(self):
        # DBS fingerprint columns are present, but Deposit Amount is not
        header = "Transaction Date,Description,Withdrawal Amount,Transaction Code"
        with pytest.raises(ValueError, match="deposit"):
            run_transform("2025-01-02,FAIRPRICE,45.30,POS", header=header)

    def test_blank_transaction_code_is_treated_as_missing(self):
        df = run_transform("2025-01-05,GRAB* GPC-0000,18.50,,")
        assert pd.isna(df.iloc[0]["transaction_code"])

    def test_transaction_code_is_uppercased_and_trimmed(self):
        df = run_transform("2025-01-02,FAIRPRICE,45.30,, pos ")
        assert df.iloc[0]["transaction_code"] == "POS"

    def test_blank_description_gets_placeholder(self):
        df = run_transform("2025-01-02,,45.30,,POS")
        assert df.iloc[0]["description"] == "UNKNOWN PAYEE"
