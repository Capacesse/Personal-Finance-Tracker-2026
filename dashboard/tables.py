"""
dashboard/tables.py
===================
Interactive data tables for the dashboard.
Receives pre-filtered DataFrames.
Does no filtering itself.
"""

import pandas as pd
import streamlit as st
from dashboard.data import update_merchant_category

_LOG_COLS = {
    "transaction_date": "Date",
    "amount":           "Amount (SGD)",
    "transaction_code": "Code",
    "merchant":         "Merchant",
    "category":         "Category",
    "description":      "Description",
}

@st.cache_data(show_spinner=False)
def _convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """Caches the CSV conversion to prevent re-computing on every UI interaction."""
    return df.to_csv(index=False).encode('utf-8')


def render_transaction_log(df: pd.DataFrame, valid_categories: list[str], db_path: str) -> None:
    """
    A searchable, sortable and interactive table of all transactions. Includes export.
    """
    with st.expander("📋 Full Transaction Log", expanded=False):
        
        col_search, col_export = st.columns([3, 1])
        with col_search:
            search = st.text_input(
                "Search by merchant or description",
                key="txn_log_search",
                placeholder="e.g. Grab, Spotify…",
                label_visibility="collapsed"
            )
            
        display = df.sort_values("transaction_date", ascending=False).copy()
        if search:
            mask = (
                display["merchant"].str.contains(search, case=False, na=False)
                | display["description"].str.contains(search, case=False, na=False)
            )
            display = display[mask]

        formatted_display = display.assign(
            transaction_date=display['transaction_date'].dt.strftime('%Y-%m-%d')
            if hasattr(display['transaction_date'], 'dt')
            else display['transaction_date'].astype(str).str[:10]
        )[list(_LOG_COLS.keys())].rename(columns=_LOG_COLS)

        with col_export:
            csv_data = _convert_df_to_csv(formatted_display)
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name="filtered_transactions.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Inline editor
        edited_df = st.data_editor(
            formatted_display,
            use_container_width=True,
            hide_index=True,
            height=420,
            disabled=["Date", "Amount (SGD)", "Code", "Merchant", "Description"], # Lock disabled columns
            column_config={
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=valid_categories,
                    required=True
                )
            },
            key="txn_log_editor"
        )
        
        # Compare  original dataframe with edited one to find rows that changed
        changes_mask = edited_df["Category"] != formatted_display["Category"]
        changes_df = edited_df[changes_mask]

        if not changes_df.empty:
            st.warning(f"You have re-categorised {len(changes_df)} transaction(s).")
            if st.button("Save Category Updates", type="primary"):
                # Apply changes to the database
                for _, row in changes_df.iterrows():
                    update_merchant_category(db_path, row["Merchant"], row["Category"])
                
                st.success("✅ Categories successfully updated in the database.")
                st.rerun()
        else:
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
