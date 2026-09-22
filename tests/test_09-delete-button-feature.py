"""Tests for Spec 09 — Delete expense (button + confirm popup).

Written from `.claude/specs/09-delete-button-feature.md` only — app.py and
database/db.py's implementations were never opened. Setup uses
`database.db.insert_expense` / `database.db.get_db()` against the throwaway
DB provided by `tests/conftest.py`'s `client` / `auth_client` fixtures,
reading only the `users` and `expenses` columns (`id`, `email`, `user_id`,
`amount`, `category`, `description`, `date`) that the spec's own Manual
Verification Guide queries directly (see spec lines ~300, ~391).

JS-only behaviour (popup open/close interactions, the red fade animation,
prefers-reduced-motion handling) is not exercised here — the Flask test
client cannot run JavaScript. See the final report for the full list of
SPEC GAP items.
"""

import inspect
from urllib.parse import parse_qs, urlparse

import pytest

from app import app as flask_app
from database import db


# --------------------------------------------------------------------- #
# Setup helpers (spec-driven, not implementation-driven)
# --------------------------------------------------------------------- #

def _user_id(email):
    """Look up a user's id the same way the spec's own Manual Verification
    Guide does (`SELECT id FROM users WHERE email = ?`)."""
    conn = db.get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()
    assert row is not None, f"expected a user row for {email}"
    return row["id"] if hasattr(row, "keys") else row[0]


def _insert_expense(user_id, amount, category, description, date):
    """Insert an expense via database.db.insert_expense for test setup.

    The spec names `db.insert_expense` as an existing interface but does not
    state its parameter order or return value (that's Step 7's spec, not
    this one) — see SPEC GAP in the final report. We introspect the
    signature to call it with keyword args when possible, and otherwise
    fall back to the (user_id, amount, category, description, date) order
    implied by the spec's own field list, then look the new row's id up
    directly from the `expenses` table (a column set the spec's Manual
    Verification Guide itself queries).
    """
    candidate_kwargs = {
        "user_id": user_id,
        "amount": amount,
        "category": category,
        "description": description,
        "date": date,
    }
    params = inspect.signature(db.insert_expense).parameters
    if set(candidate_kwargs) <= set(params):
        db.insert_expense(**candidate_kwargs)
    else:
        db.insert_expense(user_id, amount, category, description, date)

    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "expected the inserted expense to be findable by user_id"
    return row["id"] if hasattr(row, "keys") else row[0]


def _expense_count(expense_id):
    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()
    return row[0]


def _register_and_login(email):
    """A second, independent logged-in client on the same throwaway DB
    (used for the "own expenses only" ownership check, AC14)."""
    second = flask_app.test_client()
    second.post(
        "/register",
        data={"name": "Second User", "email": email, "password": "testpass1"},
    )
    second.post("/login", data={"email": email, "password": "testpass1"})
    return second


# --------------------------------------------------------------------- #
# POST /expenses/<id>/delete — happy path (FR12, FR14, AC8, AC9)
# --------------------------------------------------------------------- #

