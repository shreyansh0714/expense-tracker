---
description: Seed one random dummy user (no expenses) into database.db for manual testing
allowed-tools: Bash(python3:*)
---

Insert one new dummy user into `database.db`, with zero expenses, reusing
`get_db()` and the same insert pattern `seed_db()` uses in `database/db.py` —
do not add a new function to `database/db.py`, do not touch the `expenses`
table.

## Examples

`/seed-user` — takes no arguments; creates one fresh randomly-named user each run.

## What to do

This performs a database write (an `INSERT`), so it must NOT go in a
`` ```! `` block — those run automatically before you're even involved, with
no permission prompt, and are meant only for read-only context gathering
(a `git diff`, a `SELECT`), never for writes. Instead, run the following
command yourself using your Bash tool (`allowed-tools` already grants
`Bash(python3:*)`), from the `expense-tracker/` repo root:

```bash
python3 - <<'PYEOF'
import secrets
import uuid

from database.db import get_db
from werkzeug.security import generate_password_hash

suffix = uuid.uuid4().hex[:8]
name = f'Dummy User {suffix}'
email = f'dummy_{suffix}@example.com'
password = secrets.token_urlsafe(8)
password_hash = generate_password_hash(password)

conn = get_db()
cur = conn.execute(
    'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
    (name, email, password_hash),
)
conn.commit()
user_id = cur.lastrowid
conn.close()

print(f'id: {user_id}')
print(f'name: {name}')
print(f'email: {email}')
print(f'password: {password}')
PYEOF
```
