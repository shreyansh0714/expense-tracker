"""Tests for spec 06 — Date filter on the Profile dashboard.

Written from `.claude/specs/06-date-time-filter.md` only. Test data (dated
expenses, monthly_budget, second users) is inserted through the throwaway DB
that `tests/conftest.py`'s `client`/`auth_client` fixtures already point
`database.db.DB_PATH` at — never the real `database.db`.

Money strings use FR11's format (Revision 1, 2026-09-20): Indian digit
grouping (last 3 digits, then 2s) plus 2 decimals, e.g. `₹10,000.00` and
`₹1,00,000.00` for a lakh — built by `_money()`/`_indian_group()` below,
never Python's `f"{x:,.2f}"`, which is international grouping and only
looks the same below a lakh. "Showing ..." / note dates use `%d %b %Y`
per FR4, but FR4's own worked example ("Showing 1 Jul 2026 - 19 Sep 2026")
is NOT zero-padded, contradicting `%d`'s zero-padding — see SPEC GAP
below. Tests therefore accept either the zero-padded or unpadded day when
matching those lines.

All response bodies are read through `page_text()`, which HTML-unescapes
the decoded body before any substring check. Jinja autoescapes text nodes,
so a straight apostrophe or `&` in an expected message (e.g. "there's")
would otherwise show up in the raw response as `there&#39;s` and fail a
literal match — `page_text()`/`html.unescape` is the one place that's
handled, so every test compares against plain, human-readable text.

Revision 1 (2026-09-20) additions covered here: FR8 (budget field removed
from the edit-profile popup), FR9 (`POST /profile/budget`, the budget
card, its toasts), FR10 (active-range pill), FR11 (comma money format).
FR12/FR13 are look-only / a manual calendar click, so no automated tests
(AC20 is manual only, matching FR13). See SPEC GAP notes below and near
the relevant tests for the edit-profile-popup route/field names, which
Revision 1 still doesn't give.
"""

import calendar
import html
import re
from datetime import date, timedelta

import pytest

from database import db

RUPEE = "₹"


# ------------------------------------------------------------------ #
# DB / formatting helpers (test setup only — never used to read app.py
# or database/, only to write rows for a test's own scenario)
# ------------------------------------------------------------------ #

def _get_user_id(email):
    conn = db.get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row[0]


def _insert_expense(user_id, amount, category, expense_date, description="expense"):
    conn = db.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date.isoformat(), description),
    )
    conn.commit()
    conn.close()


def _set_budget(user_id, budget):
    conn = db.get_db()
    conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (budget, user_id))
    conn.commit()
    conn.close()


def _indian_group(int_str):
    """Indian digit grouping on an integer-part string: the last 3 digits
    are one group, everything above is grouped in 2s (e.g. "1234567" ->
    "12,34,567")."""
    if len(int_str) <= 3:
        return int_str
    last3 = int_str[-3:]
    rest = int_str[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups) + "," + last3


def _money(amount):
    """FR11 (Revision 1): Indian digit grouping + 2 decimals, e.g.
    '1,00,000.00' for a lakh — NOT Python's f"{x:,.2f}", which is
    international grouping ('100,000.00') and must not be used here."""
    sign = "-" if amount < 0 else ""
    int_part, dec_part = f"{abs(amount):.2f}".split(".")
    return f"{sign}{_indian_group(int_part)}.{dec_part}"


def _budget_subtext(spent, budget):
    return f"{RUPEE}{_money(spent)} of {RUPEE}{_money(budget)} budget used"


def page_text(resp):
    """HTML-unescape the decoded response body so tests can match plain
    text (e.g. "there's") regardless of Jinja autoescaping turning it into
    an entity (e.g. "there&#39;s")."""
    return html.unescape(resp.data.decode())


def pill_text(resp):
    """FR10: the active-range pill is `<span class="range-pill">…</span>`,
    distinct from the preset buttons that carry the same words."""
    match = re.search(r'<span class="range-pill">(.*?)</span>', page_text(resp))
    return match.group(1).strip() if match else None


def _first_of_month(d):
    return d.replace(day=1)


