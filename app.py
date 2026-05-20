"""
Personal Finance Engine — Shared Web App
=========================================
Upload your bank CSV → instant interactive dashboard.
No data is saved to disk; everything lives in your browser session.

Run with:
    streamlit run app.py
"""

import logging
import sqlite3
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from core.categoriser import MERCHANT_CATEGORY_MAP
from core.loader import (
    build_code_cache,
    initialise_schema,
    load_transactions,
)
from core.transformer import extract, transform

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Personal Finance Engine",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────

CODES_TXT = Path("DBS_Transaction_Codes___Descriptions.txt")

EXPENSE_CATEGORIES = [
    "Food & Drink", "Transport", "Subscriptions", "Health & Wellness",
    "Shopping", "Utilities", "Entertainment", "Banking Fees",
    "Investments", "Education", "Insurance", "Donations",
    "Loans & Mortgage", "Government & CPF", "Transfers", "Uncategorised",
]

# ── Session-state helpers ─────────────────────────────────────────────────────

def _state(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def _reset_session():
    for key in ["conn", "df", "filename"]:
        st.session_state.pop(key, None)

# ── In-memory database ────────────────────────────────────────────────────────

@contextmanager
def _in_memory_conn():
    """
    Yields a fresh in-memory SQLite connection with FK enforcement.
    Used only during the initial load; the resulting data is immediately
    queried into a DataFrame and the connection is closed.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _seed_codes(conn: sqlite3.Connection) -> None:
    """Seed TransactionCodes from the reference txt if available."""
    if not CODES_TXT.exists():
        log.warning("Codes file not found — code-based categorisation limited.")
        return
    try:
        from transaction_codes_loader import parse_codes_file, seed_transaction_codes
        codes = parse_codes_file(str(CODES_TXT))
        seed_transaction_codes(conn, codes)
    except ImportError:
        log.warning("transaction_codes_loader not found — skipping.")


@st.cache_data(show_spinner="Processing your CSV…")
def run_etl(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Full ETL run returning a denormalised DataFrame.
    Cached by (file_bytes, filename) so re-uploads of the same file
    don't reprocess; uploading a new file busts the cache automatically.
    """
    with _in_memory_conn() as conn:
        initialise_schema(conn)
        _seed_codes(conn)
        code_cache = build_code_cache(conn)

        raw_df   = extract(BytesIO(file_bytes))
        clean_df = transform(raw_df)
        load_transactions(conn, clean_df, code_cache)

        df = pd.read_sql_query(
            """
            SELECT t.transaction_date,
                   t.amount,
                   t.description,
                   t.transaction_code,
                   m.name  AS merchant,
                   c.name  AS category
            FROM   Transactions t
            JOIN   Merchants    m  ON t.merchant_id  = m.merchant_id
            JOIN   Categories   c  ON m.category_id  = c.category_id
            ORDER  BY t.transaction_date
            """,
            conn,
            parse_dates=["transaction_date"],
        )

    df["year_month"] = df["transaction_date"].dt.strftime("%Y-%m")
    df["is_expense"] = df["amount"] < 0
    return df

# ── Upload screen ─────────────────────────────────────────────────────────────

def render_upload_screen():
    st.title("💳 Personal Finance Engine")
    st.markdown("Upload your DBS/POSB bank export CSV to get started.")

    col_upload, col_info = st.columns([1, 1], gap="large")

    with col_upload:
        uploaded = st.file_uploader(
            "Bank export CSV",
            type=["csv"],
            help="Download from DBS iBanking → Accounts → Transaction History → CSV",
        )
        if uploaded:
            st.session_state["filename"]    = uploaded.name
            st.session_state["file_bytes"]  = uploaded.read()
            st.rerun()

    with col_info:
        st.markdown("**Expected CSV columns:**")
        st.code(
            "Transaction Date\n"
            "Description\n"
            "Withdrawal Amount\n"
            "Deposit Amount\n"
            "Transaction Code  ← optional but improves accuracy",
            language="text",
        )
        st.info(
            "Your data never leaves your device. "
            "Everything is processed in memory and discarded when you close the tab."
        )

# ── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard(df: pd.DataFrame, filename: str):

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"📄 **{filename}**")
        if st.button("⬆️  Upload new file", use_container_width=True):
            _reset_session()
            st.rerun()
        st.markdown("---")

        # Month selector — drives everything
        all_months = sorted(df["year_month"].unique())
        st.markdown("#### Month")
        selected_month = st.select_slider(
            "Select month",
            options=all_months,
            value=all_months[-1],
            label_visibility="collapsed",
        )

        st.markdown("#### View")
        show_transfers = st.checkbox("Show Transfers", value=False,
            help="Transfers are often peer-to-peer payments that inflate spend totals")
        show_income    = st.checkbox("Show Income & Credits", value=False)

        st.markdown("---")
        code_cov = (
            df["transaction_code"].notna().sum() / max(len(df), 1) * 100
        )
        st.metric("🔖 Code Coverage", f"{code_cov:.0f}%")
        st.caption(f"{len(df):,} total transactions loaded")

    # ── Filter to selected month ───────────────────────────────────────────────
    df_month = df[df["year_month"] == selected_month].copy()
    df_prev_month = None
    prev_idx = all_months.index(selected_month) - 1
    if prev_idx >= 0:
        df_prev_month = df[df["year_month"] == all_months[prev_idx]].copy()

    # Apply toggles
    exclude_cats = []
    if not show_transfers:
        exclude_cats.append("Transfers")
    if not show_income:
        exclude_cats += ["Income"]

    df_view  = df_month[~df_month["category"].isin(exclude_cats)]
    df_exp   = df_view[df_view["amount"] < 0].copy()

    # ── Header ────────────────────────────────────────────────────────────────
    st.title("💳 Personal Finance Engine")

    # Month navigation hint
    m_col, _ = st.columns([3, 1])
    with m_col:
        st.markdown(f"### {_fmt_month(selected_month)}")

    st.markdown("---")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_spent  = df_exp["amount"].sum()               # negative
    total_income = df_month[df_month["amount"] > 0]["amount"].sum()
    net_flow     = total_income + total_spent

    # Month-on-month deltas
    delta_spent = delta_income = delta_net = None
    if df_prev_month is not None:
        prev_exp     = df_prev_month[
            ~df_prev_month["category"].isin(exclude_cats) &
            (df_prev_month["amount"] < 0)
        ]["amount"].sum()
        prev_income  = df_prev_month[df_prev_month["amount"] > 0]["amount"].sum()
        delta_spent  = abs(total_spent)  - abs(prev_exp)
        delta_income = total_income - prev_income
        delta_net    = net_flow - (prev_income + prev_exp)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "💸 Spent this month",
        f"SGD {abs(total_spent):,.2f}",
        delta=f"SGD {delta_spent:+,.2f} vs last month" if delta_spent is not None else None,
        delta_color="inverse",   # red = spent more (bad), green = spent less (good)
    )
    k2.metric(
        "💰 Income this month",
        f"SGD {total_income:,.2f}",
        delta=f"SGD {delta_income:+,.2f} vs last month" if delta_income is not None else None,
    )
    k3.metric(
        "📊 Net Flow",
        f"SGD {net_flow:,.2f}",
        delta=f"SGD {delta_net:+,.2f} vs last month" if delta_net is not None else None,
    )
    k4.metric(
        "🧾 Transactions",
        f"{len(df_exp):,}",
    )

    st.markdown("---")

    # ── Row 1: Spend by Category  +  Day-by-day spend ────────────────────────
    row1_l, row1_r = st.columns(2)

    with row1_l:
        st.subheader("Spend by Category")
        cat_df = (
            df_exp.groupby("category")["amount"]
            .sum().abs()
            .reset_index()
            .rename(columns={"amount": "spent"})
            .sort_values("spent", ascending=True)
        )
        if not cat_df.empty:
            fig = px.bar(
                cat_df, x="spent", y="category",
                orientation="h",
                text=cat_df["spent"].apply(lambda v: f"${v:,.0f}"),
                labels={"spent": "SGD", "category": ""},
                color="spent",
                color_continuous_scale="Reds_r",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=0, r=60, t=10, b=0),
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data for this month.")

    with row1_r:
        st.subheader("Daily Spending")
        daily = (
            df_exp.groupby(
                [df_exp["transaction_date"].dt.day.rename("day"), "category"]
            )["amount"].sum().abs().reset_index()
            .rename(columns={"amount": "spent"})
        )
        if not daily.empty:
            fig = px.bar(
                daily, x="day", y="spent",
                color="category", barmode="stack",
                labels={"spent": "SGD", "day": "Day of Month", "category": "Category"},
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=-0.45),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Month-on-month comparison  +  Top merchants ───────────────────
    st.markdown("---")
    row2_l, row2_r = st.columns(2)

    with row2_l:
        st.subheader("Month-on-Month Comparison")
        monthly_cat = (
            df[~df["category"].isin(exclude_cats) & (df["amount"] < 0)]
            .groupby(["year_month", "category"])["amount"]
            .sum().abs().reset_index()
            .rename(columns={"amount": "spent"})
        )
        if not monthly_cat.empty:
            # Highlight the selected month with an annotation
            fig = px.bar(
                monthly_cat, x="year_month", y="spent",
                color="category", barmode="stack",
                labels={"spent": "SGD", "year_month": "Month", "category": "Category"},
            )
            # Vertical line marking selected month
            fig.add_vline(
                x=selected_month,
                line_dash="dash", line_color="white", line_width=2,
                annotation_text="← selected",
                annotation_position="top right",
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=-0.45),
            )
            st.plotly_chart(fig, use_container_width=True)

    with row2_r:
        st.subheader(f"Top Merchants — {_fmt_month(selected_month)}")
        top_m = (
            df_exp.groupby(["merchant", "category"])["amount"]
            .agg(total="sum", count="count").reset_index()
            .assign(total=lambda x: x["total"].abs())
            .sort_values("total", ascending=True)
            .tail(12)
        )
        if not top_m.empty:
            fig = px.bar(
                top_m, x="total", y="merchant",
                orientation="h",
                color="category",
                text=top_m["total"].apply(lambda v: f"${v:,.0f}"),
                labels={"total": "SGD", "merchant": "", "category": "Category"},
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                margin=dict(l=0, r=70, t=10, b=0),
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=-0.45),
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Category spend trend (selected categories over time) ───────────
    st.markdown("---")
    st.subheader("Category Trends Over Time")

    available_cats = sorted(
        df[~df["category"].isin(["Income", "Transfers"])]["category"].unique()
    )
    selected_cats = st.multiselect(
        "Compare categories",
        options=available_cats,
        default=available_cats[:5] if len(available_cats) >= 5 else available_cats,
        label_visibility="collapsed",
    )
    trend_df = (
        df[df["category"].isin(selected_cats) & (df["amount"] < 0)]
        .groupby(["year_month", "category"])["amount"]
        .sum().abs().reset_index()
        .rename(columns={"amount": "spent"})
    )
    if not trend_df.empty:
        fig = px.bar(
            trend_df, x="year_month", y="spent",
            color="category", barmode="group",
            labels={"spent": "SGD", "year_month": "Month", "category": "Category"},
        )
        fig.add_vline(
            x=selected_month, line_dash="dash",
            line_color="white", line_width=2,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
            legend=dict(orientation="h", yanchor="bottom", y=-0.35),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Uncategorised review ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔎 Uncategorised Transactions")

    df_uncat = df_month[df_month["category"] == "Uncategorised"]
    if df_uncat.empty:
        st.success("✅ All transactions this month are categorised.")
    else:
        st.warning(
            f"**{len(df_uncat)} uncategorised transactions** "
            f"totalling SGD {df_uncat['amount'].sum():,.2f} this month."
        )
        uncat_summary = (
            df_uncat.groupby(["transaction_code", "description"])
            .agg(count=("amount", "count"), total=("amount", "sum"))
            .reset_index()
            .sort_values("total")
        )
        uncat_summary["transaction_code"] = (
            uncat_summary["transaction_code"].fillna("(none)")
        )
        st.dataframe(
            uncat_summary.rename(columns={
                "transaction_code": "Code",
                "description": "Description",
                "count": "Count",
                "total": "Total (SGD)",
            }),
            use_container_width=True,
            height=240,
        )

    # ── Full transaction log ──────────────────────────────────────────────────
    with st.expander("📋 Full Transaction Log — this month", expanded=False):
        search = st.text_input("Search", "", key="txn_search")
        df_log = df_month.copy()
        if search:
            mask = (
                df_log["description"].str.contains(search, case=False, na=False) |
                df_log["merchant"].str.contains(search, case=False, na=False)
            )
            df_log = df_log[mask]
        st.dataframe(
            df_log[[
                "transaction_date", "amount", "transaction_code",
                "merchant", "category", "description",
            ]].rename(columns={
                "transaction_date": "Date",
                "amount":           "Amount (SGD)",
                "transaction_code": "Code",
                "merchant":         "Merchant",
                "category":         "Category",
                "description":      "Description",
            }),
            use_container_width=True,
            height=380,
        )
        st.caption(f"{len(df_log):,} rows")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_month(ym: str) -> str:
    """'2025-06' → 'June 2025'"""
    try:
        return pd.to_datetime(ym + "-01").strftime("%B %Y")
    except Exception:
        return ym

# ── Router ────────────────────────────────────────────────────────────────────

def main():
    if "file_bytes" not in st.session_state:
        render_upload_screen()
        return

    file_bytes = st.session_state["file_bytes"]
    filename   = st.session_state.get("filename", "upload.csv")

    with st.spinner("Processing your data…"):
        try:
            df = run_etl(file_bytes, filename)
        except Exception as e:
            st.error(f"Failed to process CSV: {e}")
            st.info("Make sure your CSV has the expected column headers.")
            if st.button("Try a different file"):
                _reset_session()
                st.rerun()
            return

    render_dashboard(df, filename)


if __name__ == "__main__":
    main()
