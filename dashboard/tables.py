"""
dashboard/tables.py
===================
Interactive data tables for the dashboard.
Receives pre-filtered DataFrames.
Does no filtering itself.
"""

import pandas as pd
import streamlit as st

_LOG_COLS = {
    "transaction_date": "Date",
    "amount":           "Amount (SGD)",
    "transaction_code": "Code",
    "merchant":         "Merchant",
    "category":         "Category",
    "description":      "Description",
}

def render_transaction_log(df: pd.DataFrame) -> None:
    """
    A collapsible, searchable and sortable table of all transactions.
    """
    with st.expander("📋 Full Transaction Log", expanded=False):
        search = st.text_input(
            "Search by merchant or description",
            key="txn_log_search",
            placeholder="e.g. Grab, Spotify…",
        )
        display = df.sort_values("transaction_date", ascending=False).copy()
        if search:
            mask = (
                display["merchant"].str.contains(search, case=False, na=False)
                | display["description"].str.contains(search, case=False, na=False)
            )
            display = display[mask]
 
        st.dataframe(
            display.assign(
                transaction_date=display['transaction_date'].dt.strftime('%Y-%m-%d')
                if hasattr(display['transaction_date'], 'dt')
                else display['transaction_date'].astype(str).str[:10]
            )[list(_LOG_COLS.keys())].rename(columns=_LOG_COLS),
            use_container_width=True,
            hide_index=True,
            height=420,
        )
        st.caption(f"{len(display):,} rows shown")

def render_uncategorised_review(df_all: pd.DataFrame) -> None:
    """
    Actionable grouped table of uncategorised transactions.
    """
    st.subheader("🔎 Uncategorised Transactions")
 
    raw_uncat = df_all[df_all["category"] == "Uncategorised"].copy()
 
    if raw_uncat.empty:
        st.success("✅ All transactions are categorised.")
        return
 
    total_amount = raw_uncat["amount"].sum()
    st.warning(
        f"**{len(raw_uncat)} uncategorised transactions** totalling "
        f"SGD {total_amount:,.2f}.  "
        "Add keywords to `core/categoriser.py → MERCHANT_CATEGORY_MAP` "
        "and re-run `python etl.py --reset`."
    )
 
    summary = (
        raw_uncat
        .groupby("merchant")
        .agg(Count=("amount", "count"), Total_SGD=("amount", "sum"))
        .reset_index()
        .sort_values("Total_SGD", ascending=True)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)