def _last_day_of_month(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _months_ago_first(d, months):
    """1st of the month `months` months before d's month."""
    total = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _add_months(d, months):
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    day = min(d.day, calendar.monthrange(year, month + 1)[1])
    return date(year, month + 1, day)


def _date_variants(d):
    """Both the zero-padded (%d %b %Y) and unpadded forms — see module
    docstring SPEC GAP about FR4's contradictory example."""
    padded = d.strftime("%d %b %Y")
    unpadded = f"{d.day} {d.strftime('%b %Y')}"
    return padded, unpadded


def assert_date_in_text(text, d, msg=None):
    padded, unpadded = _date_variants(d)
    assert padded in text or unpadded in text, (
        msg or f"expected formatted date {d.isoformat()} ({padded!r} or {unpadded!r}) in response"
    )


# ------------------------------------------------------------------ #
# AC1, AC2 — defaults + filter bar markup
# ------------------------------------------------------------------ #

class TestFilterBarAndDefaults:
    def test_no_params_defaults_to_this_month_and_marks_it_active(self, auth_client):
        """AC1: GET /profile with no params -> 200, This month figures, This
        month preset carries aria-pressed="true"."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 5000)
        _insert_expense(user_id, 500, "Food", today, "this month expense")

        resp = auth_client.get("/profile")
        text = page_text(resp)

        assert resp.status_code == 200
        assert 'aria-pressed="true"' in text, "expected an active preset marker"
        assert _budget_subtext(500, 5000) in text, (
            "This month spend should be 500.00 of the 5000.00 budget"
        )

    def test_filter_bar_has_four_presets_and_custom_range_inputs(self, auth_client):
        """AC2: 4 preset buttons (this_month/last_month/last_3_months/
        all_time), From/To date inputs named start/end, and an Apply
        button submitting range=custom."""
        resp = auth_client.get("/profile")
        text = page_text(resp)

        for label in ("This month", "Last month", "Last 3 months", "All time"):
            assert label in text, f"expected preset label {label!r} in filter bar"
        for value in (
            'value="this_month"',
            'value="last_month"',
            'value="last_3_months"',
            'value="all_time"',
        ):
            assert value in text, f"expected range value {value!r} in filter bar"
        assert 'name="start"' in text
        assert 'name="end"' in text
        assert 'type="date"' in text
        assert 'value="custom"' in text, "expected the hidden range=custom field"
        assert "Apply" in text


# ------------------------------------------------------------------ #
# AC3-AC6, AC8 — preset/custom range correctness
# ------------------------------------------------------------------ #

class TestRangeCorrectness:
    def test_last_month_includes_only_previous_calendar_month(self, auth_client):
        """AC3: ?range=last_month totals include only expenses dated in the
        previous calendar month."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        last_month_first = _months_ago_first(today, 1)
        last_month_last = _last_day_of_month(last_month_first)
        this_month_first = _first_of_month(today)

        _insert_expense(user_id, 400, "Food", last_month_first, "last month start")
        _insert_expense(user_id, 600, "Food", last_month_last, "last month end")
        _insert_expense(user_id, 900, "Food", this_month_first, "this month - excluded")

        resp = auth_client.get("/profile?range=last_month")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(1000, 100000) in text
        assert _money(900) not in text

    def test_last_3_months_includes_start_excludes_day_before(self, auth_client):
        """AC4: ?range=last_3_months includes the 1st of the month two
        months back through today, and excludes the day before that."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        range_start = _months_ago_first(today, 2)
        day_before = range_start - timedelta(days=1)

        _insert_expense(user_id, 300, "Food", range_start, "range start - included")
        _insert_expense(user_id, 700, "Food", day_before, "day before - excluded")

        resp = auth_client.get("/profile?range=last_3_months")
        text = page_text(resp)

        assert resp.status_code == 200
        assert_date_in_text(text, range_start, "Showing line should start at the 3-month range start")
        assert_date_in_text(text, today, "Showing line should end at today")
        assert range_start.strftime("%b %Y") in text
        assert _money(300) in text
        assert _money(700) not in text

    def test_all_time_includes_expense_before_signup(self, auth_client):
        """AC5: ?range=all_time includes every expense, including one dated
        before users.created_at (the account was just created "today")."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        old_date = today - timedelta(days=400)

        _insert_expense(user_id, 250, "Food", old_date, "before signup")
        _insert_expense(user_id, 750, "Food", today, "today")

        resp = auth_client.get("/profile?range=all_time")
        text = page_text(resp)

        assert resp.status_code == 200
        # history start = min(created_at date [today], oldest expense date) = old_date
        assert_date_in_text(text, old_date, "Showing line should start at history start (the old expense's date)")
        assert "when your records begin" not in text, "presets never show the case-(a) note (FR6)"
        assert old_date.strftime("%b %Y") in text
        assert _money(250) in text

    def test_custom_range_bounds_are_inclusive(self, auth_client):
        """AC6: ?range=custom&start=X&end=Y includes X and Y inclusive,
        excludes X-1 and Y+1."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        x = today - timedelta(days=10)
        y = today - timedelta(days=5)
        before_x = x - timedelta(days=1)
        after_y = y + timedelta(days=1)

        _insert_expense(user_id, 150, "Food", x, "on start - included")
        _insert_expense(user_id, 275, "Food", y, "on end - included")
        _insert_expense(user_id, 999, "Food", before_x, "before start - excluded")
        _insert_expense(user_id, 888, "Food", after_y, "after end - excluded")

        resp = auth_client.get(f"/profile?range=custom&start={x.isoformat()}&end={y.isoformat()}")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _money(999) not in text, "expense before custom start must be excluded"
        assert _money(888) not in text, "expense after custom end must be excluded"
        if (x.year, x.month) == (y.year, y.month):
            assert _budget_subtext(150 + 275, 100000) in text
        else:
            assert _money(150) in text
            assert _money(275) in text

    def test_custom_single_day_range_is_valid(self, auth_client):
        """Edge case: start == end (a single day) is valid and shows only
        that day."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        target_day = today - timedelta(days=3)

        _insert_expense(user_id, 650, "Food", target_day, "the day")
        _insert_expense(user_id, 700, "Food", target_day - timedelta(days=1), "day before - excluded")
        _insert_expense(user_id, 800, "Food", target_day + timedelta(days=1), "day after - excluded")

        resp = auth_client.get(
            f"/profile?range=custom&start={target_day.isoformat()}&end={target_day.isoformat()}"
        )
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(650, 100000) in text
        assert _money(700) not in text
        assert _money(800) not in text

    def test_other_users_expenses_never_appear(self, auth_client):
        """AC8: another user's expenses never appear in any filtered
        figure."""
        user_a_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_a_id, 100000)
        _insert_expense(user_a_id, 300, "Food", today, "user A expense")

        auth_client.post(
            "/register",
            data={"name": "Other User", "email": "other@example.com", "password": "otherpass1"},
        )
        auth_client.post("/login", data={"email": "other@example.com", "password": "otherpass1"})
        user_b_id = _get_user_id("other@example.com")
        _insert_expense(user_b_id, 99999, "Food", today, "user B expense")

        # back to user A
        auth_client.post("/login", data={"email": "test@example.com", "password": "testpass1"})
        resp = auth_client.get("/profile?range=all_time")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(300, 100000) in text
        assert _money(99999) not in text

    def test_total_spent_is_not_capped_at_five(self, auth_client):
        """Context for AC7: the Total Spent figure reflects every expense in
        range, not just the 5-row Recent Transactions preview. (The exact
        markup for Recent Transactions rows isn't specified by the spec —
        see SPEC GAP; row count/ordering isn't asserted here.)"""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        total = 0
        for i in range(7):
            amt = 100 + i
            total += amt
            _insert_expense(user_id, amt, "Food", today, f"expense {i}")

        resp = auth_client.get("/profile")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(total, 100000) in text


