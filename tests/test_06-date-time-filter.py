"""Tests for the /profile date-range filter (spec 06), read together with
spec 06b (profile-dashboard-restructure) wherever 06 is marked
"[Superseded by spec 06b.]" — those markers, not the "Originally:" text
that follows them, define the current expected behaviour tested here.

These tests never read app.py or database/db.py. Expense rows are inserted
directly with parameterised SQL against the throwaway file conftest.py
points database.db.DB_PATH at (via the client/auth_client fixtures) — the
exact `expenses` and `users` column names used below (user_id, amount,
category, date, description / id, email, monthly_budget, created_at) are
taken verbatim from spec text (06b's own manual-verification SQL and 06's
APIs section), not from reading the implementation.
"""

import html as html_module
import re
import sqlite3
from datetime import date, timedelta

import pytest

from app import app as flask_app
from database import db as db_module

# ------------------------------------------------------------------ #
# Test-only DB + formatting helpers (not implementation code)         #
# ------------------------------------------------------------------ #


def _get_conn():
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_id(email="test@example.com"):
    conn = _get_conn()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    assert row is not None, f"no user row found for {email}"
    return row[0]


def get_monthly_budget(email="test@example.com"):
    conn = _get_conn()
    row = conn.execute(
        "SELECT monthly_budget FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row[0]


def add_expense(user_id, amount, category, expense_date, description="test expense"):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


def fmt(d):
    """spec's `%d %b %Y` date text with no leading zero on the day, e.g.
    '1 Jul 2026', '19 Sep 2026' (see spec 06 FR4 and 06b FR9 examples)."""
    return f"{d.day} {d.strftime('%b %Y')}"


def money(amount):
    """Indian digit grouping with 2 decimals and a rupee prefix, per spec 06
    FR11: '₹89.99', '₹1,000.00', '₹10,000.00', '₹1,00,000.00',
    '₹12,34,567.50', '₹1,23,45,678.00'."""
    s = f"{abs(amount):.2f}"
    int_part, dec_part = s.split(".")
    if len(int_part) <= 3:
        grouped = int_part
    else:
        last3, rest = int_part[-3:], int_part[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{grouped}.{dec_part}"


def first_of_month(d):
    return d.replace(day=1)


def last_of_previous_month(d):
    return first_of_month(d) - timedelta(days=1)


def first_of_previous_month(d):
    return first_of_month(last_of_previous_month(d))


def first_of_month_n_back(d, n):
    month, year = d.month - n, d.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def has_control_with_value(html, value):
    """True if a `name="range" value="<value>"` control exists, in either
    attribute order (spec 06 AC2)."""
    pattern = (
        rf'(?:name="range"[^>]*value="{re.escape(value)}"'
        rf'|value="{re.escape(value)}"[^>]*name="range")'
    )
    return re.search(pattern, html) is not None


# Jinja autoescapes template variables/text, so a literal apostrophe or
# quote in an expected string (e.g. "there's", "haven't") comes back from
# the response body as an HTML entity ("there&#39;s"). Every assertion in
# this file reads the page through html_of(), which unescapes the decoded
# body, so a bare `resp.data.decode()` is never used directly in a test.
def html_of(resp):
    return html_module.unescape(resp.data.decode())


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #


class TestAuthGuard:
    def test_profile_get_requires_login_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "logged-out /profile must redirect, not 200"
        assert "/login" in resp.headers["Location"]

    def test_budget_post_requires_login(self, client):
        resp = client.post(
            "/profile/budget",
            data={"monthly_budget": "1000", "range": "this_month", "start": "", "end": ""},
        )
        assert resp.status_code == 302, "logged-out POST /profile/budget must redirect"
        assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# Filter bar rendering (AC1, AC2, AC18, AC19)                         #
# ------------------------------------------------------------------ #


class TestFilterBarRendering:
    def test_profile_default_range_returns_200_and_this_month_active(self, auth_client):
        resp = auth_client.get("/profile")
        html = html_of(resp)
        assert resp.status_code == 200
        idx = html.find('aria-pressed="true"')
        assert idx != -1, "expected one active preset carrying aria-pressed=true"
        window = html[max(0, idx - 150) : idx + 150]
        assert "This month" in window, "the default active preset must be This month"

    def test_profile_get_contains_filter_bar_controls(self, auth_client):
        resp = auth_client.get("/profile")
        html = html_of(resp)
        assert resp.status_code == 200
        # The HTML `method` attribute is case-insensitive (the spec's own
        # prose example happens to write it lowercase, but real markup may
        # legitimately emit method="GET"), so match case-insensitively —
        # the functional requirement is two separate GET forms, not a
        # specific casing of the attribute value.
        get_forms = re.findall(r'<form[^>]+method="get"', html, re.I)
        assert len(get_forms) >= 2, (
            "spec 06 FR1: two separate GET forms so Enter in a date box "
            "submits custom range, not the first preset button"
        )
        for value in ("this_month", "last_month", "last_3_months", "all_time"):
            assert has_control_with_value(html, value), f"missing preset control range={value}"
        assert 'type="date"' in html
        assert 'name="start"' in html
        assert 'name="end"' in html
        assert has_control_with_value(html, "custom"), "missing hidden range=custom field"
        assert "Apply" in html

    @pytest.mark.parametrize("path", ["/", "/login", "/register", "/terms", "/privacy"])
    def test_filter_controls_absent_from_other_pages(self, client, path):
        resp = client.get(path)
        html = html_of(resp)
        assert 'name="range"' not in html, (
            f"spec 06 AC18: the filter bar must appear only on /profile, "
            f"not on {path}"
        )

    def test_range_pill_shows_active_range_name(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert '<span class="range-pill">This month</span>' in html

        html = html_of(auth_client.get("/profile?range=last_3_months"))
        assert '<span class="range-pill">Last 3 months</span>' in html

        d = date.today().isoformat()
        html = html_of(auth_client.get(f"/profile?range=custom&start={d}&end={d}"))
        assert '<span class="range-pill">Custom range</span>' in html

        html = html_of(auth_client.get("/profile?range=bogus"))
        assert '<span class="range-pill">This month</span>' in html, (
            "AC19: an error fallback must show the This month pill"
        )


# ------------------------------------------------------------------ #
# Preset and custom range filtering (AC3-AC8)                         #
# ------------------------------------------------------------------ #


class TestPresetRanges:
    def test_last_month_range_includes_only_previous_calendar_month(self, auth_client):
        user_id = get_user_id()
        today = date.today()
        prev_start = first_of_previous_month(today)
        prev_end = last_of_previous_month(today)
        add_expense(user_id, 100, "Food", prev_start.isoformat(), "PREV-START")
        add_expense(user_id, 110, "Food", prev_end.isoformat(), "PREV-END")
        add_expense(user_id, 120, "Food", today.isoformat(), "THIS-MONTH")
        add_expense(user_id, 130, "Food", (prev_start - timedelta(days=1)).isoformat(), "BEFORE-PREV")

        html = html_of(auth_client.get("/profile?range=last_month"))
        assert "PREV-START" in html
        assert "PREV-END" in html
        assert "THIS-MONTH" not in html
        assert "BEFORE-PREV" not in html
        assert '<span class="range-pill">Last month</span>' in html

    def test_last_3_months_range_includes_expenses_from_two_months_back(self, auth_client):
        user_id = get_user_id()
        today = date.today()
        range_start = first_of_month_n_back(today, 2)
        add_expense(user_id, 100, "Food", range_start.isoformat(), "IN-RANGE-START")
        add_expense(user_id, 110, "Food", today.isoformat(), "IN-RANGE-TODAY")
        add_expense(user_id, 120, "Food", (range_start - timedelta(days=1)).isoformat(), "BEFORE-RANGE")

        html = html_of(auth_client.get("/profile?range=last_3_months"))
        assert "IN-RANGE-START" in html
        assert "IN-RANGE-TODAY" in html
        assert "BEFORE-RANGE" not in html

    def test_all_time_range_includes_expenses_before_signup(self, auth_client):
        user_id = get_user_id()
        add_expense(user_id, 100, "Food", "2000-01-01", "ANCIENT")
        add_expense(user_id, 110, "Food", date.today().isoformat(), "TODAY-EXP")

        html = html_of(auth_client.get("/profile?range=all_time"))
        assert "ANCIENT" in html, "AC5: all_time must include expenses dated before signup"
        assert "TODAY-EXP" in html
        assert '<span class="range-pill">All time</span>' in html

    def test_start_end_params_ignored_when_range_is_a_preset(self, auth_client):
        user_id = get_user_id()
        today = date.today()
        prev_start = first_of_previous_month(today)
        add_expense(user_id, 77, "Food", prev_start.isoformat(), "PREV-MONTH-ITEM")

        html = html_of(
            auth_client.get("/profile?range=last_month&start=2000-01-01&end=2000-01-02")
        )
        assert "PREV-MONTH-ITEM" in html, "the preset must win; start/end are ignored"
        assert '<span class="range-pill">Last month</span>' in html

    def test_extra_unknown_query_params_are_ignored(self, auth_client):
        resp = auth_client.get("/profile?range=this_month&foo=bar&baz=1")
        assert resp.status_code == 200


class TestCustomRange:
    def test_custom_range_is_inclusive_on_both_ends(self, auth_client):
        user_id = get_user_id()
        start = date.today() - timedelta(days=10)
        end = date.today() - timedelta(days=5)
        add_expense(user_id, 50, "Food", start.isoformat(), "IN-START")
        add_expense(user_id, 60, "Food", end.isoformat(), "IN-END")
        add_expense(user_id, 70, "Food", (start - timedelta(days=1)).isoformat(), "OUT-BEFORE")
        add_expense(user_id, 80, "Food", (end + timedelta(days=1)).isoformat(), "OUT-AFTER")

        html = html_of(auth_client.get(f"/profile?range=custom&start={start}&end={end}"))
        assert "IN-START" in html
        assert "IN-END" in html
        assert "OUT-BEFORE" not in html
        assert "OUT-AFTER" not in html

    def test_custom_range_single_day_is_valid(self, auth_client):
        user_id = get_user_id()
        d = date.today() - timedelta(days=5)
        add_expense(user_id, 33, "Food", d.isoformat(), "SINGLE-DAY")

        html = html_of(auth_client.get(f"/profile?range=custom&start={d}&end={d}"))
        assert "SINGLE-DAY" in html
        assert '<span class="range-pill">Custom range</span>' in html

    def test_recent_transactions_shows_at_most_5_newest_first(self, auth_client):
        user_id = get_user_id()
        base = date.today() - timedelta(days=20)
        dates = [base + timedelta(days=i) for i in range(7)]
        for i, d in enumerate(dates):
            add_expense(user_id, 10 + i, "Food", d.isoformat(), f"TXN-{i}")

        html = html_of(
            auth_client.get(f"/profile?range=custom&start={dates[0]}&end={dates[-1]}")
        )
        present = [f"TXN-{i}" for i in range(7) if f"TXN-{i}" in html]
        assert len(present) == 5, f"expected exactly 5 rows, found {present}"
        for i in range(2, 7):
            assert f"TXN-{i}" in html, "the 5 newest expenses must be shown"
        for i in range(0, 2):
            assert f"TXN-{i}" not in html, "older expenses beyond the 5-row cap must not show"
        # newest first
        positions = [html.index(f"TXN-{i}") for i in range(6, 1, -1)]
        assert positions == sorted(positions), "Recent Transactions must list newest first"

    def test_other_users_expenses_never_appear_in_filtered_figures(self, auth_client):
        # POST /register logs the new user in, which would silently swap
        # auth_client's own session to the second account. Register the
        # second user through an independent test client (same throwaway
        # DB, separate cookie jar) so auth_client stays logged in as
        # test@example.com throughout.
        other_client = flask_app.test_client()
        other_client.post(
            "/register",
            data={"name": "Other", "email": "other@example.com", "password": "testpass1"},
        )
        other_id = get_user_id("other@example.com")
        add_expense(other_id, 5000, "Food", date.today().isoformat(), "OTHER-USER-EXPENSE")
        my_id = get_user_id("test@example.com")
        add_expense(my_id, 25, "Food", date.today().isoformat(), "MY-EXPENSE")

        html = html_of(auth_client.get("/profile?range=all_time"))
        assert "MY-EXPENSE" in html
        assert "OTHER-USER-EXPENSE" not in html, "AC8: another user's expenses must never appear"


# ------------------------------------------------------------------ #
# Validation errors (AC9, APIs error table)                           #
# ------------------------------------------------------------------ #


class TestValidationErrors:
    @pytest.mark.parametrize(
        "query,expected_message",
        [
            ("range=bogus", "Unknown date range."),
            ("range=custom&start=2026-09-01", "Please choose both a start and an end date."),
            ("range=custom&start=&end=", "Please choose both a start and an end date."),
            ("range=custom&start=abc&end=2026-09-10", "Please enter valid dates."),
            ("range=custom&start=2026-02-30&end=2026-03-01", "Please enter valid dates."),
            (
                "range=custom&start=2026-09-10&end=2026-09-01",
                "Start date must be on or before end date.",
            ),
        ],
    )
    def test_filter_errors_return_200_show_message_and_fall_back_to_this_month(
        self, auth_client, query, expected_message
    ):
        resp = auth_client.get(f"/profile?{query}")
        html = html_of(resp)
        assert resp.status_code == 200, "invalid filter input must never produce a 4xx"
        assert expected_message in html
        assert '<span class="range-pill">This month</span>' in html

    def test_future_start_date_shows_error_and_falls_back(self, auth_client):
        future = (date.today() + timedelta(days=5)).isoformat()
        far_future = (date.today() + timedelta(days=10)).isoformat()
        html = html_of(
            auth_client.get(f"/profile?range=custom&start={future}&end={far_future}")
        )
        assert "That date range is in the future." in html
        assert '<span class="range-pill">This month</span>' in html

    def test_end_in_future_start_in_past_clamps_to_today_without_error(self, auth_client):
        start = date.today() - timedelta(days=10)
        end = date.today() + timedelta(days=50)
        html = html_of(auth_client.get(f"/profile?range=custom&start={start}&end={end}"))
        assert "in the future" not in html.lower()
        assert fmt(date.today()) in html, "the Showing line must end at today"


# ------------------------------------------------------------------ #
# History-start adjustment (AC10-AC12)                                #
# ------------------------------------------------------------------ #


class TestHistoryStartAdjustment:
    def test_custom_range_before_history_start_shows_note_and_uses_history_start(self, auth_client):
        user_id = get_user_id()
        history_start = date.today() - timedelta(days=30)
        add_expense(user_id, 250, "Food", history_start.isoformat(), "OLDEST")
        requested_start = history_start - timedelta(days=100)

        html = html_of(
            auth_client.get(f"/profile?range=custom&start={requested_start}&end={date.today()}")
        )
        expected_note = f"Showing data from {fmt(history_start)}, when your records begin."
        assert expected_note in html
        assert "OLDEST" in html

    def test_custom_range_entirely_before_history_start_shows_note_and_empty_state(self, auth_client):
        user_id = get_user_id()
        history_start = date.today() - timedelta(days=30)
        add_expense(user_id, 250, "Food", history_start.isoformat(), "OLDEST")
        requested_start = history_start - timedelta(days=100)
        requested_end = history_start - timedelta(days=50)

        html = html_of(
            auth_client.get(
                f"/profile?range=custom&start={requested_start}&end={requested_end}"
            )
        )
        expected_note = f"Your records begin on {fmt(history_start)} — there's no data before that."
        assert expected_note in html
        assert "OLDEST" not in html
        assert money(0) in html, "AC11: empty result must show ₹0.00"
        assert "No expenses between" in html
        assert "Try a wider range." in html

    def test_preset_range_entirely_before_history_start_shows_no_note(self, auth_client):
        # A fresh user's history start is today (no expenses, no earlier
        # signup date to fall back on), so Last month is entirely before it.
        html = html_of(auth_client.get("/profile?range=last_month"))
        assert "when your records begin" not in html, (
            "Edge Cases table: preset ranges never show the case (a)/(b) note"
        )
        assert "there's no data before that" not in html

    def test_showing_line_for_fresh_user_starts_at_signup_date(self, auth_client):
        # A brand-new user's history start = signup date = today, so This
        # month's displayed start silently moves to today (spec 06 FR6,
        # presets branch of case a) with no note shown.
        html = html_of(auth_client.get("/profile"))
        today = date.today()
        expected = f"Showing {fmt(today)} – {fmt(today)}"
        assert expected in html
        assert "when your records begin" not in html
        assert "there's no data before that" not in html


# ------------------------------------------------------------------ #
# Empty states (spec 06b FR8, superseding spec 06 AC15)               #
# ------------------------------------------------------------------ #


class TestEmptyStates:
    def test_never_logged_expense_shows_first_empty_state(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert "You haven't logged any expenses yet." in html

    def test_user_with_zero_expenses_never_crashes_across_ranges(self, auth_client):
        for query in (
            "range=this_month",
            "range=all_time",
            "range=custom&start=2020-01-01&end=2020-01-02",
        ):
            resp = auth_client.get(f"/profile?{query}")
            assert resp.status_code == 200
            assert "You haven't logged any expenses yet." in html_of(resp)

    def test_empty_filtered_range_shows_no_expenses_between_message(self, auth_client):
        user_id = get_user_id()
        add_expense(
            user_id, 40, "Food", (date.today() - timedelta(days=200)).isoformat(), "OLD-EXPENSE"
        )
        gap_start = date.today() - timedelta(days=100)
        gap_end = date.today() - timedelta(days=90)

        html = html_of(
            auth_client.get(f"/profile?range=custom&start={gap_start}&end={gap_end}")
        )
        expected = f"No expenses between {fmt(gap_start)} and {fmt(gap_end)}. Try a wider range."
        assert expected in html
        assert "OLD-EXPENSE" not in html


# ------------------------------------------------------------------ #
# Budget subtext and month-by-month table (AC13, AC14)                #
# ------------------------------------------------------------------ #


class TestBudgetSubtextAndTable:
    def test_single_month_range_shows_budget_subtext_not_table(self, auth_client):
        user_id = get_user_id()
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10000", "range": "this_month", "start": "", "end": ""},
        )
        add_expense(user_id, 500, "Food", date.today().isoformat(), "SPEND")

        html = html_of(auth_client.get("/profile?range=this_month"))
        assert f"{money(500)} of {money(10000)} budget used" in html
        assert "Uses your current monthly budget for every month." not in html

    def test_multi_month_range_hides_subtext_shows_budget_table(self, auth_client):
        user_id = get_user_id()
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10000", "range": "this_month", "start": "", "end": ""},
        )
        today = date.today()
        month1_start = first_of_previous_month(today)
        add_expense(user_id, 300, "Food", month1_start.isoformat(), "PREV-MONTH-SPEND")
        add_expense(user_id, 400, "Food", today.isoformat(), "THIS-MONTH-SPEND")

        html = html_of(
            auth_client.get(f"/profile?range=custom&start={month1_start}&end={today}")
        )
        assert "budget used" not in html, "the single-month subtext must be hidden"
        assert "Uses your current monthly budget for every month." in html
        assert money(300) in html
        assert money(400) in html
        # Scope the ordering check to the budget table itself — month
        # labels like "Sep 2026" also appear in unrelated page text (e.g.
        # a "Member since Sep 2026" header), so comparing raw whole-page
        # positions is unreliable. "budget-table" is the table's own CSS
        # class, confirmed by spec 06b's own end-to-end verification script.
        table_start = html.index("budget-table")
        table_html = html[table_start:]
        prev_label = month1_start.strftime("%b %Y")
        this_label = today.strftime("%b %Y")
        assert prev_label in table_html and this_label in table_html, (
            "expected both month labels inside the budget table"
        )
        assert table_html.index(prev_label) < table_html.index(this_label), (
            "rows must be oldest month first"
        )

    def test_no_budget_set_shows_no_subtext_or_table_for_any_range(self, auth_client):
        user_id = get_user_id()
        add_expense(user_id, 500, "Food", date.today().isoformat(), "SPEND")

        for query in ("range=this_month", "range=last_3_months"):
            html = html_of(auth_client.get(f"/profile?{query}"))
            assert "budget used" not in html
            assert "Uses your current monthly budget for every month." not in html

    def test_zero_budget_shows_dash_percent_no_division_by_zero(self, auth_client):
        user_id = get_user_id()
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "0", "range": "this_month", "start": "", "end": ""},
        )
        today = date.today()
        prev_start = first_of_previous_month(today)
        add_expense(user_id, 50, "Food", prev_start.isoformat(), "X")

        html = html_of(
            auth_client.get(f"/profile?range=custom&start={prev_start}&end={today}")
        )
        assert "Uses your current monthly budget for every month." in html
        assert "—" in html, "Edge Cases: budget=0 must show a dash, not divide by zero"