class TestDeleteHappyPath:
    def test_delete_own_expense_redirects_and_keeps_range_filter(self, auth_client):
        # Spec section 10, minimum test 1.
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 100, "Food", "Tea", "2026-09-22")

        response = auth_client.post(
            f"/expenses/{expense_id}/delete",
            data={"range": "last_3_months"},
        )

        assert response.status_code == 302, "expected a redirect on a successful delete (FR14)"
        location = urlparse(response.headers["Location"])
        assert location.path == "/profile", "AC8: should redirect back to /profile"
        assert parse_qs(location.query) == {"range": ["last_3_months"]}, (
            "AC8/AC9: the range filter that was active must be carried through unchanged"
        )

    def test_delete_success_shows_toast_and_removes_row_from_db(self, auth_client):
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 250, "Transport", "", "2026-09-22")

        response = auth_client.post(
            f"/expenses/{expense_id}/delete",
            data={"range": "last_3_months"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Expense deleted." in response.data, (
            "FR14/AC8: expected the success flash 'Expense deleted.' on the next /profile load"
        )
        assert _expense_count(expense_id) == 0, "AC8: the row must be gone from the expenses table"

    def test_delete_keeps_custom_start_and_end_filters(self, auth_client):
        # AC9: a custom start/end range must both be preserved (no `range` key
        # is sent in this case, mirroring how the budget form only sends the
        # filter keys that are actually set — FR14).
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 40, "Other", "filter-test", "2026-09-22")

        response = auth_client.post(
            f"/expenses/{expense_id}/delete",
            data={"start": "2026-09-01", "end": "2026-09-30"},
        )

        assert response.status_code == 302
        location = urlparse(response.headers["Location"])
        assert location.path == "/profile"
        query = parse_qs(location.query)
        assert query.get("start") == ["2026-09-01"], "AC9: start must be preserved"
        assert query.get("end") == ["2026-09-30"], "AC9: end must be preserved"
        assert "range" not in query, "FR14: only non-empty keys are carried through"

    def test_delete_reduces_total_spent_and_transaction_count(self, auth_client):
        # AC10 — checked at the DB level (sum/count of the user's expenses),
        # since the spec doesn't give the exact markup/selector for the
        # Total Spent / Transactions tiles (SPEC GAP, see final report).
        user_id = _user_id("test@example.com")
        _insert_expense(user_id, 100, "Food", "Tea", "2026-09-22")
        deleted_id = _insert_expense(user_id, 250, "Transport", "", "2026-09-22")

        def totals():
            conn = db.get_db()
            try:
                row = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
            finally:
                conn.close()
            return row[0], row[1]

        count_before, sum_before = totals()
        auth_client.post(f"/expenses/{deleted_id}/delete", data={"range": "this_month"})
        count_after, sum_after = totals()

        assert count_after == count_before - 1, "AC10: Transactions count must drop by one"
        assert sum_after == pytest.approx(sum_before - 250), "AC10: Total Spent must drop by the deleted amount"

    def test_delete_last_expense_shows_empty_state(self, auth_client):
        # AC16
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 40, "Other", "only one", "2026-09-22")

        response = auth_client.post(
            f"/expenses/{expense_id}/delete",
            data={"range": "this_month"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"You haven&#39;t logged any expenses yet." in response.data or (
            b"You haven't logged any expenses yet." in response.data
        ), "AC16: expected the empty-state message after deleting the only expense"


# --------------------------------------------------------------------- #
# POST /expenses/<id>/delete — auth guard, ownership, not-found (FR10-13)
# --------------------------------------------------------------------- #

class TestDeleteGuardsAndErrors:
    def test_delete_same_expense_twice_returns_404_second_time(self, auth_client):
        # Spec section 10, minimum test 2 / AC15.
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 40, "Other", "twice", "2026-09-22")

        first = auth_client.post(f"/expenses/{expense_id}/delete", data={"range": "this_month"})
        second = auth_client.post(f"/expenses/{expense_id}/delete", data={"range": "this_month"})

        assert first.status_code == 302, "the first delete should succeed"
        assert second.status_code == 404, "AC15: deleting the same id twice returns 404 the second time"

    def test_get_to_delete_route_returns_405(self, auth_client):
        # Spec section 10, minimum test 3 / AC12 / FR10.
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 40, "Other", "get-test", "2026-09-22")

        response = auth_client.get(f"/expenses/{expense_id}/delete")

        assert response.status_code == 405, "FR10: a GET must get Flask's automatic 405"
        assert _expense_count(expense_id) == 1, "AC12: nothing should be deleted on a GET"

    def test_delete_route_with_non_int_id_returns_404(self, auth_client):
        # APIs table: `/expenses/<non-int>/delete` → 404 (Flask's int converter).
        response = auth_client.post("/expenses/not-an-id/delete", data={"range": "this_month"})
        assert response.status_code == 404

    def test_signed_out_post_redirects_to_login_and_deletes_nothing(self, client):
        # Spec section 10, minimum test 4 / AC11 / FR11.
        # Register signs the client in (Step 2), so log back out afterward —
        # the spec's own AC11 manual step starts with "Click Sign out" — to
        # get a genuinely signed-out client that still owns the expense.
        client.post(
            "/register",
            data={"name": "Owner", "email": "owner@example.com", "password": "testpass1"},
        )
        client.get("/logout")
        owner_id = _user_id("owner@example.com")
        expense_id = _insert_expense(owner_id, 40, "Other", "signed-out-test", "2026-09-22")

        response = client.post(f"/expenses/{expense_id}/delete", data={"range": "this_month"})

        assert response.status_code == 302, "FR11: signed-out delete must redirect"
        location = urlparse(response.headers["Location"])
        assert location.path == "/login", "AC11: must redirect to /login"
        assert _expense_count(expense_id) == 1, "AC11: nothing should be deleted"

        followed = client.get(response.headers["Location"])
        assert b"Please sign in to delete an expense." in followed.data, (
            "FR11: expected the exact error flash text"
        )

    def test_delete_nonexistent_id_returns_404(self, auth_client):
        # Spec section 10, minimum test (also AC13).
        response = auth_client.post("/expenses/999999/delete", data={"range": "this_month"})
        assert response.status_code == 404

    def test_delete_another_users_expense_returns_404_and_row_survives(self, auth_client):
        # Spec section 10, minimum test 5 / AC14.
        second = _register_and_login("userb@example.com")
        other_user_id = _user_id("userb@example.com")
        other_expense_id = _insert_expense(other_user_id, 500, "Other", "not yours", "2026-09-22")

        response = auth_client.post(
            f"/expenses/{other_expense_id}/delete", data={"range": "this_month"}
        )

        assert response.status_code == 404, "AC14: deleting someone else's expense returns 404"
        assert _expense_count(other_expense_id) == 1, "AC14: the other user's row must be untouched"
        second.get("/profile")  # sanity: the second client's session still works


