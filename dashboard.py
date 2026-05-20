"""
Personal Finance Engine — Streamlit Dashboard
==============================================
Reads directly from the SQLite database produced by etl.py.

Run with:
    streamlit run dashboard.py

Optional — point at a different database:
    streamlit run dashboard.py -- --db path/to/finance.db
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Personal Finance Engine",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Resolve DB path ───────────────────────────────────────────────────────────

def _get_db_path() -> str:
    """Allow --db flag when launched via `streamlit run dashboard.py -- --db x`."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", default="finance.db")
    args, _ = parser.parse_known_args()
    return args.db

DB_PATH = _get_db_path()

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)   # re-query at most once per minute; clear on reload
def load_transactions(db_path: str) -> pd.DataFrame:
    """Load the full denormalised transaction view into a DataFrame."""
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
        FROM   Transactions t
        JOIN   Merchants m        ON t.merchant_id      = m.merchant_id
        JOIN   Categories c       ON m.category_id      = c.category_id
        LEFT JOIN TransactionCodes tc ON t.transaction_code = tc.code
        ORDER  BY t.transaction_date DESC
        """,
        conn,
        parse_dates=["transaction_date"],
    )
    conn.close()
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["is_expense"] = df["amount"] < 0
    return df


@st.cache_data(ttl=60)
def load_categories(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cats = pd.read_sql_query(
        "SELECT name FROM Categories ORDER BY name", conn
    )["name"].tolist()
    conn.close()
    return cats

# ── Guard: DB must exist ──────────────────────────────────────────────────────

df_all = load_transactions(DB_PATH)

if df_all.empty:
    st.error(
        f"No database found at **{DB_PATH}**. "
        "Run `python etl.py` first to populate it."
    )
    st.stop()

# ── Sidebar — global filters ──────────────────────────────────────────────────

st.sidebar.title("🔍 Filters")

all_months = sorted(df_all["month"].unique())
selected_months = st.sidebar.multiselect(
    "Month(s)",
    options=all_months,
    default=all_months,
    help="Filter to specific months",
)

all_categories = load_categories(DB_PATH)
selected_categories = st.sidebar.multiselect(
    "Category",
    options=all_categories,
    default=all_categories,
)

show_income = st.sidebar.checkbox("Include income / credits", value=False,
    help="Uncheck to see expenses only")

st.sidebar.markdown("---")
st.sidebar.caption(f"Database: `{DB_PATH}`")
st.sidebar.caption(
    f"Last refreshed: {pd.Timestamp.now().strftime('%H:%M:%S')} "
    "· Cache TTL: 60 s"
)

# ── Apply filters ─────────────────────────────────────────────────────────────

df = df_all.copy()
if selected_months:
    df = df[df["month"].isin(selected_months)]
if selected_categories:
    df = df[df["category"].isin(selected_categories)]
if not show_income:
    df = df[df["amount"] < 0]

df_expenses = df[df["amount"] < 0].copy()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("💳 Personal Finance Engine")
st.markdown(f"Showing **{len(df):,}** transactions across **{df['month'].nunique()}** month(s)")

# ── KPI Row ───────────────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)

# KPI amounts use month-scoped unfiltered data so Net Flow / Income are
# never distorted by the "show_income" toggle or category filter.
df_month_scope = df_all[df_all["month"].isin(selected_months)] if selected_months else df_all

total_spent   = df_month_scope[df_month_scope["amount"] < 0]["amount"].sum()  # negative
total_income  = df_month_scope[df_month_scope["amount"] > 0]["amount"].sum()  # positive
net_flow      = total_income + total_spent   # income - |spent|; correct sign
num_merchants = df["merchant"].nunique()     # respects category filter
code_coverage = (
    df_all["transaction_code"].notna().sum() / max(len(df_all), 1) * 100
)

col1.metric("💸 Total Spent",    f"SGD {abs(total_spent):,.2f}")
col2.metric("💰 Total Income",   f"SGD {total_income:,.2f}")
col3.metric("📊 Net Flow",       f"SGD {net_flow:,.2f}",
            delta_color="normal")
col4.metric("🏪 Unique Merchants", f"{num_merchants:,}")
col5.metric("🔖 Code Coverage",   f"{code_coverage:.0f}%",
            help="% of transactions that had a DBS transaction code")

st.markdown("---")

# ── Row 1: Spend by Category  +  Monthly Trend ───────────────────────────────

row1_left, row1_right = st.columns([1, 1])

with row1_left:
    st.subheader("Spend by Category")
    cat_summary = (
        df_expenses
        .groupby("category")["amount"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount": "spent"})
        .sort_values("spent", ascending=False)
    )
    if not cat_summary.empty:
        fig_cat = px.bar(
            cat_summary,
            x="spent", y="category",
            orientation="h",
            text=cat_summary["spent"].apply(lambda x: f"${x:,.0f}"),
            labels={"spent": "SGD", "category": ""},
            color="spent",
            color_continuous_scale="Reds_r",
        )
        fig_cat.update_traces(textposition="outside")
        fig_cat.update_layout(
            coloraxis_showscale=False,
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=0, r=60, t=20, b=0),
            height=380,
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No expense data for selected filters.")

with row1_right:
    st.subheader("Monthly Spending Trend")
    monthly = (
        df_expenses
        .groupby(["month", "category"])["amount"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount": "spent"})
    )
    if not monthly.empty:
        fig_trend = px.bar(
            monthly,
            x="month", y="spent",
            color="category",
            labels={"spent": "SGD", "month": "Month", "category": "Category"},
            barmode="stack",
        )
        fig_trend.update_layout(
            margin=dict(l=0, r=0, t=20, b=0),
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No data for selected filters.")

# ── Row 2: Category Donut  +  Top Merchants ──────────────────────────────────

row2_left, row2_right = st.columns([1, 1])

with row2_left:
    st.subheader("Category Split")
    if not cat_summary.empty:
        fig_pie = px.pie(
            cat_summary,
            values="spent",
            names="category",
            hole=0.45,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=20, b=0),
            height=340,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with row2_right:
    st.subheader("Top 10 Merchants by Spend")
    top_merch = (
        df_expenses
        .groupby(["merchant", "category"])["amount"]
        .agg(total="sum", count="count")
        .reset_index()
        .assign(total=lambda x: x["total"].abs())
        .sort_values("total", ascending=False)
        .head(10)
    )
    if not top_merch.empty:
        fig_merch = px.bar(
            top_merch,
            x="total", y="merchant",
            orientation="h",
            color="category",
            text=top_merch["total"].apply(lambda x: f"${x:,.0f}"),
            labels={"total": "SGD", "merchant": ""},
            hover_data={"count": True},
        )
        fig_merch.update_traces(textposition="outside")
        fig_merch.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=0, r=60, t=20, b=0),
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=-0.4),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_merch, use_container_width=True)

# ── Row 3: Uncategorised review (actionable table) ───────────────────────────

st.markdown("---")
st.subheader("🔎 Uncategorised Transactions — Review & Fix")

df_uncat = df_all[df_all["category"] == "Uncategorised"].copy()
uncat_count = len(df_uncat)
uncat_total = df_uncat["amount"].sum()

if uncat_count == 0:
    st.success("✅ No uncategorised transactions.")
else:
    st.warning(
        f"**{uncat_count} uncategorised transactions** totalling "
        f"SGD {uncat_total:,.2f}. "
        "Add these merchants or codes to `MERCHANT_CATEGORY_MAP` in `etl.py`, "
        "then re-run with `--reset`."
    )
    # Aggregate by description to make the fix list compact
    uncat_summary = (
        df_uncat
        .groupby(["transaction_code", "description"])
        .agg(
            occurrences=("amount", "count"),
            total_amount=("amount", "sum"),
        )
        .reset_index()
        .sort_values("total_amount")
    )
    uncat_summary["transaction_code"] = uncat_summary["transaction_code"].fillna("(none)")
    st.dataframe(
        uncat_summary.rename(columns={
            "transaction_code": "Code",
            "description":      "Description",
            "occurrences":      "Count",
            "total_amount":     "Total (SGD)",
        }),
        use_container_width=True,
        height=280,
    )

# ── Row 4: Transaction log (full searchable table) ───────────────────────────

st.markdown("---")
with st.expander("📋 Full Transaction Log", expanded=False):
    search = st.text_input("Search description or merchant", "")
    df_log = df.copy()
    if search:
        mask = (
            df_log["description"].str.contains(search, case=False, na=False) |
            df_log["merchant"].str.contains(search, case=False, na=False)
        )
        df_log = df_log[mask]

    st.dataframe(
        df_log[[
            "transaction_date", "amount", "transaction_code",
            "merchant", "category", "description"
        ]].rename(columns={
            "transaction_date": "Date",
            "amount":           "Amount (SGD)",
            "transaction_code": "Code",
            "merchant":         "Merchant",
            "category":         "Category",
            "description":      "Description",
        }),
        use_container_width=True,
        height=400,
    )
    st.caption(f"{len(df_log):,} rows shown")
