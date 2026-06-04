"""
dashboard/filters.py
====================
Sidebar UI only. Returns a FilterState defined in dashboard.data.
There is deliberately no second FilterState dataclass here.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
from dataclasses import dataclass

from dashboard.data import FilterState
from core.loader import build_code_cache, initialise_schema, load_transactions
from core.transformer import extract, transform


def render_sidebar(df_all, db_path) -> FilterState:
    """
    Renders the sidebar interface and returns the current FilterState.

    > A file uploader to ingest new bank CSVs, trigger the ETL pipeline, and update the database immediately.
    > Collects user filter preferences (months, categories, transaction types) and packages them into a FilterState object.

    Note: The actual application of these filters to the DataFrames is 
    handled entirely within dashboard/data.py, preserving separation 
    of UI and business logic.
    """
    with st.sidebar:
        # ── 1. The In-App File Uploader ──
        st.header("📥 Update Data")
        uploaded_file = st.file_uploader(
            "Upload Bank Statement", 
            type=["csv"], 
            help="Drag and drop your latest CSV export here."
        )

        if uploaded_file is not None:
            if st.button("Process New Transactions", type="primary", use_container_width=True):
                with st.spinner("Processing pipeline..."):
                    # Temporarily save the in-memory upload to disk
                    temp_path = "temp_upload.csv"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                 # Run ETL pipeline on the uploaded file
                try:
                    raw_df = extract(temp_path)
                    clean_df = transform(raw_df)

                    # Use sqlite3 to load into Database
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA foreign_keys = ON")

                    try:
                        # Check if tables exist
                        initialise_schema(conn)

                        
                        code_cache = build_code_cache(conn)
                        inserted, skipped = load_transactions(conn, clean_df, code_cache)

                        conn.commit()
                        st.success(f"✅ Processed successfully! {inserted} new transactions added. ({skipped} duplicates skipped).")
                    except Exception as e:
                         conn.rollback()
                         st.error(f"Database error during load: {e}")
                    finally:
                         conn.close()

                except Exception as e:
                    st.error(f"Error parsing the CSV file: {e}")
                                        
                    # Clean up the temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # Clear the cache so the dashboard reads the new database rows
                    st.cache_data.clear()
                    st.success("✅ Database updated successfully.")
                    st.rerun()

        st.markdown("---")
        st.header("🔎 Filters")

    # ── Month range ───────────────────────────────────────────────────────────
    all_months = sorted(df_all["month"].unique())
    selected_months = st.sidebar.multiselect(
        "Month(s)",
        options=all_months,
        default=all_months,
    )

    # ── Category filter ───────────────────────────────────────────────────────
    all_categories = sorted(df_all["category"].dropna().unique().tolist())
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
        df_all["transaction_code"].notna().sum() / max(len(df_all), 1) * 100
    )
    st.sidebar.metric("🔖 Code Coverage", f"{code_cov:.0f}%")
    st.sidebar.caption(f"`{db_path}`  ·  {len(df_all):,} total transactions")

    return FilterState(
        selected_months=selected_months,
        selected_categories=selected_categories,
        show_transfers=show_transfers,
        show_income=show_income,
    )