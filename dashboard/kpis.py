"""
dashboard/kpis.py
=================
Renders the top KPI metric row.
Receives pre-filtered DataFrames from dashboard/data.py — does
no filtering itself.
"""

import pandas as pd
import streamlit as st


def render_kpi_row(
    df_month_scope: pd.DataFrame,
    df_expenses: pd.DataFrame,
) -> None:
    """
    Render four KPI tiles:
        Total Spent | Total Income | Net Flow | Unique Merchants

    df_month_scope — month-filtered but NOT category/transfer-filtered,
                     so Income and Net Flow always reflect reality.
    df_expenses    — fully filtered expense-only view, for merchant count.
    """
    total_income = df_month_scope[df_month_scope["amount"] > 0]["amount"].sum()
    total_spent  = df_month_scope[df_month_scope["amount"] < 0]["amount"].sum()  # negative
    net_flow     = total_income + total_spent
    num_merchants = df_expenses["merchant"].nunique()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "💸 Total Spent",
        f"SGD {abs(total_spent):,.2f}",
    )
    c2.metric(
        "💰 Total Income",
        f"SGD {total_income:,.2f}",
    )
    c3.metric(
        "📊 Net Flow",
        f"SGD {net_flow:,.2f}",
        delta=f"SGD {net_flow:,.2f}",
        delta_color="normal",
        help="Income minus total outflows for the selected period",
    )
    c4.metric(
        "🏪 Unique Merchants",
        f"{num_merchants:,}",
        help="Within the current category and month filter",
    )