"""Tests for Spec 10 — Security & reliability basics.

Written from `.claude/specs/10-security-and-reliability.md` only (no
app.py / database/ source was read). Covers AC1-AC25, AC3b and AC19b
where automatable through the Flask test client or by reading
documentation/config text files (never `app.py` or `database/`).

Not automated here (see the report handed back to the caller for why):
  - AC20 (the whole suite passing is a property of the whole pytest run,
    not a single test inside it — checking it from within itself is
    circular).
  - AC22's "its run on the PR is green" (requires an actual GitHub
    Actions run); the workflow file's existence/triggers ARE checked
    below (TestCIWorkflow).
  - AC24 ("students will implement these" removed from app.py) — this
    agent is forbidden from opening app.py.
"""

import html
import importlib
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest
from flask import url_for

from conftest import csrf_post, flask_app
from database import db

import app as app_module

REPO_ROOT = Path(__file__).resolve().parents[1]

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"

CSRF_INPUT_RE = re.compile(r'name="csrf_token" value="([0-9a-f]{64})"')


def _extract_csrf_token(html_bytes):
    match = CSRF_INPUT_RE.search(html_bytes.decode("utf-8"))
    return match.group(1) if match else None


def _location_path(resp):
    return urlparse(resp.headers.get("Location", "")).path or "/"


