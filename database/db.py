import json
import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash

DB_PATH = "database.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            monthly_budget REAL,
            notes TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    # Existing databases created before these columns existed won't have
    # them yet; SQLite has no "ADD COLUMN IF NOT EXISTS", so add them
    # idempotently and ignore the error when they're already there.
    for column, coltype in (("monthly_budget", "REAL"), ("notes", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column} {coltype}")
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute("ALTER TABLE expenses ADD COLUMN updated_at TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expense_edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            edited_at TEXT NOT NULL,
            old_amount REAL NOT NULL,
            new_amount REAL NOT NULL,
            old_category TEXT NOT NULL,
            new_category TEXT NOT NULL,
            old_date TEXT NOT NULL,
            new_date TEXT NOT NULL,
            old_description TEXT,
            new_description TEXT,
            FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
        )
    """)
    # Edits saved before expense_edits existed have no history to show, so
    # they lose their "edited" badge. A no-op once every edit writes history.
    conn.execute(
        "UPDATE expenses SET updated_at = NULL WHERE updated_at IS NOT NULL "
        "AND id NOT IN (SELECT expense_id FROM expense_edits)"
    )
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    already_seeded = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if already_seeded:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cur.lastrowid

    today = date.today()
    sample_expenses = [
        (user_id, 45.50, "Food", today.replace(day=1).isoformat(), "Groceries"),
        (user_id, 12.00, "Transport", today.replace(day=3).isoformat(), "Bus pass"),
        (user_id, 89.99, "Bills", today.replace(day=5).isoformat(), "Electricity"),
        (user_id, 25.00, "Health", today.replace(day=7).isoformat(), "Pharmacy"),
        (user_id, 15.75, "Entertainment", today.replace(day=9).isoformat(), "Movie ticket"),
        (user_id, 60.00, "Shopping", today.replace(day=11).isoformat(), "New shoes"),
        (user_id, 9.50, "Other", today.replace(day=13).isoformat(), "Misc"),
        (user_id, 22.30, "Food", today.replace(day=14).isoformat(), "Restaurant"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def update_user(user_id, name, email, monthly_budget, notes, password=None):
    conn = get_db()
    try:
        if password:
            password_hash = generate_password_hash(password)
            conn.execute(
                "UPDATE users SET name = ?, email = ?, monthly_budget = ?, "
                "notes = ?, password_hash = ? WHERE id = ?",
                (name, email, monthly_budget, notes, password_hash, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET name = ?, email = ?, monthly_budget = ?, "
                "notes = ? WHERE id = ?",
                (name, email, monthly_budget, notes, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_monthly_budget(user_id, monthly_budget):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET monthly_budget = ? WHERE id = ?",
            (monthly_budget, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_category_totals(user_id, start, end):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses "
            "WHERE user_id = ? AND date >= ? AND date <= ? "
            "GROUP BY category ORDER BY total DESC",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    finally:
        conn.close()


def get_transaction_count(user_id, start, end):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM expenses "
            "WHERE user_id = ? AND date >= ? AND date <= ?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchone()[0]
    finally:
        conn.close()


def get_recent_expenses(user_id, start, end, limit=5):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? AND date >= ? AND date <= ? "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, start.isoformat(), end.isoformat(), limit),
        ).fetchall()
    finally:
        conn.close()


def get_first_expense_date(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT MIN(date) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    finally:
        conn.close()


def get_monthly_spend(user_id, start, end):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT substr(date, 1, 7) AS month, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? AND date >= ? AND date <= ? "
            "GROUP BY month",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    finally:
        conn.close()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_expense(user_id, expense_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()


def update_expense(user_id, expense_id, amount, category, date, description):
    """Update one of the user's expenses and record the change in expense_edits.

    Both writes share one commit, so an edit never exists without its history.
    """
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
        if old is None:
            return False
        now = conn.execute("SELECT datetime('now')").fetchone()[0]
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?, "
            "updated_at = ? WHERE id = ? AND user_id = ?",
            (amount, category, date, description, now, expense_id, user_id),
        )
        conn.execute(
            "INSERT INTO expense_edits (expense_id, edited_at, old_amount, new_amount, "
            "old_category, new_category, old_date, new_date, old_description, new_description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (expense_id, now, old["amount"], amount, old["category"], category,
             old["date"], date, old["description"], description),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_expense_edits(user_id, expense_ids):
    """Edit history for the given expenses (only the user's own), newest first."""
    if not expense_ids:
        return []
    conn = get_db()
    try:
        # The id list travels as one JSON parameter, so the SQL text stays fixed.
        return conn.execute(
            "SELECT expense_edits.* FROM expense_edits "
            "JOIN expenses ON expenses.id = expense_edits.expense_id "
            "WHERE expenses.user_id = ? "
            "AND expense_edits.expense_id IN (SELECT value FROM json_each(?)) "
            "ORDER BY expense_edits.edited_at DESC, expense_edits.id DESC",
            (user_id, json.dumps(list(expense_ids))),
        ).fetchall()
    finally:
        conn.close()


def delete_expense(user_id, expense_id):
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()