# --------------------------------------------------------------------- #
# database.db.delete_expense — direct unit coverage of the new helper
# --------------------------------------------------------------------- #

class TestDeleteExpenseDbHelper:
    def test_delete_expense_returns_true_and_removes_own_row(self, client):
        client.post(
            "/register",
            data={"name": "Owner", "email": "owner2@example.com", "password": "testpass1"},
        )
        user_id = _user_id("owner2@example.com")
        expense_id = _insert_expense(user_id, 10, "Other", "helper-test", "2026-09-22")

        result = db.delete_expense(user_id, expense_id)

        assert result is True, "FR12: delete_expense must return True when exactly one row is deleted"
        assert _expense_count(expense_id) == 0

    def test_delete_expense_returns_false_for_wrong_user(self, client):
        client.post(
            "/register",
            data={"name": "Owner", "email": "owner3@example.com", "password": "testpass1"},
        )
        client.post(
            "/register",
            data={"name": "Intruder", "email": "intruder@example.com", "password": "testpass1"},
        )
        owner_id = _user_id("owner3@example.com")
        intruder_id = _user_id("intruder@example.com")
        expense_id = _insert_expense(owner_id, 10, "Other", "helper-test", "2026-09-22")

        result = db.delete_expense(intruder_id, expense_id)

        assert result is False, "FR12/FR13: wrong user_id must not delete the row"
        assert _expense_count(expense_id) == 1

    def test_delete_expense_returns_false_for_missing_id(self, client):
        client.post(
            "/register",
            data={"name": "Owner", "email": "owner4@example.com", "password": "testpass1"},
        )
        user_id = _user_id("owner4@example.com")

        result = db.delete_expense(user_id, 999999)

        assert result is False, "FR13: a nonexistent id must return False"