def _login_as_demo(client):
    """Approved exception FR8.4: seed_db() creates demo@spendly.com."""
    db.seed_db()
    csrf_post(client, "/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    return client


# ------------------------------------------------------------------ #
# FR1 — CSRF token rendering (AC1)
# ------------------------------------------------------------------ #
class TestCSRFTokenRendering:
    def test_login_page_renders_matching_csrf_token(self, client):
        resp = client.get("/login")
        token = _extract_csrf_token(resp.data)
        assert token is not None and len(token) == 64, (
            "login form must render a 64-hex-char csrf_token hidden input (AC1)"
        )
        with client.session_transaction() as sess:
            assert sess.get("csrf_token") == token, (
                "the rendered token must equal session['csrf_token'] (AC1)"
            )

    def test_register_page_renders_csrf_token(self, client):
        resp = client.get("/register")
        assert _extract_csrf_token(resp.data) is not None, (
            "register form must render a csrf_token hidden input (AC1, FR1.2)"
        )

    def test_add_expense_page_renders_csrf_token(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert _extract_csrf_token(resp.data) is not None, (
            "add-expense form must render a csrf_token hidden input (AC1, FR1.2)"
        )

    def test_edit_expense_page_renders_csrf_token(self, client):
        _login_as_demo(client)
        conn = db.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = "
            "(SELECT id FROM users WHERE email = ?) LIMIT 1",
            (DEMO_EMAIL,),
        ).fetchone()
        assert row is not None, "seed_db() must create at least one demo expense"
        resp = client.get(f"/expenses/{row['id']}/edit")
        assert _extract_csrf_token(resp.data) is not None, (
            "edit-expense form must render a csrf_token hidden input (AC1, FR1.2)"
        )

    def test_profile_page_renders_three_csrf_tokens_with_no_expenses(self, auth_client):
        resp = auth_client.get("/profile")
        page_html = resp.data.decode("utf-8")
        count = page_html.count('name="csrf_token"')
        assert count == 3, (
            "a user with no expenses has no delete popup, so /profile should "
            f"render 3 CSRF inputs: Sign out, budget, profile edit (AC1); found {count}"
        )

    def test_profile_page_renders_four_csrf_tokens_with_an_expense(self, auth_client):
        csrf_post(
            auth_client,
            "/expenses/add",
            data={
                "amount": "10",
                "category": "Food",
                "date": db.today_ist().isoformat(),
                "description": "Lunch",
            },
        )
        resp = auth_client.get("/profile")
        page_html = resp.data.decode("utf-8")
        count = page_html.count('name="csrf_token"')
        assert count == 4, (
            "with at least one expense, /profile should render 4 CSRF inputs: "
            "Sign out, budget, profile edit and the delete popup (AC1); "
            f"found {count}"
        )


# ------------------------------------------------------------------ #
# FR1 — CSRF rejection (AC2, AC3, AC3b, AC4)
# ------------------------------------------------------------------ #
class TestCSRFProtection:
    def test_add_expense_missing_token_no_referer_redirects_home(self, auth_client):
        conn = db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        resp = auth_client.post("/expenses/add", data={})
        assert resp.status_code == 302, "a missing CSRF token must be refused with a redirect (AC2)"
        assert _location_path(resp) == "/", (
            "with no Referer header, the refusal must redirect to '/' (AC2, FR1.3)"
        )
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        assert after == before, "a request with a missing CSRF token must save nothing (AC2)"

    def test_add_expense_missing_token_shows_expired_toast(self, auth_client):
        resp = auth_client.post("/expenses/add", data={}, follow_redirects=True)
        assert b"Your form expired. Please try again." in resp.data, (
            "AC2: the refusal toast must read exactly this"
        )

    def test_add_expense_missing_token_same_site_referer_redirects_back(self, auth_client):
        resp = auth_client.post(
            "/expenses/add",
            data={},
            headers={"Referer": "http://localhost/expenses/add"},
        )
        assert resp.status_code == 302
        assert _location_path(resp) == "/expenses/add", (
            "with a same-site Referer, the refusal must redirect back to that page (AC2, FR1.3)"
        )

    def test_add_expense_wrong_token_rejected(self, auth_client):
        conn = db.get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        with auth_client.session_transaction() as sess:
            sess["csrf_token"] = "a" * 64
        resp = auth_client.post("/expenses/add", data={"csrf_token": "b" * 64})
        assert resp.status_code == 302, "a wrong CSRF token must be refused exactly like a missing one (AC3)"
        assert _location_path(resp) == "/"
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        assert after == before

    def test_add_expense_wrong_token_shows_expired_toast(self, auth_client):
        with auth_client.session_transaction() as sess:
            sess["csrf_token"] = "a" * 64
        resp = auth_client.post(
            "/expenses/add", data={"csrf_token": "b" * 64}, follow_redirects=True
        )
        assert b"Your form expired. Please try again." in resp.data

    def test_forged_post_with_evil_referer_redirects_home_not_evil_site(self, client):
        resp = client.post(
            "/login", data={}, headers={"Referer": "https://evil.example/page"}
        )
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "evil.example" not in location, (
            "the CSRF refusal must never redirect to a third-party Referer (AC3b, FR1.3)"
        )
        assert _location_path(resp) == "/", (
            "a non-same-site Referer must fall back to '/' (AC3b, FR1.3)"
        )

    def test_login_missing_token_does_not_log_in(self, client):
        csrf_post(
            client,
            "/register",
            data={"name": "No Login", "email": "nologin@example.com", "password": "testpass1"},
        )
        csrf_post(client, "/logout")
        resp = client.post(
            "/login", data={"email": "nologin@example.com", "password": "testpass1"}
        )
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert "user_id" not in sess, (
                "login with correct credentials but no csrf_token must not log in (AC4)"
            )


# ------------------------------------------------------------------ #
# FR1/FR3 — valid token still works (AC5, part of AC11)
# ------------------------------------------------------------------ #
class TestCSRFDoesNotBreakNormalUse:
    def test_register_with_valid_token_creates_account_and_logs_in(self, client):
        resp = csrf_post(
            client,
            "/register",
            data={"name": "Normal User", "email": "normal@example.com", "password": "testpass1"},
        )
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert "user_id" in sess, "a valid CSRF token must let registration log the user in (AC5)"
        conn = db.get_db()
        row = conn.execute(
            "SELECT email FROM users WHERE email = ?", ("normal@example.com",)
        ).fetchone()
        assert row is not None, "register must create the user row"

    def test_login_with_valid_token_logs_in(self, client):
        csrf_post(
            client,
            "/register",
            data={"name": "Normal User 2", "email": "normal2@example.com", "password": "testpass1"},
        )
        csrf_post(client, "/logout")
        resp = csrf_post(
            client, "/login", data={"email": "normal2@example.com", "password": "testpass1"}
        )
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert "user_id" in sess

    def test_budget_update_with_valid_token_not_rejected_for_csrf(self, auth_client):
        # SPEC GAP: Spec 10 doesn't give the exact form field name(s) for
        # POST /profile/budget (owned by an earlier spec), so this only
        # confirms the CSRF check itself doesn't block a valid-token post.
        resp = csrf_post(
            auth_client, "/profile/budget", data={"budget": "500"}, follow_redirects=True
        )
        assert b"Your form expired. Please try again." not in resp.data


# ------------------------------------------------------------------ #
# FR2 — Logout becomes a POST button (AC6, AC7, AC8)
# ------------------------------------------------------------------ #
class TestLogout:
    def test_get_logout_returns_405(self, client):
        resp = client.get("/logout")
        assert resp.status_code == 405, "GET /logout must be refused with 405 (AC6, FR2.1)"

    def test_post_logout_with_valid_token_redirects_home(self, auth_client):
        resp = csrf_post(auth_client, "/logout")
        assert resp.status_code == 302
        assert _location_path(resp) == "/", "POST /logout must redirect to the landing page (AC7, FR2.3)"

    def test_logout_clears_entire_session(self, auth_client):
        with auth_client.session_transaction() as sess:
            sess["custom_marker"] = "pre-logout-value"
        csrf_post(auth_client, "/logout")
        with auth_client.session_transaction() as sess:
            assert "user_id" not in sess, "logout must clear user_id (AC7)"
            assert "custom_marker" not in sess, (
                "logout must session.clear() everything, not just user_id (AC7, FR2.3)"
            )

    def test_logout_button_is_post_form_pointing_to_logout_route(self, auth_client):
        with flask_app.test_request_context():
            logout_url = url_for("logout")
        resp = auth_client.get("/profile")
        html = resp.data.decode("utf-8")
        assert f'action="{logout_url}"' in html, (
            "the nav Sign out control must be a form posting to the logout route (AC8, FR2.2)"
        )
        assert '<form method="post"' in html, "the Sign out control must be a POST form (AC8)"
        assert "<button" in html, "the Sign out control must be a <button> (AC8)"


# ------------------------------------------------------------------ #
# FR3 — Demo account profile lock (AC9-AC13)
# ------------------------------------------------------------------ #
class TestDemoAccountLock:
    def test_demo_name_change_is_locked(self, client):
        _login_as_demo(client)
        resp = csrf_post(client, "/profile", data={"name": "Hacker"})
        assert resp.status_code == 302
        assert _location_path(resp) == "/profile", "a locked demo edit must redirect back to /profile (AC9)"
        conn = db.get_db()
        row = conn.execute("SELECT name FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
        assert row["name"] == "Demo User", "the demo account's name must not change (AC9)"

    def test_demo_name_change_shows_locked_toast(self, client):
        _login_as_demo(client)
        resp = csrf_post(client, "/profile", data={"name": "Hacker"}, follow_redirects=True)
        page_text = html.unescape(resp.data.decode("utf-8"))
        assert (
            "The demo account's profile can't be changed. "
            "Create your own free account to try this." in page_text
        ), "AC9: the demo-lock toast must read exactly this (apostrophes are HTML-escaped as &#39; in the source)"

    def test_demo_email_change_is_locked(self, client):
        _login_as_demo(client)
        csrf_post(client, "/profile", data={"email": "hacker@example.com"})
        conn = db.get_db()
        row = conn.execute(
            "SELECT email FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
        assert row is not None, "the demo account's email must still be demo@spendly.com (AC10)"

    def test_demo_password_change_is_locked(self, client):
        _login_as_demo(client)
        csrf_post(
            client,
            "/profile",
            data={"password": "newpassword1", "new_password": "newpassword1"},
        )
        csrf_post(client, "/logout")
        csrf_post(client, "/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        with client.session_transaction() as sess:
            assert "user_id" in sess, (
                "the demo password must still be demo123 after a locked change attempt (AC10)"
            )

    def test_demo_budget_update_allowed(self, client):
        _login_as_demo(client)
        resp = csrf_post(
            client, "/profile/budget", data={"budget": "500"}, follow_redirects=True
        )
        assert (
            b"The demo account's profile can't be changed" not in resp.data
        ), "POST /profile/budget must stay unlocked for the demo user (AC11, FR3.3)"

    def test_demo_add_expense_allowed(self, client):
        # SPEC GAP: exact /expenses/add field names aren't given in Spec 10;
        # this only confirms the demo lock doesn't apply to this route.
        _login_as_demo(client)
        resp = csrf_post(client, "/expenses/add", data={}, follow_redirects=True)
        assert b"The demo account's profile can't be changed" not in resp.data

    def test_demo_edit_expense_allowed(self, client):
        # SPEC GAP: exact /expenses/<id>/edit field names aren't given in
        # Spec 10; this only confirms the demo lock doesn't apply.
        _login_as_demo(client)
        conn = db.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = "
            "(SELECT id FROM users WHERE email = ?) LIMIT 1",
            (DEMO_EMAIL,),
        ).fetchone()
        assert row is not None
        resp = csrf_post(
            client, f"/expenses/{row['id']}/edit", data={}, follow_redirects=True
        )
        assert b"The demo account's profile can't be changed" not in resp.data

    def test_demo_delete_expense_allowed(self, client):
        _login_as_demo(client)
        conn = db.get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = "
            "(SELECT id FROM users WHERE email = ?) LIMIT 1",
            (DEMO_EMAIL,),
        ).fetchone()
        assert row is not None, "seed_db() must seed at least one demo expense"
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        csrf_post(client, f"/expenses/{row['id']}/delete")
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        assert after == before - 1, "the demo user must be allowed to delete expenses (AC11, FR3.3)"

    def test_demo_banner_shown_for_demo_user(self, client):
        _login_as_demo(client)
        resp = client.get("/profile")
        assert (
            b"You're using the shared demo account. Profile settings are "
            b"locked" in resp.data
        ), "AC12: the demo banner text must be present for the demo user"
        with flask_app.test_request_context():
            register_url = url_for("register")
        assert register_url.encode() in resp.data, "AC12: the banner must link to /register"

    def test_demo_banner_absent_for_regular_user(self, auth_client):
        resp = auth_client.get("/profile")
        assert b"You're using the shared demo account" not in resp.data, (
            "AC12: non-demo users must never see the demo banner"
        )

    def test_regular_user_can_change_name(self, auth_client):
        # AC13: the profile form always submits name and email together, so
        # a name change posts the new name with the user's current email.
        resp = csrf_post(
            auth_client,
            "/profile",
            data={"name": "New Name", "email": "test@example.com"},
            follow_redirects=True,
        )
        assert b"Profile updated." in resp.data, "AC13: a non-demo name change should succeed"
        conn = db.get_db()
        row = conn.execute(
            "SELECT name FROM users WHERE email = ?", ("test@example.com",)
        ).fetchone()
        assert row["name"] == "New Name"


# ------------------------------------------------------------------ #
# FR4 — Secret key & session cookies (AC14, AC15)
# ------------------------------------------------------------------ #
class TestSecretKeyAndSessionCookies:
    def test_missing_secret_key_in_production_raises_runtime_error(self, monkeypatch, tmp_path):
        reload_db = str(tmp_path / "reload-ac14.db")
        monkeypatch.setenv("SPENDLY_DB", reload_db)
        monkeypatch.setattr(db, "DB_PATH", reload_db)
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        try:
            with pytest.raises(RuntimeError, match="SECRET_KEY must be set in production"):
                importlib.reload(app_module)
        finally:
            monkeypatch.undo()
            importlib.reload(app_module)

    def test_cookie_flags_local_default(self, monkeypatch, tmp_path):
        reload_db = str(tmp_path / "reload-ac15a.db")
        monkeypatch.setenv("SPENDLY_DB", reload_db)
        monkeypatch.setattr(db, "DB_PATH", reload_db)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        try:
            importlib.reload(app_module)
            cfg = app_module.app.config
            assert cfg["SESSION_COOKIE_HTTPONLY"] is True, "AC15"
            assert cfg["SESSION_COOKIE_SAMESITE"] == "Lax", "AC15"
            assert cfg["SESSION_COOKIE_SECURE"] is False, (
                "AC15: SESSION_COOKIE_SECURE must be False when RAILWAY_ENVIRONMENT is unset"
            )
        finally:
            monkeypatch.undo()
            importlib.reload(app_module)

    def test_cookie_secure_flag_true_in_production(self, monkeypatch, tmp_path):
        reload_db = str(tmp_path / "reload-ac15b.db")
        monkeypatch.setenv("SPENDLY_DB", reload_db)
        monkeypatch.setattr(db, "DB_PATH", reload_db)
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "test-secret-key")
        try:
            importlib.reload(app_module)
            assert app_module.app.config["SESSION_COOKIE_SECURE"] is True, (
                "AC15: SESSION_COOKIE_SECURE must be True when RAILWAY_ENVIRONMENT is set"
            )
        finally:
            monkeypatch.undo()
            importlib.reload(app_module)


# ------------------------------------------------------------------ #
# FR4.3 — session reset & permanence (AC16, AC17)
# ------------------------------------------------------------------ #
class TestSessionResetAndPermanence:
    def test_register_sets_session_permanent(self, client):
        csrf_post(
            client,
            "/register",
            data={"name": "Perm User", "email": "perm@example.com", "password": "testpass1"},
        )
        with client.session_transaction() as sess:
            assert sess.permanent is True, "register must set session.permanent = True (AC16, FR4.3)"

    def test_login_sets_session_permanent(self, client):
        csrf_post(
            client,
            "/register",
            data={"name": "Perm User 2", "email": "perm2@example.com", "password": "testpass1"},
        )
        csrf_post(client, "/logout")
        csrf_post(client, "/login", data={"email": "perm2@example.com", "password": "testpass1"})
        with client.session_transaction() as sess:
            assert sess.permanent is True

    def test_register_clears_any_preexisting_session_data(self, client):
        with client.session_transaction() as sess:
            sess["leftover"] = "pre-register-value"
        csrf_post(
            client,
            "/register",
            data={"name": "Fresh User", "email": "fresh@example.com", "password": "testpass1"},
        )
        with client.session_transaction() as sess:
            assert "leftover" not in sess, "register must session.clear() before login (AC17, FR4.3)"
            assert "user_id" in sess

    def test_login_clears_any_preexisting_session_data(self, client):
        csrf_post(
            client,
            "/register",
            data={"name": "Fresh User 2", "email": "fresh2@example.com", "password": "testpass1"},
        )
        csrf_post(client, "/logout")
        with client.session_transaction() as sess:
            sess["leftover"] = "pre-login-value"
        csrf_post(client, "/login", data={"email": "fresh2@example.com", "password": "testpass1"})
        with client.session_transaction() as sess:
            assert "leftover" not in sess, "login must session.clear() before setting user_id (AC17)"
            assert "user_id" in sess


# ------------------------------------------------------------------ #
# FR5 — One "today", in IST (AC18, AC19, AC19b)
# ------------------------------------------------------------------ #
class TestISTDates:
    def test_signup_date_shown_in_ist_not_utc(self, auth_client, monkeypatch):
        # Approved exception FR8.3: direct UPDATE of created_at + monkeypatch
        # app.today_ist (not db.today_ist).
        conn = db.get_db()
        conn.execute(
            "UPDATE users SET created_at = ? WHERE email = ?",
            ("2026-10-01 20:00:00", "test@example.com"),
        )
        conn.commit()
        monkeypatch.setattr(app_module, "today_ist", lambda: date(2026, 10, 2))
        resp = auth_client.get("/profile")
        assert (
            "Showing 2 Oct 2026 – 2 Oct 2026".encode("utf-8") in resp.data
        ), "a signup at 20:00 UTC on 1 Oct must be shown as 2 Oct in IST (AC18, FR5.3)"

    def test_local_time_converts_utc_to_ist(self):
        assert app_module.local_time("2026-10-01 20:00:00") == "2 Oct 2026, 1:30 AM", (
            "local_time() must convert UTC to IST regardless of the server's own "
            "timezone (AC19, FR5.4)"
        )

    def test_profile_showing_line_follows_ist_month_rollover(self, auth_client, monkeypatch):
        monkeypatch.setattr(app_module, "today_ist", lambda: date(2026, 10, 3))
        resp = auth_client.get("/profile")
        html = resp.data.decode("utf-8")
        assert re.search(r"Showing[^<]*3 Oct 2026", html), (
            "the default 'This month' range must end on 3 Oct 2026 when "
            "today_ist() returns 3 Oct 2026 (AC19b)"
        )


# ------------------------------------------------------------------ #
# FR6/FR10 — test isolation & the new index (AC21, AC23)
# ------------------------------------------------------------------ #
class TestIndexAndIsolation:
    def test_db_path_is_never_the_real_database_file(self, client):
        assert db.DB_PATH != "database.db", (
            "tests must never point at the real database.db (AC21, FR6.3)"
        )

    def test_expenses_table_has_user_date_index(self, client):
        conn = db.get_db()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'expenses'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert "idx_expenses_user_date" in names, (
            "init_db() must create idx_expenses_user_date on expenses(user_id, date) (AC23, FR10.1)"
        )


# ------------------------------------------------------------------ #
# FR9 — CI workflow file (AC22, automatable part only)
# ------------------------------------------------------------------ #
class TestCIWorkflow:
    def test_ci_workflow_file_exists_and_targets_push_and_pull_request(self):
        workflow = REPO_ROOT / ".github" / "workflows" / "tests.yml"
        assert workflow.exists(), ".github/workflows/tests.yml must exist (AC22, FR9.1)"
        text = workflow.read_text()
        assert "push" in text and "pull_request" in text, (
            "the workflow must trigger on both push and pull_request (AC22, FR9.1)"
        )


# ------------------------------------------------------------------ #
# FR10 — docs updated (AC25)
# ------------------------------------------------------------------ #
class TestDocsUpdatedForSpec10:
    def test_spec_03_logout_description_marked_superseded(self):
        text = (REPO_ROOT / ".claude" / "specs" / "03-login-and-logout.md").read_text()
        assert "superseded by Spec 10" in text, (
            "Spec 03's GET /logout / session.pop lines must be marked superseded (AC25, FR10.3)"
        )

    def test_test_writer_agent_documents_csrf_post(self):
        text = (REPO_ROOT / ".claude" / "agents" / "spendly-test-writer.md").read_text()
        assert "csrf_post" in text, "spendly-test-writer.md must mention the csrf_post helper (AC25)"

    def test_progress_md_lists_post_logout_route(self):
        text = (REPO_ROOT / ".claude" / "PROGRESS.md").read_text()
        assert "POST /logout" in text, "PROGRESS.md's route table must list POST /logout (AC25, FR10.4)"