# ------------------------------------------------------------------ #
# AC9 — validation errors
# ------------------------------------------------------------------ #

class TestFilterErrors:
    @pytest.mark.parametrize(
        "query, expected_message",
        [
            ("range=bogus", "Unknown date range."),
            ("range=custom&start=2026-09-01", "Please choose both a start and an end date."),
            ("range=custom&start=&end=2026-09-10", "Please choose both a start and an end date."),
            ("range=custom&start=abc&end=2026-09-10", "Please enter valid dates."),
            ("range=custom&start=2026-02-30&end=2026-03-01", "Please enter valid dates."),
        ],
    )
    def test_static_error_inputs_return_200_with_message_and_this_month_fallback(
        self, auth_client, query, expected_message
    ):
        resp = auth_client.get(f"/profile?{query}")
        text = page_text(resp)
        assert resp.status_code == 200, "invalid filter input must never produce a 4xx"
        assert expected_message in text
        assert 'aria-pressed="true"' in text, "should fall back to This month, which is marked active"

    def test_start_after_end_shows_error(self, auth_client):
        today = date.today()
        start = today.isoformat()
        end = (today - timedelta(days=1)).isoformat()
        resp = auth_client.get(f"/profile?range=custom&start={start}&end={end}")
        text = page_text(resp)
        assert resp.status_code == 200
        assert "Start date must be on or before end date." in text

    def test_start_after_today_shows_future_error(self, auth_client):
        today = date.today()
        start = (today + timedelta(days=5)).isoformat()
        end = (today + timedelta(days=10)).isoformat()
        resp = auth_client.get(f"/profile?range=custom&start={start}&end={end}")
        text = page_text(resp)
        assert resp.status_code == 200
        assert "That date range is in the future." in text

    def test_start_end_ignored_when_range_is_not_custom(self, auth_client):
        """Edge case table: start/end given with a non-custom range are
        ignored; the preset wins."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        _insert_expense(user_id, 400, "Food", today, "this month expense")

        resp = auth_client.get("/profile?range=this_month&start=2000-01-01&end=2000-01-02")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(400, 100000) in text
        assert "Please enter valid dates." not in text

    def test_extra_unknown_query_params_are_ignored(self, auth_client):
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        _insert_expense(user_id, 321, "Food", today, "expense")

        resp = auth_client.get("/profile?foo=bar&range=this_month&baz=qux")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(321, 100000) in text
        assert "Unknown date range." not in text


# ------------------------------------------------------------------ #
# AC10-AC12 — history-start adjustment notes
# ------------------------------------------------------------------ #

class TestHistoryStartAdjustment:
    def test_custom_start_before_history_start_moves_start_and_notes(self, auth_client):
        """AC10: a custom range starting before history start shows the
        "Showing data from ..." note and correct figures from history
        start."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        oldest_expense_date = today - timedelta(days=30)
        _insert_expense(user_id, 500, "Food", oldest_expense_date, "history start expense")
        far_past_start = oldest_expense_date - timedelta(days=1000)

        resp = auth_client.get(
            f"/profile?range=custom&start={far_past_start.isoformat()}&end={today.isoformat()}"
        )
        text = page_text(resp)

        assert resp.status_code == 200
        padded, unpadded = _date_variants(oldest_expense_date)
        note_padded = f"Showing data from {padded}, when your records begin."
        note_unpadded = f"Showing data from {unpadded}, when your records begin."
        assert note_padded in text or note_unpadded in text, "expected the case-(a) history-start note"
        assert _money(500) in text

    def test_custom_range_entirely_before_history_start_is_empty_with_note(self, auth_client):
        """AC11: a custom range entirely before history start shows the
        "Your records begin on ..." note and 0/empty states."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        oldest_expense_date = today - timedelta(days=10)
        _insert_expense(user_id, 500, "Food", oldest_expense_date, "only expense")
        range_end = oldest_expense_date - timedelta(days=5)
        range_start = range_end - timedelta(days=30)

        resp = auth_client.get(
            f"/profile?range=custom&start={range_start.isoformat()}&end={range_end.isoformat()}"
        )
        text = page_text(resp)

        assert resp.status_code == 200
        padded, unpadded = _date_variants(oldest_expense_date)
        note_padded = f"Your records begin on {padded} — there's no data before that."
        note_unpadded = f"Your records begin on {unpadded} — there's no data before that."
        assert note_padded in text or note_unpadded in text, "expected the case-(b) history-start note"
        assert "No expenses in this period." in text

    def test_custom_range_entirely_before_history_start_hides_budget_table(self, auth_client):
        """FR6 case (b): "Empty result (₹0, 0 transactions, no top category,
        empty list/bars, no budget table)" — with monthly_budget set and a
        multi-month custom range entirely before history start, neither the
        budget subtext nor the Month-by-month budget table appears."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 10000)
        oldest_expense_date = today - timedelta(days=10)
        _insert_expense(user_id, 500, "Food", oldest_expense_date, "only expense")

        resp = auth_client.get("/profile?range=custom&start=2000-01-01&end=2000-12-31")
        text = page_text(resp)

        assert resp.status_code == 200
        assert "budget used" not in text, "no budget subtext for an empty, pre-history-start range"
        assert "Uses your current monthly budget for every month." not in text, (
            "no Month-by-month budget table for an empty, pre-history-start range"
        )

    def test_custom_range_with_future_end_clamps_to_today(self, auth_client):
        """AC12: end in the future + start in the past -> 200, no error,
        "Showing ..." ends at today."""
        today = date.today()
        start = (today - timedelta(days=5)).isoformat()
        end = (today + timedelta(days=30)).isoformat()

        resp = auth_client.get(f"/profile?range=custom&start={start}&end={end}")
        text = page_text(resp)

        assert resp.status_code == 200
        assert "That date range is in the future." not in text
        assert_date_in_text(text, today, "Showing line should clamp its end to today")


