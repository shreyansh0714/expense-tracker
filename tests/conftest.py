import atexit
import os
import secrets
import tempfile

import pytest

# Point the database at a throwaway file BEFORE app is imported. Importing
# app runs init_db() and seed_db(), and without this they would open the
# real database.db.
_fd, _import_db = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["SPENDLY_DB"] = _import_db
atexit.register(os.remove, _import_db)  # clean up the temp file after the run

from app import app as flask_app  # noqa: E402
from database import db  # noqa: E402

assert db.DB_PATH != "database.db", "tests must never use the real database.db"


def csrf_post(client, url, data=None, **kwargs):
    """POST like a real browser form: with a valid CSRF token.

    A fresh token is written into the session right before every post,
    because login clears the session (and its token) each time.
    """
    token = secrets.token_hex(32)
    with client.session_transaction() as sess:
        sess["csrf_token"] = token
    form = dict(data or {})
    form["csrf_token"] = token
    return client.post(url, data=form, **kwargs)


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Each test also gets its own fresh database file. monkeypatch puts the
    # previous path back after the test.
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def auth_client(client):
    # A client that is already registered and logged in.
    csrf_post(
        client,
        "/register",
        data={"name": "Test User", "email": "test@example.com", "password": "testpass1"},
    )
    csrf_post(
        client,
        "/login",
        data={"email": "test@example.com", "password": "testpass1"},
    )
    return client
