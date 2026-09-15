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
            created_at TEXT DEFAULT (datetime('now'))
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
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
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
