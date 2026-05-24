-- ============================================================
-- Personal Finance Tracker — SQLite Database Schema
-- ============================================================
-- Design principles:
--   • 
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ------------------------------------------------------------
-- Table 1: Categories
-- Every merchant belongs to one category.
-- Examples: 'Food & Drink', 'Transport', 'Subscriptions', 'Education'
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Categories (
    category_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE
);

INSERT OR IGNORE INTO Categories (name) VALUES
    ('Food & Drink'),
    ('Transport'),
    ('Subscriptions'),
    ('Health & Wellness'),
    ('Shopping'),
    ('Utilities'),
    ('Entertainment'),
    -- Transfers split into three specific subcategories
    ('Transfers'),              -- catch-all fallback only
    ('PayNow & FAST'),          -- outbound peer-to-peer (ICT, GR negative)
    ('Cash Withdrawals'),       -- ATM / counter cash (AWL, WDL)
    ('Internal Transfers'),     -- own-account movements (DBS to DBS)
    ('Income'),
    ('Banking Fees'),           -- service charges, annual fees, etc.
    ('Investments'),            -- unit trusts, fixed deposits, shares, SGS
    ('Education'),              -- school fees, study loans, tuition
    ('Insurance'),              -- life, general, travel insurance premiums
    ('Donations'),              -- charitable & self-help group donations
    ('Loans & Mortgage'),       -- housing, personal, renovation loans
    ('Government & CPF'),       -- CPF, IRAS, government agencies
    ('Uncategorised');

-- ------------------------------------------------------------
-- Table 2: Transaction Codes
-- Stores every DBS/POSB transaction code with its official
-- description and the category we've mapped it to.
-- Seeded at runtime by transaction_codes_loader.py.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS TransactionCodes (
    code          TEXT    PRIMARY KEY,   -- e.g. 'SALA', 'FAST', 'ATM'
    description   TEXT    NOT NULL,      -- official DBS description
    category_id   INTEGER NOT NULL
                  REFERENCES Categories(category_id)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_txcode_cat ON TransactionCodes(category_id);

-- ------------------------------------------------------------
-- Table 3: Merchants
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Merchants (
    merchant_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    category_id   INTEGER NOT NULL
                  REFERENCES Categories(category_id)
                  ON UPDATE CASCADE
                  ON DELETE RESTRICT
);

-- ------------------------------------------------------------
-- Table 4: Transactions
-- Each row is one bank transaction line.
-- amount is always stored as a signed decimal:
--   negative  → withdrawal / expense
--   positive  → deposit / income
-- transaction_hash = SHA-256(date || '|' || amount || '|' || description)
-- Computed in Python before insert; UNIQUE prevents re-import duplicates.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Transactions (
    transaction_id    INTEGER PRIMARY KEY,
    transaction_date  TEXT    NOT NULL,
    amount            REAL    NOT NULL,
    description       TEXT    NOT NULL,
    merchant_id       INTEGER NOT NULL
                      REFERENCES Merchants(merchant_id)
                      ON UPDATE CASCADE
                      ON DELETE RESTRICT,
    transaction_code  TEXT
                      REFERENCES TransactionCodes(code)
                      ON UPDATE CASCADE
                      ON DELETE SET NULL,
    transaction_hash  TEXT    NOT NULL UNIQUE,  -- deduplication key
    created_at        TEXT    NOT NULL
                      DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
 
CREATE INDEX IF NOT EXISTS idx_txn_date     ON Transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_merchant ON Transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_txn_code     ON Transactions(transaction_code);
CREATE INDEX IF NOT EXISTS idx_txn_hash     ON Transactions(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_merchant_cat ON Merchants(category_id);

-- ------------------------------------------------------------
-- Table 5: Budgets
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Budgets (
    category VARCHAR PRIMARY KEY,
    monthly_limit REAL NOT NULL DEFAULT 0.0
);

-- ------------------------------------------------------------
-- Denormalised read view
-- ------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_transactions_full AS
SELECT
    t.transaction_id,
    t.transaction_date,
    t.amount,
    t.description,
    t.transaction_code,
    t.transaction_hash,
    tc.description  AS code_description,
    m.name          AS merchant,
    c.name          AS category
FROM  Transactions    t
JOIN  Merchants       m  ON t.merchant_id      = m.merchant_id
JOIN  Categories      c  ON m.category_id      = c.category_id
LEFT  JOIN TransactionCodes tc ON t.transaction_code = tc.code;