"""
transaction_codes_loader.py
===========================
Parses the DBS/POSB transaction code reference file and seeds the
TransactionCodes table in the SQLite database.

The txt file alternates lines:  CODE  →  DESCRIPTION  →  CODE  →  ...
We parse each pair, assign a category via keyword rules on the description,
then bulk-insert into TransactionCodes using INSERT OR IGNORE so the loader
is safe to re-run without creating duplicates.

Usage (standalone):
    python transaction_codes_loader.py --codes DBS_Transaction_Codes.txt --db finance.db
"""

import re
import sqlite3
import logging
import argparse
from pathlib import Path

log = logging.getLogger(__name__)

# ── Category assignment rules ─────────────────────────────────────────────────
# Evaluated in order; first match wins. Each entry is (keyword_list, category).
# Keywords are matched case-insensitively against the official DBS description.
#
# Rule ordering rationale:
#   • Specific multi-word phrases first  ("fixed deposit interest" before "interest")
#   • Then single high-signal words
#   • Catch-all "Uncategorised" is the Python fallback, not listed here

CATEGORY_RULES: list[tuple[list[str], str]] = [

    # ── Income ────────────────────────────────────────────────────────────────
    (["salary", "payroll", "pay credit"],                   "Income"),
    (["dividend", "dividends payment", "dividends/cash"],   "Income"),
    (["interest earned", "bonus interest", "credit interest",
      "interest on mma", "total interest", "top up interest",
      "fixed deposit interest", "savings reward", "cashback bonus",
      "workfare", "silver support", "baby bonus", "growth dividend",
      "government payout", "gst voucher", "gstv", "saye cash gift",
      "saye account", "special reward", "cash-point incentive",
      "inward remittance", "cpf profit transfer",
      "guaranteed notes issuance"],                         "Income"),
    (["payroll", "giro payroll", "salary credit",
      "inward fast", "fast receipt",
      "instant direct credit"],                             "Income"),

    # ── Transfers ─────────────────────────────────────────────────────────────
    (["funds transfer", "fund transfer", "telegraphic transfer",
      "fast payment", "fast or paynow", "fast receipt",
      "paynow", "interbank", "giro", "instant direct credit",
      "instant direct debit", "meps payment", "meps receipt",
      "remittance", "cancellation transfer", "creation transfer",
      "returned interbank", "standing instruction",
      "cash withdrawal", "atm transaction", "cash deposit",
      "regional funds", "outward demand draft", "inward demand draft",
      "cashier's order", "reversal", "returned cheque", "returned giro",
      "cheque writing", "cheque"],                          "Transfers"),

    # ── Banking Fees ──────────────────────────────────────────────────────────
    (["service charge", "annual fee", "monthly account fee",
      "debit card annual fee", "atm withdrawal fee",
      "debit card replacement", "debit card retrieval",
      "coin deposit fee", "cheque book fee", "cheque fee",
      "commitment fee", "processing fee", "repricing fee",
      "flash pay fee", "custody", "custodian",
      "interest statement fee", "admin", "administrative charge",
      "overdraft interest", "revolving credit",
      "short term advance", "overdraft"],                   "Banking Fees"),

    # ── Investments ───────────────────────────────────────────────────────────
    (["unit trust", "fixed deposit", "structured deposit",
      "singapore government securities", "sgs", "shares",
      "share transaction", "share financing", "share application",
      "ipo", "purchase / sale of shares", "purchase international",
      "leverage currency", "hedging", "investment of funds",
      "bonds", "rights", "dividends payment", "dividend claim",
      "redemption of units", "savings bond", "cpf investment",
      "nets proceeds", "cashcard proceeds"],                "Investments"),

    # ── Loans & Mortgage ──────────────────────────────────────────────────────
    (["housing loan", "mortgage loan", "renovation loan",
      "personal loan", "term loan", "short term loan",
      "revolving advance", "computer loan", "study loan",
      "tuition fee loan", "club membership loan",
      "share financing loan", "car financing",
      "hire purchase", "bill payment to dbs mortgage",
      "bill payment to dbs cashline", "staff"],             "Loans & Mortgage"),

    # ── Government & CPF ─────────────────────────────────────────────────────
    (["central provident fund", "cpf", "iras", "income tax",
      "property tax", "gst", "customs", "mas",
      "hdb", "housing & development board",
      "lta", "ura", "psa", "jtc", "public works",
      "ministry", "inland revenue", "monetary authority",
      "immigration", "cpf minimum sum"],                    "Government & CPF"),

    # ── Utilities ─────────────────────────────────────────────────────────────
    (["sp services", "power supply", "singapore power",
      "starhub", "singtel", "singapore telecom", "m1 limited",
      "pub", "public utilities", "keppel electric",
      "seraya energy", "geneco", "pager", "handphone",
      "mobilelink", "pagelink"],                            "Utilities"),

    # ── Health & Wellness ─────────────────────────────────────────────────────
    (["hospital", "medical", "dental", "health",
      "polyclinic", "eye centre", "cancer centre",
      "nursing", "pharmacy", "institute of mental",
      "kkh", "sgh", "nuh", "ttsh", "nhg",
      "khoo teck puat", "changi general", "sengkang general",
      "national university hospital", "assisi hospice",
      "dover park hospice"],                                "Health & Wellness"),

    # ── Insurance ─────────────────────────────────────────────────────────────
    (["insurance", "prudential", "great eastern",
      "aia", "manulife", "tokio marine", "china taiping",
      "loanshield", "fire insurance", "travellershield",
      "life insurance", "general insurance"],               "Insurance"),

    # ── Education ─────────────────────────────────────────────────────────────
    (["school", "university", "college", "education",
      "study", "tuition", "ntu", "nus", "smu",
      "kaplan", "nafa", "laselle", "james cook",
      "management development", "further studyassist",
      "scholarship"],                                       "Education"),

    # ── Donations ─────────────────────────────────────────────────────────────
    (["donation", "donate", "charity", "hospice",
      "nkf", "sinda", "mendaki", "self-help",
      "yellow ribbon", "rainbow", "touch community",
      "spd", "arc(s)", "leukemia", "cerebal palsy",
      "world vision", "red cross"],                         "Donations"),

    # ── Transport ─────────────────────────────────────────────────────────────
    (["taxi", "grab", "transit", "mrt", "ez-link",
      "transitlink", "comfort delgro", "bus", "lta coe",
      "uber", "gojek", "cabcharge", "vehicle",
      "car financing", "car lease", "petrol",
      "petroleum", "esso", "shell", "caltex", "spc",
      "7-eleven"],                                          "Transport"),

    # ── Food & Drink ──────────────────────────────────────────────────────────
    (["food panda", "foodpanda", "delivery hero",
      "mcdonald", "macdonalds", "sheng siong",
      "ntuc fairprice", "fairprice", "cold storage",
      "kopitiam", "hawker"],                                "Food & Drink"),

    # ── Shopping ─────────────────────────────────────────────────────────────
    (["point-of-sale", "point of sale", "nets", "debit card transaction",
      "e-commerce", "purchase", "cirrus purchase",
      "ikea", "isetan", "duty free", "aldo",
      "cash converters", "gnc"],                            "Shopping"),

    # ── Entertainment ─────────────────────────────────────────────────────────
    (["club", "country club", "golf", "racing",
      "singapore pools", "turf club", "cable vision",
      "tickets", "entertainment"],                          "Entertainment"),

    # ── Subscriptions ─────────────────────────────────────────────────────────
    (["magazine", "newspaper", "subscription",
      "standing instruction", "recurring"],                 "Subscriptions"),
]


