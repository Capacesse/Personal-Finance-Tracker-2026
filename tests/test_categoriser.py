"""
The tiered categoriser: which rule wins for a given code, description, amount.
"""

import pytest

from core.categoriser import categorise


class TestTiers:
    @pytest.mark.parametrize("code", ["AWL", "WDL", "ATM"])
    def test_cash_codes_always_mean_cash_withdrawal(self, code, code_cache):
        assert categorise(code, "ATM CASH WITHDRAWAL", -200.0, code_cache) == "Cash Withdrawals"

    def test_cash_code_beats_merchant_keyword(self, code_cache):
        # Description mentions a food keyword, but the code says cash
        assert categorise("AWL", "ATM AT STARBUCKS MALL", -50.0, code_cache) == "Cash Withdrawals"

    @pytest.mark.parametrize("code", ["IBG", "ICT", "GR", "PAY"])
    def test_bidirectional_code_inbound_is_income(self, code, code_cache):
        assert categorise(code, "TRANSFER", 500.0, code_cache) == "Income"

    @pytest.mark.parametrize("code", ["IBG", "ICT", "GR", "PAY"])
    def test_bidirectional_code_outbound_is_paynow(self, code, code_cache):
        assert categorise(code, "TRANSFER", -500.0, code_cache) == "PayNow & FAST"

    @pytest.mark.parametrize(
        "code, description, expected",
        [
            ("POS", "FAIRPRICE XTRA JURONG", "Food & Drink"),
            ("MST", "SPOTIFY P1D2E3F4", "Subscriptions"),
            ("BAT", "COMFORT DELGRO TAXI", "Transport"),
            ("POS", "WATSONS SINGAPORE", "Health & Wellness"),
        ],
    )
    def test_generic_code_falls_through_to_merchant_keyword(
        self, code, description, expected, code_cache
    ):
        assert categorise(code, description, -10.0, code_cache) == expected

    @pytest.mark.parametrize(
        "description, expected",
        [
            ("GRAB* GPC-000000000000", "Transport"),
            ("GOOGLE*YOUTUBEPREMIUM", "Subscriptions"),
            ("FP*FOOD PANDA SINGAPORE", "Food & Drink"),
        ],
    )
    def test_missing_code_uses_merchant_keyword(self, description, expected, code_cache):
        assert categorise(None, description, -10.0, code_cache) == expected

    def test_no_code_and_no_keyword_is_uncategorised(self, code_cache):
        assert categorise(None, "ZZZ UNKNOWN SHOP 123", -10.0, code_cache) == "Uncategorised"

    def test_unknown_code_and_no_keyword_is_uncategorised(self, code_cache):
        assert categorise("QQQQ", "ZZZ UNKNOWN SHOP 123", -10.0, code_cache) == "Uncategorised"


class TestKeywordOrdering:
    """Longer, more specific keywords must win over shorter ones."""

    def test_grab_food_is_food_not_transport(self, code_cache):
        assert categorise(None, "GRAB FOOD ORDER", -15.0, code_cache) == "Food & Drink"

    def test_bare_grab_is_transport(self, code_cache):
        assert categorise(None, "GRAB", -15.0, code_cache) == "Transport"

    def test_amazon_prime_is_subscription_not_shopping(self, code_cache):
        assert categorise(None, "AMAZON PRIME MEMBERSHIP", -2.99, code_cache) == "Subscriptions"

    def test_plain_amazon_is_shopping(self, code_cache):
        assert categorise(None, "AMAZON SG ORDER", -40.0, code_cache) == "Shopping"

    def test_keyword_match_is_case_insensitive(self, code_cache):
        assert categorise(None, "netflix.com", -15.98, code_cache) == "Subscriptions"


class TestSampleCoverage:
    def test_every_sample_transaction_gets_a_category(self, sample_df, code_cache):
        """Acceptance criterion from MILESTONES.md: 0% uncategorised."""
        categories = [
            categorise(r.transaction_code, r.description, r.amount, code_cache)
            for r in sample_df.itertuples()
        ]
        assert "Uncategorised" not in categories

    def test_salary_in_sample_is_income(self, sample_df, code_cache):
        salary = sample_df[sample_df["description"].str.contains("SALARY")].iloc[0]
        assert (
            categorise(salary.transaction_code, salary.description, salary.amount, code_cache)
            == "Income"
        )