# ------------------------------------------------------------------ #
# Budget bar control (spec 06 FR9 as superseded by 06b FR3)           #
# ------------------------------------------------------------------ #


class TestBudgetBarControl:
    def test_no_budget_shows_add_monthly_budget_control(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert "Add monthly budget" in html

    def test_setting_budget_shows_amount_and_toast(self, auth_client):
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10,000", "range": "this_month", "start": "", "end": ""},
            follow_redirects=True,
        )
        html = html_of(resp)
        assert resp.status_code == 200
        assert money(10000) in html
        assert "Add monthly budget" not in html
        assert "Budget saved." in html
        assert get_monthly_budget() == 10000, "commas must be stripped before saving"

    def test_removing_budget_shows_add_control_again(self, auth_client):
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10000", "range": "this_month", "start": "", "end": ""},
        )
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "", "range": "this_month", "start": "", "end": ""},
            follow_redirects=True,
        )
        html = html_of(resp)
        assert resp.status_code == 200
        assert "Budget removed." in html
        assert "Add monthly budget" in html
        assert get_monthly_budget() is None

    @pytest.mark.parametrize("bad_value", ["-5", "abc"])
    def test_invalid_budget_input_leaves_budget_unchanged_and_errors(self, auth_client, bad_value):
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10000", "range": "this_month", "start": "", "end": ""},
        )
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": bad_value, "range": "this_month", "start": "", "end": ""},
            follow_redirects=True,
        )
        html = html_of(resp)
        assert resp.status_code == 200
        assert "Monthly budget must be a non-negative number." in html
        assert get_monthly_budget() == 10000, "an invalid value must not overwrite the saved budget"

    def test_budget_value_ignores_commas_and_spaces(self, auth_client):
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": " 10 000 ", "range": "this_month", "start": "", "end": ""},
        )
        assert get_monthly_budget() == 10000

    def test_budget_zero_is_a_valid_value(self, auth_client):
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "0", "range": "this_month", "start": "", "end": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Budget saved." in html_of(resp)
        assert get_monthly_budget() == 0

    def test_budget_post_redirects_preserving_preset_range(self, auth_client):
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "5000", "range": "last_3_months", "start": "", "end": ""},
        )
        assert resp.status_code == 302
        assert "range=last_3_months" in resp.headers["Location"]

    def test_budget_post_redirects_preserving_custom_start_end(self, auth_client):
        start, end = "2026-01-01", "2026-01-31"
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "5000", "range": "custom", "start": start, "end": end},
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "range=custom" in location
        assert f"start={start}" in location
        assert f"end={end}" in location