# --------------------------------------------------------------------- #
# /profile HTML — trash button + popup markup (FR1, FR2, FR4, FR5, AC1-3)
# --------------------------------------------------------------------- #

class TestProfileMarkup:
    def test_row_has_aria_label_and_data_action(self, auth_client):
        # Spec section 10, minimum test 6 / AC1 / AC2.
        user_id = _user_id("test@example.com")
        expense_id = _insert_expense(user_id, 100, "Food", "Tea", "2026-09-22")

        response = auth_client.get("/profile")
        html = response.data.decode()

        assert 'aria-label="Delete expense"' in html, "AC1: every row's button needs this aria-label"
        assert f'data-action="/expenses/{expense_id}/delete"' in html, (
            "AC2: data-action must point at this row's delete URL"
        )
        assert 'id="delete-expense-modal"' in html, "AC3: the shared popup must be present"

    def test_row_data_attributes_match_row_values(self, auth_client):
        # AC2
        user_id = _user_id("test@example.com")
        _insert_expense(user_id, 100, "Food", "Tea", "2026-09-22")

        html = auth_client.get("/profile").data.decode()

        assert 'data-date="2026-09-22"' in html
        assert 'data-description="Tea"' in html
        assert 'data-category="Food"' in html
        assert 'data-amount="' in html and "100" in html

    def test_row_data_description_defaults_to_dash_when_empty(self, auth_client):
        # AC2: "data-description is — when the description is empty."
        user_id = _user_id("test@example.com")
        _insert_expense(user_id, 250, "Transport", "", "2026-09-22")

        html = auth_client.get("/profile").data.decode()

        assert "data-description=" in html
        assert "—" in html or "&mdash;" in html or "—" in html, (
            "AC2: an empty description must render as the — placeholder"
        )

    def test_delete_modal_absent_when_no_expenses(self, auth_client):
        # AC3: "When Recent Transactions is empty, the popup isn't rendered."
        html = auth_client.get("/profile").data.decode()

        assert "delete-expense-modal" not in html, (
            "AC3: the popup must not be rendered when there are no expenses"
        )
        assert "You haven't logged any expenses yet." in html or (
            "You haven&#39;t logged any expenses yet." in html
        )

    def test_delete_modal_contains_expected_static_content(self, auth_client):
        # FR5 / AC3: heading, "can't be undone" line, Cancel + Delete buttons.
        user_id = _user_id("test@example.com")
        _insert_expense(user_id, 100, "Food", "Tea", "2026-09-22")

        html = auth_client.get("/profile").data.decode()

        assert html.count('id="delete-expense-modal"') == 1, "AC3: exactly one popup"
        assert "Delete this expense?" in html, "FR5: expected heading"
        assert "This can&#39;t be undone." in html or "This can't be undone." in html
        assert 'method="post"' in html, "FR5: the popup's form must POST"
        assert "Cancel" in html, "FR5: expected a Cancel button"
        assert "Delete" in html, "FR5: expected a Delete submit button"

    def test_delete_modal_description_attribute_is_html_escaped(self, auth_client):
        # AC17 (server-rendered half): the raw HTML attribute must be escaped
        # so a browser never parses it as markup; the JS textContent behaviour
        # itself is not exercisable via the Flask test client (see report).
        user_id = _user_id("test@example.com")
        _insert_expense(user_id, 40, "Other", "<b>x</b>", "2026-09-22")

        html = auth_client.get("/profile").data.decode()

        assert 'data-description="<b>x</b>"' not in html, (
            "AC17: the raw markup must not appear unescaped in a data attribute"
        )
        assert "&lt;b&gt;x&lt;/b&gt;" in html, (
            "AC17: Jinja auto-escaping should render the literal characters, not a <b> tag"
        )
