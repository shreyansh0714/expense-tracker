import pytest

from app import app as flask_app
from database import db


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Point get_db() at a throwaway file so tests never touch the real
    # database.db. monkeypatch puts the original path back after each test.
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def auth_client(client):
    # A client that is already registered and logged in.
    client.post(
        "/register",
        data={"name": "Test User", "email": "test@example.com", "password": "testpass1"},
    )
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "testpass1"},
    )
    return client