# ------------------------------------------------------------------ #
# AC13, AC14 — budget comparison
# ------------------------------------------------------------------ #

class TestBudgetComparison:
    def test_single_month_range_shows_subtext_not_table(self, auth_client):
        """AC13 (part 1): a single-month range with monthly_budget set shows
        the subtext and no budget table."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 10000)
        last_month_first = _months_ago_first(today, 1)
        _insert_expense(user_id, 2500, "Food", last_month_first, "last month expense")

        resp = auth_client.get("/profile?range=last_month")
        text = page_text(resp)

        assert resp.status_code == 200
        assert _budget_subtext(2500, 10000) in text
        assert "Uses your current monthly budget for every month." not in text

    def test_multi_month_range_shows_table_not_subtext(self, auth_client):
        """AC13 (part 2): a multi-month range hides the subtext and shows
        one Month-by-month row per month, oldest first, with correct Spent
        and % used, and the fixed caption."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 10000)
        m0 = _months_ago_first(today, 2)
        m1 = _add_months(m0, 1)
        # m2 (the current month) is left with 0 spend to also exercise
        # FR7's "no-spend month shows ₹0.00 and 0%" rule.
        _insert_expense(user_id, 1000, "Food", m0, "month0 expense")
        _insert_expense(user_id, 2000, "Food", m1, "month1 expense")

        resp = auth_client.get("/profile?range=last_3_months")
        text = page_text(resp)

        assert resp.status_code == 200
        assert "budget used" not in text, "subtext must be hidden for a multi-month range"
        assert "Uses your current monthly budget for every month." in text
        assert m0.strftime("%b %Y") in text
        assert m1.strftime("%b %Y") in text
        assert today.strftime("%b %Y") in text
        assert _money(1000) in text
        assert _money(2000) in text
        # 1000/10000 = 10%, 2000/10000 = 20%
        assert "10%" in text
        assert "20%" in text
        # FR7: the current (0-spend) month shows ₹0.00 and 0% — "0%" alone
        # would also match the tail of "10%"/"20%", so require it not be
        # preceded by a digit.
        assert f"{RUPEE}0.00" in text, "expected the 0-spend month's Spent cell to show ₹0.00"
        assert re.search(r"(?<!\d)0%", text), "expected the 0-spend month's % used cell to show 0%"

    @pytest.mark.parametrize("range_param", ["this_month", "last_month", "last_3_months", "all_time"])
    def test_no_monthly_budget_shows_neither_subtext_nor_table(self, auth_client, range_param):
        """AC14: with no monthly_budget, no subtext or table appears for
        any range."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, None)
        _insert_expense(user_id, 500, "Food", today, "expense")

        resp = auth_client.get(f"/profile?range={range_param}")
        text = page_text(resp)

        assert resp.status_code == 200
        assert "budget used" not in text
        assert "Uses your current monthly budget for every month." not in text

    def test_zero_budget_shows_dash_for_percent_used(self, auth_client):
        """Edge case: monthly_budget = 0 still shows the table (it's a set
        value, unlike NULL), but % used shows an em dash, not a
        division-by-zero result."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 0)
        m0 = _months_ago_first(today, 2)
        _insert_expense(user_id, 500, "Food", m0, "expense")

        resp = auth_client.get("/profile?range=last_3_months")
        text = page_text(resp)

        assert resp.status_code == 200
        assert "—" in text, "expected an em dash for % used when budget is 0"