# ------------------------------------------------------------------ #
# Money format (AC26, FR11)                                           #
# ------------------------------------------------------------------ #


class TestMoneyFormat:
    @pytest.mark.parametrize(
        "raw_value,expected",
        [
            ("10000", "₹10,000.00"),
            ("100000", "₹1,00,000.00"),
            ("1234567.5", "₹12,34,567.50"),
        ],
    )
    def test_budget_amount_uses_indian_digit_grouping(self, auth_client, raw_value, expected):
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": raw_value, "range": "this_month", "start": "", "end": ""},
            follow_redirects=True,
        )
        html = html_of(resp)
        assert resp.status_code == 200
        assert expected in html, "spec 06 FR11: Indian digit grouping, not Python's {:,.2f}"


# ------------------------------------------------------------------ #
# Edit-profile interaction (AC16 / AC25)                              #
# ------------------------------------------------------------------ #


class TestEditProfileInteraction:
    def test_saving_edit_profile_form_does_not_change_existing_budget(self, auth_client):
        """SPEC GAP: the edit-profile POST route's full field list (e.g. a
        display-name field) belongs to spec 04, which this file does not
        read. Only `email` (spec 06b DOM hooks) and `notes`
        (spec 06b FR10: `<textarea name="notes" form="profile-form">`) are
        confirmed field names. This test therefore only asserts the
        budget-preservation invariant (spec 06 AC25), not a specific
        success status code for the save itself."""
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "7000", "range": "this_month", "start": "", "end": ""},
        )
        resp = auth_client.post(
            "/profile", data={"email": "test@example.com", "notes": "updated via test"}
        )
        assert resp.status_code in (200, 302), "editing the profile popup must not error"
        assert get_monthly_budget() == 7000, (
            "spec 06 FR8: saving the edit-profile popup keeps monthly_budget unchanged"
        )
