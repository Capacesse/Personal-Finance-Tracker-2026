"""
core/transformer.py
===================
Extract and Transform steps.
Accepts a file path (str) or any file-like object (BytesIO from Streamlit).
"""

import hashlib
import logging
import re
from io import BytesIO
from typing import Union

import pandas as pd

log = logging.getLogger(__name__)

# Merchant name cleaning
_NOISE_TOKENS = [
    " SINGAPORE", " PTE LTD", " SDN BHD", " LTD", " (S)",
    " PVT", " PRIVATE", " HOLDINGS", " INTERNATIONAL", " GROUP",
]

# Strips trailing reference codes: GRAB*00123456, NETS#REF991, etc.
_REF_SUFFIX   = re.compile(r'[*#]\S*')
# Strips leading reference codes that DBS sometimes prepends: "00123 MERCHANT"
_REF_PREFIX   = re.compile(r'^\d{5,}\s+')
# Collapse runs of whitespace
_WHITESPACE   = re.compile(r'\s{2,}')

# Merchant name normalisation map — applied AFTER basic cleaning.
# Maps normalised substrings → canonical display names.
# Extend this as you find variants in your own exports.
MERCHANT_ALIASES: dict[str, str] = {
    "GRAB FOOD":    "GRAB FOOD",
    "GRAB*FOOD":    "GRAB FOOD",
    "GRABFOOD":     "GRAB FOOD",
    "GRAB CAR":     "GRAB TRANSPORT",
    "GRAB TAXI":    "GRAB TRANSPORT",
    "GRAB RIDE":    "GRAB TRANSPORT",
    "MCDONALDS":    "MCDONALD'S",
    "MCDONALD S":   "MCDONALD'S",
    "COMFORTDELGRO":"COMFORT DELGRO",
    "COMFORT TAXI": "COMFORT DELGRO",
    "CDG TAXI":     "COMFORT DELGRO",
    "SP SERVICES":  "SINGAPORE POWER",
    "SP GROUP":     "SINGAPORE POWER",
    "NTUC FAIRPRICE":"FAIRPRICE",
    "FAIRPRICE XTRA":"FAIRPRICE",
    "FAIRPRICE FINEST":"FAIRPRICE",
    "APPLE COM BILL":"APPLE.COM",
    "APPLE.COM/BILL":"APPLE.COM",
}


