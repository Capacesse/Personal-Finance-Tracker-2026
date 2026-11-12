"""
dashboard/filters.py
====================
Sidebar UI only. Returns a FilterState defined in dashboard.data.
There is deliberately no second FilterState dataclass here.
"""

import sqlite3
import pandas as pd
import streamlit as st
from dataclasses import dataclass

from dashboard.data import FilterState
from core.loader import build_code_cache, initialise_schema, load_transactions
from core.transformer import extract, transform


def _ingest_upload(uploaded_file, db_path: str) -> tuple[int, int]:
    """
    Run the ETL pipeline on an uploaded CSV and load it into the database.
    Returns (inserted, skipped). Raises on any failure, leaving the database
    unchanged.

    The upload is read straight from memory. Nothing is written to disk.
    """
    clean_df = transform(extract(uploaded_file))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        initialise_schema(conn)
        code_cache = build_code_cache(conn)
        inserted, skipped = load_transactions(conn, clean_df, code_cache)
        conn.commit()
        return inserted, skipped
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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

        # Result of the previous upload. Stored in session state because the
        # page reruns after a successful load, which would wipe a message
        # shown directly.
        flash = st.session_state.pop("upload_result", None)
        if flash:
            st.success(flash)

        uploaded_file = st.file_uploader(
            "Upload Bank Statement", 
            type=["csv"], 
            help="Drag and drop your latest CSV export here."
        )
        st.caption(
            "Uploads are stored in this app's database. "
            "On a public demo, do not upload real statements."
        )

        if uploaded_file is not None:
            if st.button("Process New Transactions", type="primary", width="stretch"):
                outcome = None
                with st.spinner("Processing pipeline..."):
                    try:
                        outcome = _ingest_upload(uploaded_file, db_path)
                    except ValueError as e:
                        # Raised by transform() for unsupported or incomplete files
                        st.error(f"Error parsing the CSV file: {e}")
                    except Exception as e:
                        st.error(f"Database error during load: {e}")

                if outcome is not None:
                    inserted, skipped = outcome
                    st.session_state["upload_result"] = (
                        f"✅ Processed successfully! {inserted} new transactions "
                        f"added. ({skipped} duplicates skipped)."
                    )
                    # Clear the cache so the dashboard reads the new rows, then
                    # redraw. Only on success: an error message must stay visible.
                    st.cache_data.clear()
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