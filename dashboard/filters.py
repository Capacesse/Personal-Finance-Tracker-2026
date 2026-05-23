"""
dashboard/filters.py
====================
Sidebar UI only. Returns a FilterState defined in dashboard.data.
There is deliberately no second FilterState dataclass here.
"""

import pandas as pd
import streamlit as st

from dashboard.data import FilterState


def render_sidebar(df: pd.DataFrame, db_path: str) -> FilterState:
    """
    Render sidebar controls and return the current FilterState.
    All filter logic (actually applying the filters to DataFrames)
    lives in dashboard/data.py, not here.
    """
    st.sidebar.header("🔍 Filters")

    # ── Month range ───────────────────────────────────────────────────────────
    all_months = sorted(df["month"].unique())
    selected_months = st.sidebar.multiselect(
        "Month(s)",
        options=all_months,
        default=all_months,
    )

    # ── Category filter ───────────────────────────────────────────────────────
    all_categories = sorted(df["category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Categories",
        options=all_categories,
        default=all_categories,
    )

    # ── Toggle switches ───────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### View options")
    show_transfers = st.sidebar.checkbox(
        "Include Transfers / PayNow",
        value=False,
        help="Wallet top-ups and peer payments inflate spend totals",
    )
    show_income = st.sidebar.checkbox(
        "Include Income & Credits",
        value=False,
    )

    # ── DB info ───────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    code_cov = (
        df["transaction_code"].notna().sum() / max(len(df), 1) * 100
    )
    st.sidebar.metric("🔖 Code Coverage", f"{code_cov:.0f}%")
    st.sidebar.caption(f"`{db_path}`  ·  {len(df):,} total transactions")

    return FilterState(
        selected_months=selected_months,
        selected_categories=selected_categories,
        show_transfers=show_transfers,
        show_income=show_income,
    )