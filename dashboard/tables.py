"""
dashboard/tables.py
===================
Interactive data tables for the dashboard.
Receives pre-filtered DataFrames — does no filtering itself.
"""

import pandas as pd
import streamlit as st

def render_uncategorised_review(df_all: pd.DataFrame, uncat_df: pd.DataFrame = None):
    """
    Renders the warning and summary table for uncategorised transactions.
    """
    st.subheader("🔎 Uncategorised Transactions")
    
    raw_uncat = df_all[df_all["category"] == "Uncategorised"].copy()
    
    if raw_uncat.empty:
        st.success("✅ All transactions are categorised.")
        return

    total_amount = raw_uncat["amount"].sum()
    
    st.warning(
        f"{len(raw_uncat)} uncategorised transactions totalling SGD {total_amount:,.2f}. "
        "Add keywords to `core/categoriser.py` → `MERCHANT_CATEGORY_MAP` and re-run `python etl.py --reset`."
    )

    # Group by merchant to make it easy to find the biggest culprits
    summary = (
        raw_uncat.groupby("merchant")
        .agg(
            Count=("amount", "count"),
            Total_SGD=("amount", "sum")
        )
        .reset_index()
        .sort_values("Total_SGD", ascending=True) 
    )

    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_transaction_log(df_full: pd.DataFrame):
    """
    Renders a collapsible, searchable table of all loaded transactions.
    """
    with st.expander("📋 Full Transaction Log", expanded=False):
        search = st.text_input("Search", "", key="txn_search")
        df_log = df_full.copy()
        
        # Apply the text search filter if the user typed something
        if search:
            mask = (
                df_log["description"].str.contains(search, case=False, na=False) |
                df_log["merchant"].str.contains(search, case=False, na=False)
            )
            df_log = df_log[mask]
            
        # Select and format columns for display
        display_cols = ["transaction_date", "amount", "transaction_code", "merchant", "category", "description"]
        existing_cols = [c for c in display_cols if c in df_log.columns]
        
        st.dataframe(
            df_log[existing_cols].rename(columns={
                "transaction_date": "Date",
                "amount":           "Amount (SGD)",
                "transaction_code": "Code",
                "merchant":         "Merchant",
                "category":         "Category",
                "description":      "Description",
            }),
            use_container_width=True,
            height=380,
            hide_index=True
        )
        st.caption(f"{len(df_log):,} rows")