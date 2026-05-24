"""
core/categoriser.py
===================
All categorisation constants and the 5-tier confidence system.
Imported by etl.py (persistent mode) and app.py (session mode).
"""

# ── Generic codes ─────────────────────────────────────────────────────────────
GENERIC_CODES: frozenset[str] = frozenset({
    "MST", "POS", "NETS", "BAT", "DEP", "WDL", "AWL", "CCCC",
})

# ── Bidirectional codes ───────────────────────────────────────────────────────
BIDIRECTIONAL_CODES: frozenset[str] = frozenset({
    "ICT", "GR", "GRP", "GRS", "GRC", "GRB", "IBG", "DCR", "DCRT", "PAY",
})

# ── Cash withdrawal codes ─────────────────────────────────────────────────────
CASH_CODES: frozenset[str] = frozenset({
    "AWL", "WDL", "NWL", "C-WDL", "ATM",
})

# ── Merchant keyword map ──────────────────────────────────────────────────────
# ORDERING RULE: longer / more specific strings must come before shorter ones
# that are substrings of them.  E.g. "grab food" before any bare "grab*"
# entry, or the shorter key wins first.  There is NO bare "grab" entry here
# for exactly this reason — it would swallow GrabFood orders into Transport.
MERCHANT_CATEGORY_MAP: dict[str, str] = {
    # ── Food & Drink ──────────────────────────────────────────────────────────
    "grab food":         "Food & Drink",
    "grabfood":          "Food & Drink",
    "food panda":        "Food & Drink",
    "foodpanda":         "Food & Drink",
    "fp*food panda":     "Food & Drink",
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
    "yqueue":            "Food & Drink",
    "dabba street":      "Food & Drink",
    "wingstop":          "Food & Drink",
    "shiok burger":      "Food & Drink",
    "chagee":            "Food & Drink",
    "supersnacks":       "Food & Drink",
    "stuff'd":           "Food & Drink",
    "coffee":            "Food & Drink",
    "beviamo":           "Food & Drink",
    "f&b":               "Food & Drink",

    # ── Subscriptions ─────────────────────────────────────────────────────────
    "spotify":           "Subscriptions",
    "netflix":           "Subscriptions",
    "apple.com/bill":    "Subscriptions",
    "apple.com":         "Subscriptions",
    "google play":       "Subscriptions",
    "amazon prime":      "Subscriptions",
    "amznprimesg":       "Subscriptions",
    "disney+":           "Subscriptions",
    "disneyplus":        "Subscriptions",
    "youtubepremium":    "Subscriptions",
    "youtube":           "Subscriptions",
    "google*youtube":    "Subscriptions",
    "microsoft 365":     "Subscriptions",
    "adobe":             "Subscriptions",
    "chatgpt":           "Subscriptions",
    "openai":            "Subscriptions",
    "notion":            "Subscriptions",
    "dropbox":           "Subscriptions",
    "icloud":            "Subscriptions",
    "subscriptiongrab":  "Subscriptions",
    "grab subscription": "Subscriptions",   # Grab Premium subscription

    # ── Transport ─────────────────────────────────────────────────────────────
    # NOTE: No bare "grab" entry — it would incorrectly catch GrabFood orders.
    "grab transport":    "Transport",
    "grab car":          "Transport",
    "grab taxi":         "Transport",
    "grab ride":         "Transport",
    "grabpay-ec":        "Transport",       # overseas GrabPay (MYS/etc) — almost always transport
    "grab":              "Transport",       # bare GRAB card transaction — cannot distinguish food vs transport;
    "comfort":           "Transport",
    "comfortdelgro":     "Transport",
    "cdg":               "Transport",
    "gojek":             "Transport",
    "uber":              "Transport",
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
    "tada":              "Transport",
    "ryde":              "Transport",
    "phv":               "Transport",

    # ── Health & Wellness ─────────────────────────────────────────────────────
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
    "hockhua":           "Health & Wellness",

    # ── Utilities ─────────────────────────────────────────────────────────────
    "singapore power":   "Utilities",
    "sp services":       "Utilities",
    "sp group":          "Utilities",
    "starhub":           "Utilities",
    "singtel":           "Utilities",
    "m1 limited":        "Utilities",
    "myrepublic":        "Utilities",
    "viewqwest":         "Utilities",
    "pub ":              "Utilities",    # trailing space avoids matching 'public'

    # ── Shopping ──────────────────────────────────────────────────────────────
    "ikea":              "Shopping",
    "uniqlo":            "Shopping",
    "zara":              "Shopping",
    "h&m":               "Shopping",
    "lazada":            "Shopping",
    "shopee":            "Shopping",
    "amazon":            "Shopping",    # after "amazon prime" / "amznprimesg"
    "courts":            "Shopping",
    "harvey norman":     "Shopping",
    "best denki":        "Shopping",
    "challenger":        "Shopping",
    "wristcheck":        "Shopping",
    "taobao":            "Shopping",
    "shein":             "Shopping",
    "aliexpress":        "Shopping",

    # ── Entertainment ─────────────────────────────────────────────────────────
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
    "have fun":          "Entertainment",

    # ── Education ─────────────────────────────────────────────────────────────
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

    # ── Investments ───────────────────────────────────────────────────────────
    "interactive brokers": "Investments",

    # ── Transfers ─────────────────────────────────────────────────────────────
    "top-up to paylah!": "Transfers",

    # ── Income (keyword fallback — bidirectional codes handle most salary) ────
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
    5-Tier Confidence System.

    Tier 0  — Manual override:    description substring → hardcoded category
    Tier 1a — Cash code:          AWL/WDL/ATM → always 'Cash Withdrawals'
    Tier 1b — Bidirectional code: sign of amount → 'Income' or 'PayNow & FAST'
    Tier 2  — High-signal code:   known, not generic → trust DB mapping
    Tier 3  — Merchant keyword:   generic/missing code + keyword match
    Tier 4  — Low-signal fallback: generic code, no keyword → broad DB category
    Tier 5  — Absolute fallback:  'Uncategorised'
    """
    is_valid   = isinstance(code, str) and bool(code)
    in_db      = is_valid and code in code_cache
    is_generic = is_valid and code in GENERIC_CODES
    is_cash    = is_valid and code in CASH_CODES
    is_bidir   = is_valid and code in BIDIRECTIONAL_CODES

    keyword_cat = _keyword_match(description)
    keyword_hit = keyword_cat != "Uncategorised"

    # Tier 1a
    if is_cash:
        return "Cash Withdrawals"

    # Tier 1b
    if is_bidir:
        return "Income" if amount > 0 else "PayNow & FAST"

    # Tier 2
    if in_db and not is_generic:
        return code_cache[code]

    # Tier 3
    if keyword_hit:
        return keyword_cat

    # Tier 4
    if in_db:
        return code_cache[code]

    return "Uncategorised"


def _keyword_match(description: str) -> str:
    desc_lower = description.lower()
    for keyword, category in MERCHANT_CATEGORY_MAP.items():
        if keyword in desc_lower:
            return category
    return "Uncategorised"