def _assign_category(description: str) -> str:
    """
    Return the best-matching category name for a given DBS code description.
    Applies CATEGORY_RULES in order; returns 'Uncategorised' if nothing matches.
    """
    desc_lower = description.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Uncategorised"


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_codes_file(filepath: str) -> dict[str, str]:
    """
    Parse the DBS/POSB transaction code reference txt file.

    Format: lines alternate between CODE and DESCRIPTION.
    Line 1 = header "Transaction Codes/Descriptions" — skipped.
    Line 2 = header "Explanation" — skipped.
    Then pairs: code line, description line, code line, description line, …

    Returns a dict of {code: description}.
    """
    raw = Path(filepath).read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in raw.splitlines()]

    # Skip the two header lines
    lines = [ln for ln in lines if ln]   # drop blanks
    if lines and lines[0].lower().startswith("transaction code"):
        lines = lines[1:]
    if lines and lines[0].lower() == "explanation":
        lines = lines[1:]

    codes: dict[str, str] = {}
    i = 0
    while i + 1 < len(lines):
        code = lines[i].strip()
        desc = lines[i + 1].strip()

        # Skip pairs that look like two descriptions in a row
        # (heuristic: real codes are short and contain no lowercase letters
        #  after the first character, OR are known merchant-style codes)
        if code and desc:
            codes[code] = desc
        i += 2

    log.info("Parsed %d transaction codes from %s", len(codes), filepath)
    return codes


