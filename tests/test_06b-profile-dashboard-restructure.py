"""Tests for the /profile dashboard restructure (spec 06b).

Written from `.claude/specs/06b-profile-dashboard-restructure.md` only —
`app.py`, `templates/`, `static/` and `database/` were never opened. Most of
this spec is layout and colour (block reordering, icon badges, CSS category
tokens), which pytest cannot see in a response body; those acceptance
criteria are intentionally NOT covered here — see the handback report for
the full list and why.

Expense rows are inserted directly with parameterised SQL against the
throwaway file conftest.py points database.db.DB_PATH at (via the
client/auth_client fixtures). The `expenses`/`users` column names below
(user_id, amount, category, date, description / id, email, monthly_budget)
and the html_of()/fmt()/money() helper conventions are copied from
tests/test_06-date-time-filter.py's own helper section, per the task's
instructions — never its assertions.
"""

import html as html_module
import re
import sqlite3
from datetime import date, timedelta

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
    '1 Jul 2026', '19 Sep 2026' (spec 06 FR4 / 06b FR9 examples)."""
    return f"{d.day} {d.strftime('%b %Y')}"


def money(amount):
    """Indian digit grouping with 2 decimals and a rupee prefix, per spec 06
    FR11 (reaffirmed unchanged by 06b): '₹10,000.00', '₹1,00,000.00'."""
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


# Jinja autoescapes template variables, so a literal apostrophe in an
# expected string (e.g. "haven't", "records begin — there's") comes back
# from the response body as an HTML entity ("haven&#39;t"). Every assertion
# below reads the page through html_of(), never a bare resp.data.decode().
def html_of(resp):
    return html_module.unescape(resp.data.decode())


def extract_showing_range(html):
    """Pull the two date labels out of the bar's 'Showing <start> – <end>'
    line. `[^<]+` stops at the first tag boundary (e.g. the range-pill span
    that follows), so it works regardless of surrounding markup."""
    m = re.search(r"Showing\s+([^<]+?)\s+–\s+([^<]+?)(?:<|\s{2,}|$)", html)
    assert m, "expected a 'Showing <start> – <end>' line on the bar"
    return m.group(1).strip(), m.group(2).strip()


def extract_empty_range_message_dates(html):
    """Pull the two date labels out of FR8 row 2's
    'No expenses between <start> and <end>. Try a wider range.' message."""
    m = re.search(
        r"No expenses between\s+(.+?)\s+and\s+(.+?)\.\s*Try a wider range\.", html
    )
    assert m, "expected the FR8 row-2 empty-range message"
    return m.group(1).strip(), m.group(2).strip()


def bar_slice(html):
    """Slice the page down to just the range+budget bar's own markup (spec
    06b FR3 names the element `.range-budget-bar`; its own End-to-End
    Verification script in §10 locates it the same way, via the literal
    substring). Bounded by the next block FR1 puts after it, the stat tiles
    (`.profile-stats-row`) — so assertions run against this slice only see
    what the bar itself rendered, never an unrelated "Edit"/"Add" elsewhere
    on the page (e.g. the header's "Edit profile" button or the edit-profile
    modal's own heading)."""
    start = html.index("range-budget-bar")
    end = html.index("profile-stats-row", start)
    return html[start:end]


def date_filter_custom_slice(html):
    """Slice the page down to the `.date-filter-custom` From/To controls
    (spec 06b FR2), bounded by the next block FR1 puts after the whole date
    filter row, the range+budget bar."""
    start = html.index("date-filter-custom")
    end = html.index("range-budget-bar", start)
    return html[start:end]


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #


class TestAuthGuard:
    def test_profile_logged_out_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "logged-out /profile must redirect, not 200"
        assert "/login" in resp.headers["Location"]


# ------------------------------------------------------------------ #
# AC1 — block order                                                   #
# ------------------------------------------------------------------ #


class TestBlockOrder:
    def test_filter_row_then_bar_then_stats_then_grid(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        idx_filter = html.index("date-filter")
        idx_bar = html.index("range-budget-bar")
        idx_stats = html.index("profile-stats-row")
        idx_grid = html.index('class="profile-content-grid"')
        assert idx_filter < idx_bar < idx_stats < idx_grid, (
            "FR1: date filter -> range+budget bar -> stat tiles -> content "
            "grid, in that exact order"
        )

    def test_budget_table_renders_after_content_grid_when_present(self, auth_client):
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
        grid = html.index('class="profile-content-grid"')
        table = html.index("budget-table")
        assert grid < table, (
            "FR1: the month-by-month budget table must render after the "
            "content grid, not between it and the stat tiles"
        )


# ------------------------------------------------------------------ #
# AC3 — From/To boxes blank unless active_range == 'custom'           #
# ------------------------------------------------------------------ #


class TestDateFilterCustomBoxes:
    def test_date_inputs_blank_on_preset_range(self, auth_client):
        html = html_of(auth_client.get("/profile?range=this_month"))
        filter_html = date_filter_custom_slice(html)
        inputs = re.findall(r'<input[^>]*type="date"[^>]*>', filter_html)
        assert len(inputs) == 2, "expected exactly the From/To date inputs"
        for tag in inputs:
            m = re.search(r'value="([^"]*)"', tag)
            value = m.group(1) if m else ""
            assert value == "", (
                "AC3: From/To boxes must be blank unless active_range == "
                f"'custom', got value={value!r}"
            )

    def test_date_inputs_carry_submitted_dates_on_custom_range(self, auth_client):
        # A fresh auth_client's history start is today (no expenses, no
        # earlier signup date to fall back on — spec 06 FR6), so a single
        # day equal to today is the one custom range guaranteed not to
        # trigger a history-start note or a future-date error, keeping this
        # test focused only on AC3 (input echo), not FR6 adjustment.
        d = date.today().isoformat()
        html = html_of(auth_client.get(f"/profile?range=custom&start={d}&end={d}"))
        filter_html = date_filter_custom_slice(html)
        assert filter_html.count(f'value="{d}"') == 2, (
            f"AC3: both From and To boxes must carry the submitted date {d!r} "
            "when active_range == 'custom'"
        )


# ------------------------------------------------------------------ #
# AC4-AC6, AC8 — the range + budget bar                               #
# ------------------------------------------------------------------ #


class TestRangeBudgetBar:
    def test_bar_shows_showing_line_and_range_pill(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert re.search(
            r"Showing\s+\d{1,2} [A-Za-z]{3} \d{4}\s+–\s+\d{1,2} [A-Za-z]{3} \d{4}", html
        ), "AC4: expected 'Showing <start> – <end>' on the bar's left side"
        assert '<span class="range-pill">' in html, "spec 06 FR10 pill still applies"

    def test_no_budget_shows_add_control_and_no_bare_edit(self, auth_client):
        # Scoped to the bar's own markup (bar_slice), not the whole page —
        # a page-wide search for "Edit" also matches the header's "Edit
        # profile" button and the edit-profile modal's own "Edit profile"
        # heading, neither of which says anything about what the bar itself
        # renders. AC5 is specifically about the bar's right side.
        html = html_of(auth_client.get("/profile"))
        bar = bar_slice(html)
        assert "Add monthly budget" in bar, "AC5"
        assert not re.search(r"\bEdit\b", bar), (
            "AC5: the bar must not carry an Edit control when no budget is set"
        )

    def test_budget_set_shows_amount_and_edit_hides_add_control(self, auth_client):
        auth_client.post(
            "/profile/budget",
            data={"monthly_budget": "10000", "range": "this_month", "start": "", "end": ""},
        )
        html = html_of(auth_client.get("/profile"))
        bar = bar_slice(html)
        assert money(10000) in bar, "AC6: budget amount must render on the bar, FR11 formatted"
        assert "Add monthly budget" not in bar, "AC6: Add control must be absent once set"
        assert re.search(r"\bEdit\b", bar), "AC6: the bar must carry an Edit control once set"

    def test_popover_tip_line_renders(self, auth_client):
        """AC8 (partial). A native <details> element's body is present in the
        HTML response regardless of open/closed state, so this confirms the
        tip line text exists on the page. It does NOT confirm the text is
        nested *inside the popover rather than on the bar itself* — that is
        a DOM-nesting claim pytest cannot see from response text alone."""
        html = html_of(auth_client.get("/profile"))
        assert (
            "Your current budget is used for every month in a multi-month view."
            in html
        )


# ------------------------------------------------------------------ #
# AC9 — filter_error / range_note sit below the bar, not inside it    #
# ------------------------------------------------------------------ #


class TestFilterErrorAndRangeNotePlacement:
    def test_filter_error_renders_between_bar_and_stat_tiles(self, auth_client):
        html = html_of(auth_client.get("/profile?range=bogus"))
        bar_idx = html.index("range-budget-bar")
        error_idx = html.index("Unknown date range.")
        stats_idx = html.index("profile-stats-row")
        assert bar_idx < error_idx < stats_idx, (
            "AC9: filter_error must render below the bar, not squeezed inside it"
        )

    def test_range_note_renders_between_bar_and_stat_tiles(self, auth_client):
        user_id = get_user_id()
        history_start = date.today() - timedelta(days=30)
        add_expense(user_id, 250, "Food", history_start.isoformat(), "OLDEST")
        requested_start = history_start - timedelta(days=100)

        html = html_of(
            auth_client.get(
                f"/profile?range=custom&start={requested_start}&end={date.today()}"
            )
        )
        bar_idx = html.index("range-budget-bar")
        note_idx = html.index("when your records begin")
        stats_idx = html.index("profile-stats-row")
        assert bar_idx < note_idx < stats_idx, (
            "AC9: range_note must render below the bar, not squeezed inside it"
        )


# ------------------------------------------------------------------ #
# AC11 — no bare pencil entity/character anywhere on the page         #
# ------------------------------------------------------------------ #


class TestNoBareEntity:
    def test_no_pencil_entity_or_character_on_page(self, auth_client):
        raw = auth_client.get("/profile").data.decode()
        assert "&#9998;" not in raw, "FR5: &#9998; must be replaced by the edit icon macro"
        assert "✎" not in raw


# ------------------------------------------------------------------ #
# AC12 — View all link                                                #
# ------------------------------------------------------------------ #


class TestViewAllLink:
    def test_view_all_link_points_at_analytics(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert "View all" in html
        assert 'href="/analytics"' in html, "FR6: View all must point at /analytics"


# ------------------------------------------------------------------ #
# AC16, AC17 — empty states (FR8)                                     #
# ------------------------------------------------------------------ #


class TestEmptyStates:
    def test_never_logged_expense_shows_message_in_both_cards(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert html.count("You haven't logged any expenses yet.") >= 2, (
            "AC16: FR8 row 1 — both Recent Transactions and By Category show it"
        )

    def test_expenses_exist_but_range_empty_shows_message_in_both_cards(self, auth_client):
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
        assert html.count(expected) >= 2, (
            "AC17: FR8 row 2 — both cards show the same effective-range message"
        )
        assert "OLD-EXPENSE" not in html

    def test_empty_state_message_dates_match_bar_after_history_adjustment(self, auth_client):
        """FR8: the <start>/<end> in the empty-state message are the
        *effective* range (after any history-start adjustment) — the same
        range_start_label/range_end_label the bar shows — never the raw
        ?start=/?end= query values.

        SPEC GAP: FR6/FR8 don't state the exact effective end-date value used
        when a custom range falls *entirely* before history start (the
        "there's no data before that" branch) — spec 06's own test for this
        branch (test_06 TestHistoryStartAdjustment) only asserts the note and
        "No expenses between"/"Try a wider range." text are present, never
        pinning exact dates either. So this test asserts the general
        consistency guarantee FR8 actually states in prose ("the page never
        shows two different ranges at once") — bar dates == message dates —
        rather than hardcoding specific date values for this branch.
        """
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
        bar_dates = extract_showing_range(html)
        msg_dates = extract_empty_range_message_dates(html)
        assert bar_dates == msg_dates, (
            "AC17/FR8: the bar and the empty-state message must never show "
            f"two different ranges (bar={bar_dates}, message={msg_dates})"
        )


# ------------------------------------------------------------------ #
# AC18 — date labels come from format_day(), not a template strftime  #
# ------------------------------------------------------------------ #


class TestDateLabelFormat:
    def test_no_leading_zero_on_single_digit_day(self, auth_client):
        user_id = get_user_id()
        add_expense(user_id, 10, "Food", "2026-09-01", "SEED")

        html = html_of(
            auth_client.get("/profile?range=custom&start=2026-09-01&end=2026-09-05")
        )
        assert "Showing 1 Sep 2026 – 5 Sep 2026" in html, (
            "AC18: labels must come from format_day() (no leading zero on the "
            "day), not a template-side strftime('%d %b %Y') call"
        )
        assert "01 Sep 2026" not in html
        assert "05 Sep 2026" not in html


# ------------------------------------------------------------------ #
# AC20 — DOM hooks static/js/main.js binds must survive               #
# ------------------------------------------------------------------ #


class TestJsHooksSurvive:
    def test_edit_profile_and_profile_form_hooks_present(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert 'id="open-edit-profile"' in html
        assert 'id="profile-form"' in html
        assert 'id="email"' in html
        assert "data-original-email" in html

    def test_exactly_two_custom_date_inputs(self, auth_client):
        html = html_of(auth_client.get("/profile"))
        assert "date-filter-custom" in html
        assert html.count('type="date"') == 2, (
            "the .date-filter-custom From/To native date inputs main.js's "
            "IIFE 5 binds — FR2 says this block is otherwise unchanged"
        )