# ------------------------------------------------------------------ #
# AC15 — empty states
# ------------------------------------------------------------------ #

class TestEmptyStates:
    def test_empty_range_shows_no_expenses_message_in_both_sections(self, auth_client):
        """AC15: empty ranges show "No expenses in this period." in both
        Recent Transactions and By Category."""
        user_id = _get_user_id("test@example.com")
        today = date.today()
        _set_budget(user_id, 100000)
        _insert_expense(user_id, 500, "Food", today, "this month only")

        resp = auth_client.get("/profile?range=last_month")
        text = page_text(resp)

        assert resp.status_code == 200
        assert text.count("No expenses in this period.") >= 2


# ------------------------------------------------------------------ #
# AC18 — filter bar placement, and auth guard
# ------------------------------------------------------------------ #

class TestFilterPlacementAndAuth:
    def test_filter_form_absent_from_other_pages(self, client):
        """AC18: the filter form appears on /profile only."""
        for path in ("/", "/login", "/register", "/terms", "/privacy"):
            resp = client.get(path)
            text = page_text(resp)
            assert 'name="range"' not in text, f"{path} must not contain the date-range filter form"

    def test_unauthenticated_profile_with_range_redirects_to_login(self, client):
        """Edge case table: logged-out visit to /profile?range=... keeps the
        existing auth guard (redirect to /login)."""
        resp = client.get("/profile?range=last_month", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


# ------------------------------------------------------------------ #
# AC19 — active-range pill (FR10, Revision 1)
# ------------------------------------------------------------------ #

class TestActiveRangePill:
    """FR10/AC19: the pill is `<span class="range-pill">…</span>`, distinct
    from the 4 preset buttons that carry the same words, so `pill_text()`
    can read its exact text for every case."""

    def test_pill_reads_this_month_by_default(self, auth_client):
        resp = auth_client.get("/profile")
        assert pill_text(resp) == "This month"

    def test_pill_reads_last_3_months_for_that_preset(self, auth_client):
        resp = auth_client.get("/profile?range=last_3_months")
        assert pill_text(resp) == "Last 3 months"

    def test_pill_reads_custom_range_for_a_valid_custom_range(self, auth_client):
        today = date.today()
        start = today - timedelta(days=2)
        resp = auth_client.get(
            f"/profile?range=custom&start={start.isoformat()}&end={today.isoformat()}"
        )
        assert pill_text(resp) == "Custom range"

    def test_pill_reads_this_month_after_an_error_fallback(self, auth_client):
        """AC19: "after the bogus URL, it reads This month"."""
        resp = auth_client.get("/profile?range=bogus")
        text = page_text(resp)
        assert "Unknown date range." in text, "sanity check that the fallback path was actually hit"
        assert pill_text(resp) == "This month"


# ------------------------------------------------------------------ #
# AC21-AC24, AC26 — budget card + POST /profile/budget (FR9/FR11,
# Revision 1)
# ------------------------------------------------------------------ #

class TestBudgetCard:
    def test_add_budget_saves_shows_toast_and_card_state(self, auth_client):
        """AC21: with no budget, /profile shows "+ Add monthly budget".
        POSTing monthly_budget=10,000 saves 10000, redirects to /profile,
        shows "Budget saved.", and the card then shows ₹10,000.00 with
        "✎ Edit"."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, None)

        resp_before = auth_client.get("/profile")
        assert "+ Add monthly budget" in page_text(resp_before)

        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10,000", "range": "this_month", "start": "", "end": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302, "APIs section: POST /profile/budget always returns 302"
        location = resp.headers.get("Location", "")
        assert "/profile" in location

        follow = auth_client.get(location)
        text = page_text(follow)
        assert follow.status_code == 200
        assert "Budget saved." in text
        assert f"{RUPEE}{_money(10000)}" in text
        assert "✎ Edit" in text, "expected the pencil '✎ Edit' control"
        assert "+ Add monthly budget" not in text

        conn = db.get_db()
        row = conn.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        assert float(row[0]) == 10000, "commas/spaces must be stripped before saving"

    def test_empty_budget_removes_it_and_shows_toast(self, auth_client):
        """AC22: POSTing monthly_budget= (empty) removes the budget, shows
        "Budget removed.", and the card shows "+ Add monthly budget"
        again."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, 5000)

        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "", "range": "this_month", "start": "", "end": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302, "APIs section: POST /profile/budget always returns 302"
        location = resp.headers.get("Location", "")

        follow = auth_client.get(location)
        text = page_text(follow)
        assert "Budget removed." in text
        assert "+ Add monthly budget" in text

        conn = db.get_db()
        row = conn.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        assert row[0] is None

    @pytest.mark.parametrize("bad_value", ["-5", "abc"])
    def test_invalid_budget_input_is_rejected_and_leaves_budget_unchanged(self, auth_client, bad_value):
        """AC23: POSTing monthly_budget=-5 or abc leaves the budget
        unchanged and shows the non-negative-number error."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, 7000)

        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": bad_value, "range": "this_month", "start": "", "end": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302, "APIs section: POST /profile/budget always returns 302"
        location = resp.headers.get("Location", "")

        follow = auth_client.get(location)
        text = page_text(follow)
        assert "Monthly budget must be a non-negative number." in text

        conn = db.get_db()
        row = conn.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        assert float(row[0]) == 7000, "the bad input must not overwrite the existing budget"

    def test_budget_post_redirect_preserves_the_current_filter(self, auth_client):
        """AC24 (part 1): POSTing with range=last_3_months redirects to
        /profile?range=last_3_months, not This month."""
        resp = auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "1000", "range": "last_3_months", "start": "", "end": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302, "APIs section: POST /profile/budget always returns 302"
        location = resp.headers.get("Location", "")
        assert "/profile" in location
        assert "range=last_3_months" in location

    def test_logged_out_budget_post_redirects_to_login(self, client):
        """AC24 (part 2): a logged-out POST redirects to /login."""
        resp = client.post(
            "/profile/budget",
            data={"monthly_budget": "1000", "range": "this_month", "start": "", "end": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    def test_money_amounts_use_thousands_commas(self, auth_client):
        """AC26: amounts use commas, e.g. ₹10,000.00, in the budget card."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, 10000)

        resp = auth_client.get("/profile")
        text = page_text(resp)

        assert resp.status_code == 200
        assert f"{RUPEE}{_money(10000)}" in text

    def test_money_uses_indian_grouping_not_international_for_lakh_amounts(self, auth_client):
        """AC26 / FR11: at a lakh or more, Indian grouping (last 3 digits,
        then 2s) differs visibly from Python's international `{:,.2f}` —
        below a lakh the two styles are identical, so this needs an amount
        of a lakh or more to actually exercise the difference. Uses the
        Manual Verification Guide's own AC26 example (1234567.5 ->
        ₹12,34,567.50, not ₹1,234,567.50)."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, 1234567.5)

        resp = auth_client.get("/profile")
        text = page_text(resp)

        assert resp.status_code == 200
        assert f"{RUPEE}12,34,567.50" in text
        assert _money(1234567.5) == "12,34,567.50"
        assert f"{RUPEE}1,234,567.50" not in text, "must not use international grouping"


# ------------------------------------------------------------------ #
# AC25 — budget field removed from the edit-profile popup (FR8,
# Revision 1)
# ------------------------------------------------------------------ #

class TestEditProfilePopupHasNoBudgetField:
    def test_monthly_budget_field_appears_exactly_once_on_the_page(self, auth_client):
        """AC25 (partial): the only monthly_budget field on /profile is the
        budget card's (FR9) — the edit-profile popup no longer has one.
        Checked as a page-wide count rather than scoping into the popup's
        markup specifically.

        SPEC GAP: the spec never gives the edit-profile popup's POST route
        or its field names (only "e.g. changing the name" informally), so
        the rest of AC25 — "saving the popup ... keeps an existing budget
        unchanged" — can't be exercised by actually submitting that form
        here. That half of AC25 is left untested; see the Manual
        Verification Guide's AC25 row instead."""
        user_id = _get_user_id("test@example.com")
        _set_budget(user_id, 4242)

        resp = auth_client.get("/profile")
        text = page_text(resp)

        assert resp.status_code == 200
        assert text.count('name="monthly_budget"') == 1, (
            "expected exactly one monthly_budget field (the budget card's), "
            "none left in the edit-profile popup"
        )
