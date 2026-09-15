---
description: Seed N random expenses for an existing user, spread across the last M months
argument-hint: "[name] [count] [months]"
allowed-tools: Bash(python3:*), Bash(sqlite3:*)
---

Seed `$1` random expenses for the user named `$0`, spread evenly across the last
`$2` months (current month included). The user must already exist — this
command never creates a user (use `/seed-user` for that).

## Users currently in the database

!`sqlite3 database.db "SELECT id, name, email FROM users;"`

Pick `$0` from the `name` column above — do not invent a name that isn't listed.

## Examples

`/seed-expense "Dummy User 54eba4a9" 10 3` — 10 expenses for that user, spread
across this month and the 2 before it.

## Implementation notes

Reuses `get_db()` and the same parameterized `INSERT INTO expenses (user_id,
amount, category, date, description) VALUES (?, ?, ?, ?, ?)` pattern already
used by `seed_db()` in `database/db.py` — do not add a new function to
`database/db.py`, and do not touch the `users` table.

## What to do

This performs a database write (an `INSERT`), so it must NOT go in a
`` ```! `` block like the read-only user list above — those run automatically
before you're even involved, with no permission prompt, and are meant only
for read-only context gathering, never for writes. Instead, run the
following command yourself using your Bash tool (`allowed-tools` already
grants `Bash(python3:*)`), from the `expense-tracker/` repo root:

```bash
python3 - "$0" "$1" "$2" <<'PYEOF'
import random
import sys
from datetime import date

from database.db import get_db

name = sys.argv[1]
count = int(sys.argv[2])
months = int(sys.argv[3])

conn = get_db()
rows = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchall()
if len(rows) == 0:
    conn.close()
    sys.exit(f"No user found with name '{name}' - nothing seeded")
if len(rows) > 1:
    conn.close()
    sys.exit(f"{len(rows)} users found with name '{name}' - name must be unambiguous, nothing seeded")
user_id = rows[0]["id"]

categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

today = date.today()
month_starts = []
for i in range(months - 1, -1, -1):
    y, m = today.year, today.month - i
    while m <= 0:
        m += 12
        y -= 1
    month_starts.append((y, m))

base, extra = divmod(count, months)
counts_per_month = [base + (1 if i < extra else 0) for i in range(months)]

expenses = []
idx = 0
for (y, m), n in zip(month_starts, counts_per_month):
    for _ in range(n):
        category = categories[idx % len(categories)]
        amount = round(random.uniform(5, 200), 2)
        day = random.randint(1, 28)
        expense_date = date(y, m, day).isoformat()
        description = f"Sample {category} expense"
        expenses.append((user_id, amount, category, expense_date, description))
        idx += 1

conn.executemany(
    "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
    expenses,
)
conn.commit()
conn.close()

print(f"Seeded {count} expenses for '{name}' (user_id={user_id}) across {months} month(s):")
for (y, m), n in zip(month_starts, counts_per_month):
    print(f"  {y}-{m:02d}: {n} expense(s)")
PYEOF
```
