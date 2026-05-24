"""
app.py — Entry Point
=====================
Orchestrates the modular dashboard components.
No business logic, no SQL, no chart construction lives here.

Run:
    streamlit run app.py
    streamlit run app.py -- --db path/to/finance.db
"""

import argparse
import pandas as pd
import streamlit as st

from dashboard.charts import (
    build_category_bar,
    build_category_share_bar,
    build_daily_spend_bar,
    build_income_vs_spend_bar,
    build_monthly_trend_bar,
    build_top_merchants_bar,
)
from dashboard.data import (
    EXCLUDE_FROM_SPEND,
    agg_by_category,
    agg_category_share,
    agg_daily_spend,
    agg_monthly_trend,
    agg_top_merchants,
    get_expense_view,
    get_full_view,
    get_month_scoped,
    load_all_transactions,
    load_budgets,
    save_budgets
)
from dashboard.filters import render_sidebar
from dashboard.kpis import render_kpi_row
from dashboard.tables import render_transaction_log, render_uncategorised_review

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB path ───────────────────────────────────────────────────────────────────

def _db_path() -> str:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--db", default="finance.db")
    return p.parse_known_args()[0].db

DB_PATH = _db_path()

# ── 1. Load data ──────────────────────────────────────────────────────────────

df_all = load_all_transactions(DB_PATH)

if df_all.empty:
    st.error(
        f"No database found at **{DB_PATH}**. "
        "Run `python etl.py --reset` first."
    )
    st.stop()

# ── 2. Sidebar → FilterState ──────────────────────────────────────────────────

state = render_sidebar(df_all, DB_PATH)

# ── 3. Derive filtered views ──────────────────────────────────────────────────

df_month_scope = get_month_scoped(df_all, state)  # KPIs & income chart
df_expenses    = get_expense_view(df_all, state)  # all spend charts
df_full        = get_full_view(df_all, state)     # transaction log

# ── 4. Pre-aggregate once — reused by multiple charts ────────────────────────

cat_df   = agg_by_category(df_expenses)
share_df = agg_category_share(df_expenses)
trend_df = agg_monthly_trend(df_expenses)
daily_df = agg_daily_spend(df_expenses)
merch_df = agg_top_merchants(df_expenses)

# ── 5. Render ─────────────────────────────────────────────────────────────────

st.title("💳 Personal Finance Tracker")

months_label = (
    ", ".join(state.selected_months)
    if len(state.selected_months) <= 3
    else f"{len(state.selected_months)} months selected"
)
st.caption(f"Showing {len(df_expenses):,} expense transactions · {months_label}")

render_kpi_row(df_month_scope, df_expenses)
st.markdown("---")

# Row 1 — Category breakdown + monthly trend
r1_l, r1_r = st.columns(2)
with r1_l:
    st.plotly_chart(build_category_bar(cat_df), use_container_width=True)
with r1_r:
    st.plotly_chart(build_monthly_trend_bar(trend_df), use_container_width=True)

st.markdown("---")

# Row 2 — Category share + income vs spend
r2_l, r2_r = st.columns(2)
with r2_l:
    st.plotly_chart(build_category_share_bar(share_df), use_container_width=True)
with r2_r:
    st.plotly_chart(build_income_vs_spend_bar(df_month_scope), use_container_width=True)

st.markdown("---")

# Row 3 — Daily spend + top merchants
r3_l, r3_r = st.columns(2)
with r3_l:
    st.plotly_chart(build_daily_spend_bar(daily_df), use_container_width=True)
with r3_r:
    st.plotly_chart(build_top_merchants_bar(merch_df), use_container_width=True)

st.markdown("---")

render_uncategorised_review(df_all)
st.markdown("---")
render_transaction_log(df_full)
st.markdown("---")
st.subheader("🎯 Monthly Budget Targets")

df_budgets = load_budgets(DB_PATH)

if df_budgets.empty:
    all_cats = [c for c in df_all["category"].unique() if c not in EXCLUDE_FROM_SPEND]
    df_budgets = pd.DataFrame({"category": all_cats, "monthly_limit": 0.0})

edited_budgets = st.data_editor(
    df_budgets,
    use_container_width=True,
    num_rows="dynamic", # Lets you add or delete rows
    column_config={
        "category": st.column_config.TextColumn("Category", disabled=True),
        "monthly_limit": st.column_config.NumberColumn(
            "Monthly Limit (SGD)", 
            min_value=0.0, 
            format="$ %.2f"
        )
    },
    hide_index=True,
    key="budget_editor"
)

if st.button("Save Budget Limits", type="primary"):
    save_budgets(DB_PATH, edited_budgets)
    st.success("✅ Budgets successfully updated!")
    st.rerun()