def extract(source: Union[str, BytesIO]) -> pd.DataFrame:
    """
    Read the raw bank CSV.
    source = file path string or BytesIO / Streamlit UploadedFile.
    """
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    log.info("Loaded %d raw rows.", len(df))
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalise the raw DataFrame.

    Output columns:
        transaction_date   ISO-8601 'YYYY-MM-DD'
        year_month         'YYYY-MM' for grouping
        amount             signed float (negative = expense)
        description        normalised uppercase string (original, for audit)
        transaction_code   normalised uppercase code or None
        merchant_name      deduplicated canonical merchant name
        transaction_hash   SHA-256 of (date|amount|description) — dedup key
    """
    log.info("Transforming %d rows…", len(df))

    # ── Rename ────────────────────────────────────────────────────────────────
    rename_map = {
        "Transaction Date":  "transaction_date",
        "Description":       "description",
        "Withdrawal Amount": "withdrawal",
        "Deposit Amount":    "deposit",
        "Transaction Code":  "transaction_code",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # ── Transaction code ──────────────────────────────────────────────────────
    if "transaction_code" not in df.columns:
        df["transaction_code"] = None
    else:
        df["transaction_code"] = (
            df["transaction_code"].str.strip().str.upper().replace("", None)
        )

    # ── Dates ─────────────────────────────────────────────────────────────────
    # Parse to datetime objects first (handling Day/Month/Year formats)
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], 
        format="mixed", 
        dayfirst=True, 
        errors="coerce"
    )

    bad_dates = df["transaction_date"].isna().sum()
    if bad_dates:
        log.warning("%d row(s) had unparseable dates and will be dropped.", bad_dates)
    df = df.dropna(subset=["transaction_date"])

    df["year_month"] = df["transaction_date"].dt.strftime("%Y-%m")
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")

    # ── Amounts ───────────────────────────────────────────────────────────────
    df["withdrawal"] = pd.to_numeric(df["withdrawal"], errors="coerce").fillna(0.0)
    df["deposit"]    = pd.to_numeric(df["deposit"],    errors="coerce").fillna(0.0)
    df["amount"]     = df["deposit"] - df["withdrawal"]

    # ── Descriptions ─────────────────────────────────────────────────────────
    df["description"] = (
        df["description"].str.strip().str.upper().replace("", "UNKNOWN PAYEE")
    )

    # ── Drop zero-amount rows ─────────────────────────────────────────────────
    before = len(df)
    df     = df[df["amount"] != 0].copy()
    log.info("Dropped %d zero-amount rows. %d remain.", before - len(df), len(df))

    # ── Merchant names (after zeroes dropped) ────────────────────────────────
    df["merchant_name"] = df["description"].apply(_normalise_merchant)

    # ── Deduplication hash ────────────────────────────────────────────────────
    # Hash is computed on the raw description (not the cleaned merchant name)
    # so it's stable even if normalisation logic changes in future.
    df["transaction_hash"] = df.apply(
        lambda r: _compute_hash(
            r["transaction_date"], r["amount"], r["description"]
        ),
        axis=1,
    )

    # Warn if the CSV itself contains duplicates (same hash twice)
    dup_count = df["transaction_hash"].duplicated().sum()
    if dup_count:
        log.warning(
            "%d duplicate rows detected within this CSV and will be dropped.",
            dup_count,
        )
        df = df.drop_duplicates(subset="transaction_hash")

    return df[[
        "transaction_date", "year_month", "amount",
        "description", "transaction_code", "merchant_name", "transaction_hash",
    ]]


def _compute_hash(date: str, amount: float, description: str) -> str:
    """
    Deterministic SHA-256 hash of the three fields that uniquely identify
    a real bank transaction.  Using SHA-256 (truncated to 16 hex chars)
    gives 64-bit collision resistance — more than sufficient for personal
    transaction volumes.
    """
    raw = f"{date}|{amount:.2f}|{description}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _normalise_merchant(description: str) -> str:
    """
    Produce a clean, canonical merchant name from a raw bank description.
    Includes aggressive stripping for DBS terminal noise.
    """
    # Force uppercase immediately for consistent regex matching
    name = description.upper()

    # 1. Strip the standard DBS card terminal suffix (e.g., " SI SGP 02JAN 5264...")
    name = re.sub(r'\s+(SI )?SGP\s+\d{2}[A-Z]{3}.*$', '', name)

    # 2. Strip Grab/FoodPanda/Google hex codes and prefixes
    name = re.sub(r'^GRAB\*\s*(GPC-)?[A-F0-9]+\s*', 'GRAB ', name)
    name = name.replace('FP*FOOD PANDA', 'FOOD PANDA')
    name = name.replace('GOOGLE*YOUTUBEPREMIUM', 'YOUTUBE PREMIUM')
    name = re.sub(r'\s+SG\s*$', '', name)

    # 3. Existing logic: Leading digits & Trailing reference codes
    name = _REF_PREFIX.sub("", name)
    name = _REF_SUFFIX.sub("", name)

    # 4. Existing logic: Noise tokens
    for token in _NOISE_TOKENS:
        name = name.replace(token, "")

    # 5. Existing logic: Whitespace + length cap
    name = _WHITESPACE.sub(" ", name).strip()[:45]

    # 6. Existing logic: Alias resolution
    for alias, canonical in MERCHANT_ALIASES.items():
        if alias in name:
            return canonical

    return name
