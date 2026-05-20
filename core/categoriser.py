"""
core/categoriser.py
===================
All categorisation constants and the 5-tier confidence system.
Imported by etl.py (persistent mode) and app.py (session mode).
"""

# ── Generic codes ─────────────────────────────────────────────────────────────
# Valid DBS codes that carry too little signal to override a keyword match.
# All verified against the DBS reference file.
GENERIC_CODES: frozenset[str] = frozenset({
    "MST",   # Debit Card Transaction
    "POS",   # Point-of-Sale Transaction
    "NETS",  # Point-of-Sale Transaction (NETS terminal)
    "BAT",   # Debit Card Transaction (variant)
    "DEP",   # Deposit (generic inward)
    "WDL",   # Withdrawal (generic outbound)
    "AWL",   # Cash Withdrawal  ← also in CASH_CODES below
    "CCCC",  # NETS Proceeds
})

# ── Bidirectional codes ───────────────────────────────────────────────────────
# These codes appear on both inbound (Income) and outbound (PayNow & FAST)
# transactions.  The sign of `amount` is the tiebreaker.
BIDIRECTIONAL_CODES: frozenset[str] = frozenset({
    "ICT",   # Instant Credit Transfer (FAST / PayNow)
    "GR",    # GIRO
    "GRP",   # GIRO Payroll
    "GRS",   # GIRO Payroll (variant)
    "GRC",   # GIRO Credit
    "GRB",   # GIRO Bulk
    "IBG",   # Interbank GIRO
    "DCR",   # Instant Direct Credit
    "DCRT",  # Instant Direct Credit Transfer
    "PAY",   # Payment (DBS internal)
})

# ── Cash withdrawal codes ─────────────────────────────────────────────────────
# These always map to 'Cash Withdrawals' regardless of direction.
CASH_CODES: frozenset[str] = frozenset({
    "AWL",   # Cash Withdrawal
    "WDL",   # Withdrawal
    "NWL",   # Cash Withdrawal Others
    "C-WDL", # CIRRUS Cash Withdrawal
    "ATM",   # ATM Transactions
})

