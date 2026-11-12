"""
Dashboard data layer: the filtered views and aggregations behind the charts.
These functions take DataFrames, so they are tested without starting Streamlit.
"""

import pandas as pd
import pytest

from dashboard.data import (
    FilterState,
    agg_by_category,
    agg_category_share,
    agg_cumulative_spend,
    get_budget_variance,
    get_expense_view,
    get_full_view,
    get_month_scoped,
    load_all_transactions,
    load_budgets,
    save_budgets,
    update_merchant_category,
)

ALL_CATEGORIES = [
    "Cash Withdrawals", "Food & Drink", "Health & Wellness", "Income",
    "Subscriptions", "Transfers", "Transport", "Utilities",
]


def state(**overrides) -> FilterState:
    defaults = dict(
        selected_months=["2025-01"],
        selected_categories=ALL_CATEGORIES,
        show_transfers=False,
        show_income=False,
    )
    return FilterState(**{**defaults, **overrides})


@pytest.fixture
def df_all(loaded_db) -> pd.DataFrame:
    load_all_transactions.clear()
    return load_all_transactions(loaded_db)


class TestLoading:
    def test_missing_database_returns_empty_frame(self, tmp_path):
        load_all_transactions.clear()
        assert load_all_transactions(str(tmp_path / "nope.db")).empty

    def test_all_rows_loaded_with_helper_columns(self, df_all):
        assert len(df_all) == 13
        assert {"month", "day", "is_expense"} <= set(df_all.columns)
        assert set(df_all["month"]) == {"2025-01"}


class TestFilteredViews:
    def test_expense_view_hides_transfers_and_cash_by_default(self, df_all):
        view = get_expense_view(df_all, state())
        assert not set(view["category"]) & {"Transfers", "Cash Withdrawals", "Income"}
        assert view["amount"].sum() == pytest.approx(-298.45)

    def test_expense_view_includes_transfers_when_toggled(self, df_all):
        view = get_expense_view(df_all, state(show_transfers=True))
        assert view["amount"].sum() == pytest.approx(-548.45)

    def test_expense_view_never_contains_income(self, df_all):
        view = get_expense_view(df_all, state(show_transfers=True, show_income=True))
        assert (view["amount"] < 0).all()

    def test_category_filter_narrows_expense_view(self, df_all):
        view = get_expense_view(df_all, state(selected_categories=["Subscriptions"]))
        assert len(view) == 3
        assert view["amount"].sum() == pytest.approx(-29.95)

    def test_full_view_hides_income_by_default(self, df_all):
        assert len(get_full_view(df_all, state())) == 11

    def test_full_view_shows_income_when_toggled(self, df_all):
        assert len(get_full_view(df_all, state(show_income=True))) == 13

    def test_month_filter_with_no_matching_month_is_empty(self, df_all):
        assert get_month_scoped(df_all, state(selected_months=["2030-01"])).empty

    def test_month_scope_ignores_category_filter(self, df_all):
        """KPIs use this view, so income must survive a category filter."""
        view = get_month_scoped(df_all, state(selected_categories=["Subscriptions"]))
        assert len(view) == 13


class TestAggregations:
    def test_category_totals_are_positive_and_sorted(self, df_all):
        cat = agg_by_category(get_expense_view(df_all, state()))
        assert cat.iloc[0]["category"] == "Utilities"
        assert cat.iloc[0]["spent"] == pytest.approx(145.00)
        assert cat["spent"].is_monotonic_decreasing

    def test_category_shares_sum_to_100(self, df_all):
        share = agg_category_share(get_expense_view(df_all, state()))
        assert share["share_pct"].sum() == pytest.approx(100.0, abs=0.5)

    def test_category_share_of_empty_view_does_not_divide_by_zero(self, df_all):
        share = agg_category_share(df_all.iloc[0:0])
        assert share.empty

    def test_cumulative_spend_ends_at_total_spend(self, df_all):
        cum = agg_cumulative_spend(get_expense_view(df_all, state()))
        assert cum["cumulative_spend"].iloc[-1] == pytest.approx(298.45)
        assert cum["cumulative_spend"].is_monotonic_increasing


class TestBudgets:
    def test_budgets_round_trip_through_database(self, loaded_db):
        budgets = pd.DataFrame(
            {"category": ["Food & Drink", "Transport"], "monthly_limit": [100.0, 20.0]}
        )
        save_budgets(loaded_db, budgets)
        loaded = load_budgets(loaded_db).set_index("category")["monthly_limit"].to_dict()
        assert loaded == {"Food & Drink": 100.0, "Transport": 20.0}

    def test_variance_flags_overspent_category_first(self, df_all):
        budgets = pd.DataFrame(
            {"category": ["Food & Drink", "Transport"], "monthly_limit": [100.0, 20.0]}
        )
        variance = get_budget_variance(get_expense_view(df_all, state()), budgets)
        transport = variance.set_index("category").loc["Transport"]
        assert transport["remaining"] == pytest.approx(-12.70)   # 20.00 - 32.70
        assert transport["utilisation_pct"] > 100

        food = variance.set_index("category").loc["Food & Drink"]
        assert food["remaining"] == pytest.approx(32.30)         # 100.00 - 67.70


class TestCategoryOverride:
    def test_recategorising_a_merchant_moves_its_transactions(self, loaded_db):
        update_merchant_category(loaded_db, "WATSONS", "Shopping")
        load_all_transactions.clear()
        df = load_all_transactions(loaded_db)
        assert df.loc[df["merchant"] == "WATSONS", "category"].tolist() == ["Shopping"]

    def test_unknown_category_name_changes_nothing(self, loaded_db):
        update_merchant_category(loaded_db, "WATSONS", "Not A Real Category")
        load_all_transactions.clear()
        df = load_all_transactions(loaded_db)
        assert df.loc[df["merchant"] == "WATSONS", "category"].tolist() == ["Health & Wellness"]
