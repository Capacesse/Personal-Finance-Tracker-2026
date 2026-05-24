"""
dashboard/data.py
=================
All data access for the dashboard.  No Streamlit UI code lives here —
only queries, caching, and DataFrame transformations.

Design rules:
  • Every public function is decorated with @st.cache_data so results
    are reused across reruns unless the inputs change.
  • All DB connections are opened and closed within the function —
    never leak a connection into the caller.
  • Filter logic lives here so charts and KPIs all work from the
    same filtered DataFrames, never filtering independently.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Categories that distort pure "spending" views ─────────────────────────────
EXCLUDE_FROM_SPEND: list[str] = [
    "Income",
    "Transfers",
    "PayNow & FAST",
    "Cash Withdrawals",
    "Internal Transfers",
]


# ── Filter state ──────────────────────────────────────────────────────────────

@dataclass
class FilterState:
    """
    Single object carrying every active filter.
    Passed from the sidebar renderer into every chart / table function,
    so there is no implicit global state.
    """
    selected_months:     list[str]
    selected_categories: list[str]
    show_transfers:      bool
    show_income:         bool


# ── Raw data loaders ──────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def load_all_transactions(db_path: str) -> pd.DataFrame:
    """
    Load the full v_transactions_full view into a DataFrame.
    Cached for 60 seconds — stale after an ETL re-run until refresh.

    Extra columns added here:
      month      — 'YYYY-MM' period string for grouping
      day        — integer day-of-month for daily charts
      is_expense — boolean convenience flag
    """
    if not Path(db_path).exists():
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT t.transaction_id,
               t.transaction_date,
               t.amount,
               t.description,
               t.transaction_code,
               tc.description  AS code_description,
               m.name          AS merchant,
               c.name          AS category
        FROM   Transactions   t
        JOIN   Merchants      m  ON t.merchant_id      = m.merchant_id
        JOIN   Categories     c  ON m.category_id      = c.category_id
        LEFT JOIN TransactionCodes tc ON t.transaction_code = tc.code
        ORDER  BY t.transaction_date DESC
        """,
        conn,
        parse_dates=["transaction_date"],
    )
    conn.close()

    df["month"]      = df["transaction_date"].dt.to_period("M").astype(str)
    df["day"]        = df["transaction_date"].dt.day
    df["is_expense"] = df["amount"] < 0
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_category_names(db_path: str) -> list[str]:
    """All category names from the DB, sorted alphabetically."""
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    names = pd.read_sql_query(
        "SELECT name FROM Categories ORDER BY name", conn
    )["name"].tolist()
    conn.close()
    return names


# ── Filtered views ────────────────────────────────────────────────────────────

def get_month_scoped(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    """
    Filter to selected months only — used for KPIs so that Income and
    Net Flow are never affected by the category or transfer toggles.
    """
    if state.selected_months:
        return df[df["month"].isin(state.selected_months)].copy()
    return df.copy()


def get_expense_view(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    """
    The primary spending DataFrame used by most charts.
    Applies: month filter → category filter → expense-only → transfer toggle.
    """
    result = df.copy()

    if state.selected_months:
        result = result[result["month"].isin(state.selected_months)]

    if state.selected_categories:
        result = result[result["category"].isin(state.selected_categories)]

    # Always start with expenses only for spend charts
    result = result[result["amount"] < 0]

    # Optionally suppress transfer-type categories
    if not state.show_transfers:
        result = result[~result["category"].isin([
            "Transfers", "PayNow & FAST",
            "Cash Withdrawals", "Internal Transfers",
        ])]

    return result.copy()


def get_full_view(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    """
    Month + category filtered view including both income and expenses.
    Used by the transaction log.
    """
    result = df.copy()
    if state.selected_months:
        result = result[result["month"].isin(state.selected_months)]
    if state.selected_categories:
        result = result[result["category"].isin(state.selected_categories)]
    if not state.show_income:
        result = result[result["amount"] < 0]
    return result.copy()


# ── Aggregations (pre-computed here so charts stay thin) ─────────────────────

def agg_by_category(df_expenses: pd.DataFrame) -> pd.DataFrame:
    """Total absolute spend per category, sorted descending."""
    return (
        df_expenses
        .groupby("category")["amount"]
        .sum().abs()
        .reset_index()
        .rename(columns={"amount": "spent"})
        .sort_values("spent", ascending=False)
    )


def agg_monthly_trend(df_expenses: pd.DataFrame) -> pd.DataFrame:
    """Total spend per (month, category) pair."""
    return (
        df_expenses
        .groupby(["month", "category"])["amount"]
        .sum().abs()
        .reset_index()
        .rename(columns={"amount": "spent"})
    )


def agg_daily_spend(df_expenses: pd.DataFrame) -> pd.DataFrame:
    """Total spend per (day, category) within the filtered window."""
    return (
        df_expenses
        .groupby(["day", "category"])["amount"]
        .sum().abs()
        .reset_index()
        .rename(columns={"amount": "spent"})
    )


def agg_top_merchants(df_expenses: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    """Top N merchants by total absolute spend."""
    return (
        df_expenses
        .groupby(["merchant", "category"])["amount"]
        .agg(total="sum", txns="count")
        .reset_index()
        .assign(total=lambda x: x["total"].abs())
        .sort_values("total", ascending=False)
        .head(n)
    )


def agg_category_share(df_expenses: pd.DataFrame) -> pd.DataFrame:
    """
    Category spend as a percentage of total — used for the share bar chart
    (replaces pie chart).
    """
    cat_df = agg_by_category(df_expenses)
    total  = cat_df["spent"].sum()
    if total == 0:
        cat_df["share_pct"] = 0.0
    else:
        cat_df["share_pct"] = (cat_df["spent"] / total * 100).round(1)
    return cat_df