# ── Seeder ────────────────────────────────────────────────────────────────────

def seed_transaction_codes(conn: sqlite3.Connection,
                           codes: dict[str, str]) -> int:
    """
    Insert all parsed codes into the TransactionCodes table.
    Uses INSERT OR IGNORE so re-running is safe.

    Returns the number of newly inserted rows.
    """
    # Build a category_name → category_id lookup from the DB
    cat_rows = conn.execute(
        "SELECT category_id, name FROM Categories"
    ).fetchall()
    cat_map: dict[str, int] = {r["name"]: r["category_id"] for r in cat_rows}
    uncategorised_id = cat_map["Uncategorised"]

    rows_to_insert = []
    for code, description in codes.items():
        category_name = _assign_category(description)
        category_id   = cat_map.get(category_name, uncategorised_id)
        # Normalise code to uppercase so it matches what the ETL produces
        # after stripping and uppercasing the CSV's Transaction Code column.
        rows_to_insert.append((code.upper(), description, category_id))

    cursor = conn.executemany(
        "INSERT OR IGNORE INTO TransactionCodes (code, description, category_id) "
        "VALUES (?, ?, ?)",
        rows_to_insert,
    )
    inserted = cursor.rowcount
    log.info("Seeded %d new transaction code(s) into TransactionCodes.", inserted)
    return inserted


def load_codes_into_db(db_path: str, codes_path: str) -> None:
    """End-to-end helper: parse → seed."""
    import contextlib

    @contextlib.contextmanager
    def _conn(path):
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    codes = parse_codes_file(codes_path)
    with _conn(db_path) as conn:
        seed_transaction_codes(conn, codes)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_sample(db_path: str, n: int = 20) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT tc.code, tc.description, c.name AS category
        FROM   TransactionCodes tc
        JOIN   Categories       c ON tc.category_id = c.category_id
        ORDER  BY c.name, tc.code
        LIMIT  ?
        """, (n,)
    ).fetchall()
    conn.close()

    print(f"\n{'CODE':<30}  {'CATEGORY':<20}  DESCRIPTION")
    print("─" * 90)
    for r in rows:
        print(f"  {r['code']:<28}  {r['category']:<20}  {r['description']}")

    # Also print category distribution
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    dist = conn.execute(
        """
        SELECT c.name, COUNT(*) AS cnt
        FROM   TransactionCodes tc
        JOIN   Categories       c ON tc.category_id = c.category_id
        GROUP  BY c.name ORDER BY cnt DESC
        """
    ).fetchall()
    conn.close()

    print(f"\n{'CATEGORY':<25}  {'CODES MAPPED':>12}")
    print("─" * 40)
    for r in dist:
        print(f"  {r['name']:<23}  {r['cnt']:>12}")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")

    parser = argparse.ArgumentParser(
        description="Seed DBS transaction codes into the finance database"
    )
    parser.add_argument("--codes", required=True,
                        help="Path to DBS_Transaction_Codes txt file")
    parser.add_argument("--db", default="finance.db",
                        help="Path to SQLite database")
    args = parser.parse_args()

    load_codes_into_db(args.db, args.codes)
    _print_sample(args.db)
