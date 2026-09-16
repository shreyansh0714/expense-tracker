# Implementation Plan — Step 1: Database Setup

Source spec: `.claude/specs/01-databse-setup.md`

## Scope

Only two files change:
- `database/db.py` — implement `get_db()`, `init_db()`, `seed_db()`
- `app.py` — import those three functions and call `init_db()`/`seed_db()` on startup

No new routes, no new templates, no new dependencies. `app.py`'s existing routes are untouched.

## 1. `database/db.py`

DB file: `database.db` in the project root (matches existing CLAUDE.md reference), opened with a plain relative path since the app is always run from `expense-tracker/`.

```python
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
```

Notes:
- `today.replace(day=N)` keeps all seed dates inside the current month regardless of when the seed runs, and avoids hardcoding a month/year that goes stale. All 7 categories are covered, with Food used twice for 8 total rows.
- `seed_db()` guards on `users` row count, matching spec section 5C.
- Every query uses `?` placeholders — no string formatting anywhere, satisfying spec section 11.

## 2. `app.py`

Add the import and startup calls; nothing else in the file changes.

```python
from flask import Flask, render_template
from database.db import get_db, init_db, seed_db

app = Flask(__name__)

with app.app_context():
    init_db()
    seed_db()
```

`get_db` is imported now (per spec section 6) even though no route calls it yet — later steps (auth) will use it directly.

## Verification (Definition of Done, spec section 14)

1. Run `python app.py` from `expense-tracker/` — confirm no startup errors and `database.db` is created in the project root.
2. Run `python app.py` a second time — confirm no duplicate demo user/expenses (re-check row counts).
3. Quick self-check script (throwaway, not committed) or a one-off `python -c`:
   - `sqlite3.connect("database.db")` → `PRAGMA foreign_key_check` returns nothing
   - `SELECT COUNT(*) FROM users` == 1, `SELECT COUNT(*) FROM expenses` == 8
   - Attempt duplicate email insert → raises `sqlite3.IntegrityError`
   - Attempt expense insert with a bogus `user_id` → raises `sqlite3.IntegrityError` (confirms `PRAGMA foreign_keys = ON` is active)
4. Existing routes (`/`, `/register`, `/login`, `/terms`, `/privacy`) still render — startup DB calls shouldn't affect them.

## Explicitly out of scope

- No POST handlers for register/login (Step 3)
- No use of `get_db()` from any route yet
- No new templates, no new pip packages