# ── Merchant keyword map ──────────────────────────────────────────────────────
# Consulted when the transaction code is generic or absent.
# Keys are lowercase substrings matched against the normalised description.
MERCHANT_CATEGORY_MAP: dict[str, str] = {
    # Food & Drink
    "grab food":         "Food & Drink",
    "grabfood":          "Food & Drink",
    "foodpanda":         "Food & Drink",
    "deliveroo":         "Food & Drink",
    "mcdonald":          "Food & Drink",
    "fairprice":         "Food & Drink",
    "sheng siong":       "Food & Drink",
    "cold storage":      "Food & Drink",
    "giant":             "Food & Drink",
    "kopitiam":          "Food & Drink",
    "hawker":            "Food & Drink",
    "starbucks":         "Food & Drink",
    "toast box":         "Food & Drink",
    "ya kun":            "Food & Drink",
    "old chang kee":     "Food & Drink",
    "bengawan":          "Food & Drink",
    "prima deli":        "Food & Drink",
    "bread talk":        "Food & Drink",
    "4fingers":          "Food & Drink",
    "jollibee":          "Food & Drink",
    "subway":            "Food & Drink",
    "burger king":       "Food & Drink",
    "kfc":               "Food & Drink",
    "pizza":             "Food & Drink",
    "dining":            "Food & Drink",
    "restaurant":        "Food & Drink",
    "cafe":              "Food & Drink",
    "bakery":            "Food & Drink",
    # Subscriptions
    "spotify":           "Subscriptions",
    "netflix":           "Subscriptions",
    "apple.com/bill":    "Subscriptions",
    "apple.com":         "Subscriptions",
    "google play":       "Subscriptions",
    "amazon prime":      "Subscriptions",
    "disney+":           "Subscriptions",
    "disneyplus":        "Subscriptions",
    "youtube premium":   "Subscriptions",
    "microsoft 365":     "Subscriptions",
    "adobe":             "Subscriptions",
    "chatgpt":           "Subscriptions",
    "openai":            "Subscriptions",
    "notion":            "Subscriptions",
    "dropbox":           "Subscriptions",
    "icloud":            "Subscriptions",
    # Transport
    "comfort":           "Transport",
    "comfortdelgro":     "Transport",
    "cdg":               "Transport",
    "gojek":             "Transport",
    "uber":              "Transport",
    "grab transport":    "Transport",
    "grab car":          "Transport",
    "grab taxi":         "Transport",
    "transit link":      "Transport",
    "transitlink":       "Transport",
    "ez-link":           "Transport",
    "smrt":              "Transport",
    "sbst":              "Transport",
    "sbs transit":       "Transport",
    "parking":           "Transport",
    "car park":          "Transport",
    "esso":              "Transport",
    "shell":             "Transport",
    "caltex":            "Transport",
    "spc":               "Transport",
    "koolex":            "Transport",
    "grab ride":         "Transport",
    "tada":              "Transport",
    "ryde":              "Transport",
    "phv":               "Transport",
    # Health & Wellness
    "watsons":           "Health & Wellness",
    "guardian":          "Health & Wellness",
    "unity pharmacy":    "Health & Wellness",
    "ntuc unity":        "Health & Wellness",
    "polyclinic":        "Health & Wellness",
    "hospital":          "Health & Wellness",
    "dental":            "Health & Wellness",
    "clinic":            "Health & Wellness",
    "physiotherapy":     "Health & Wellness",
    "optometrist":       "Health & Wellness",
    "eyecare":           "Health & Wellness",
    "gym":               "Health & Wellness",
    "fitness":           "Health & Wellness",
    "anytime fitness":   "Health & Wellness",
    "pure fitness":      "Health & Wellness",
    "activesg":          "Health & Wellness",
    # Utilities
    "singapore power":   "Utilities",
    "sp services":       "Utilities",
    "sp group":          "Utilities",
    "starhub":           "Utilities",
    "singtel":           "Utilities",
    "m1 limited":        "Utilities",
    "myrepublic":        "Utilities",
    "viewqwest":         "Utilities",
    "pub ":              "Utilities",    # trailing space avoids matching 'public'
    # Shopping
    "ikea":              "Shopping",
    "uniqlo":            "Shopping",
    "zara":              "Shopping",
    "h&m":               "Shopping",
    "lazada":            "Shopping",
    "shopee":            "Shopping",
    "amazon":            "Shopping",
    "courts":            "Shopping",
    "harvey norman":     "Shopping",
    "best denki":        "Shopping",
    "challenger":        "Shopping",
    "wristcheck":        "Shopping",
    "taobao":            "Shopping",
    # Entertainment
    "cathay":            "Entertainment",
    "golden village":    "Entertainment",
    "gv ":               "Entertainment",
    "shaw":              "Entertainment",
    "sports hub":        "Entertainment",
    "escape":            "Entertainment",
    "laser quest":       "Entertainment",
    "bowling":           "Entertainment",
    "ktv":               "Entertainment",
    "karaoke":           "Entertainment",
    # Education
    "nus":               "Education",
    "ntu":               "Education",
    "smu":               "Education",
    "sit ":              "Education",
    "sutd":              "Education",
    "kaplan":            "Education",
    "school fee":        "Education",
    "tuition":           "Education",
    "coursera":          "Education",
    "udemy":             "Education",
    "skillsfuture":      "Education",
    # Income — keyword fallback only; bidirectional codes handle most salary
    "salary credit":     "Income",
    "payroll":           "Income",
}


def categorise(
    code: str | None,
    description: str,
    amount: float,
    code_cache: dict[str, str],
) -> str:
    """
    5-Tier Confidence System — returns the best category name.

    Tier 1a — Cash code:          AWL/WDL/ATM etc → always 'Cash Withdrawals'
    Tier 1b — Bidirectional code: sign of amount → 'Income' or 'PayNow & FAST'
    Tier 2  — High-signal code:   known, not generic → trust DB mapping
    Tier 3  — Merchant keyword:   generic/missing code + description match
    Tier 4  — Low-signal code:    generic code, unknown merchant → broad DB mapping
    Tier 5  — Absolute fallback:  'Uncategorised'
    """
    is_valid   = isinstance(code, str) and bool(code)
    in_db      = is_valid and code in code_cache
    is_generic = is_valid and code in GENERIC_CODES
    is_cash    = is_valid and code in CASH_CODES
    is_bidir   = is_valid and code in BIDIRECTIONAL_CODES

    keyword_cat = _keyword_match(description)
    keyword_hit = keyword_cat != "Uncategorised"

    # Tier 1a: cash withdrawal codes are unambiguous
    if is_cash:
        return "Cash Withdrawals"

    # Tier 1b: bidirectional — amount sign determines direction
    if is_bidir:
        return "Income" if amount > 0 else "PayNow & FAST"

    # Tier 2: high-signal, specific code
    if in_db and not is_generic:
        return code_cache[code]

    # Tier 3: merchant keyword beats a generic code
    if keyword_hit:
        return keyword_cat

    # Tier 4: generic code with no keyword match — broad category is better than nothing
    if in_db:
        return code_cache[code]

    return "Uncategorised"


def _keyword_match(description: str) -> str:
    desc_lower = description.lower()
    for keyword, category in MERCHANT_CATEGORY_MAP.items():
        if keyword in desc_lower:
            return category
    return "Uncategorised"
