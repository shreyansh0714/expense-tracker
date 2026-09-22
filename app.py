import math
import os
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    delete_expense as db_delete_expense,
    get_category_totals,
    get_db,
    get_first_expense_date,
    get_monthly_spend,
    get_recent_expenses,
    get_transaction_count,
    get_user_by_email,
    get_user_by_id,
    init_db,
    insert_expense,
    seed_db,
    update_monthly_budget,
    update_user,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

@app.template_filter("inr")
def format_inr(amount):
    """Indian digit grouping: 1234567.5 -> '12,34,567.50' (last 3 digits, then 2s)."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0.0
    whole, _, paise = f"{amount:.2f}".partition(".")
    sign, whole = ("-", whole[1:]) if whole.startswith("-") else ("", whole)
    head, tail = whole[:-3], whole[-3:]
    if head:
        groups = [head[max(i - 2, 0):i] for i in range(len(head), 0, -2)]
        tail = ",".join(reversed(groups)) + "," + tail
    return f"{sign}{tail}.{paise}"


def format_day(d):
    return f"{d.day} {d.strftime('%b %Y')}"


DATE_RANGES = {
    "this_month": "This month",
    "last_month": "Last month",
    "last_3_months": "Last 3 months",
    "all_time": "All time",
    "custom": "Custom range",
}

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
MAX_EXPENSE_AMOUNT = 10_000_000  # ₹1 crore


def resolve_date_range(args, history_start, today):
    """Turn the profile page's query string into an effective date range.

    Returns (active_range, start, end, note, error). Both dates are inclusive.
    """
    active_range = args.get("range") or "this_month"
    error = None
    note = None

    if active_range not in DATE_RANGES:
        error = "Unknown date range."
        active_range = "this_month"

    if active_range == "custom":
        start_raw = args.get("start", "").strip()
        end_raw = args.get("end", "").strip()
        try:
            custom_start = date.fromisoformat(start_raw)
            custom_end = date.fromisoformat(end_raw)
        except ValueError:
            custom_start = custom_end = None

        if not start_raw or not end_raw:
            error = "Please choose both a start and an end date."
        elif custom_start is None:
            error = "Please enter valid dates."
        elif custom_start > custom_end:
            error = "Start date must be on or before end date."
        elif custom_start > today:
            error = "That date range is in the future."

        if error:
            active_range = "this_month"

    month_start = today.replace(day=1)
    if active_range == "last_month":
        end = month_start - timedelta(days=1)
        start = end.replace(day=1)
    elif active_range == "last_3_months":
        months = today.year * 12 + today.month - 1 - 2
        start = date(months // 12, months % 12 + 1, 1)
        end = today
    elif active_range == "all_time":
        start, end = history_start, today
    elif active_range == "custom":
        start, end = custom_start, min(custom_end, today)
    else:
        start, end = month_start, today

    if end < history_start:
        if active_range == "custom":
            note = f"Your records begin on {format_day(history_start)} — there's no data before that."
    elif start < history_start:
        start = history_start
        if active_range == "custom":
            note = f"Showing data from {format_day(history_start)}, when your records begin."

    return active_range, start, end, note, error


def build_budget_rows(budget, start, end, monthly_spend):
    """One row per calendar month touched by start..end, oldest first."""
    spent_by_month = {row["month"]: row["total"] for row in monthly_spend}
    rows = []
    month = start.replace(day=1)
    while month <= end:
        spent = spent_by_month.get(month.strftime("%Y-%m"), 0)
        rows.append({
            "month_label": month.strftime("%b %Y"),
            "budget": budget,
            "spent": spent,
            "percent": round(spent / budget * 100) if budget else None,
        })
        month = (month + timedelta(days=32)).replace(day=1)
    return rows


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        error = "Name is required."
    elif "@" not in email:
        error = "Please enter a valid email address."
    elif (
        len(password) < 8
        or not any(c.isalpha() for c in password)
        or not any(c.isdigit() for c in password)
    ):
        error = "Password must be at least 8 characters and include a letter and a number."
    else:
        error = None

    if error:
        return render_template("register.html", error=error, name=name, email=email)

    try:
        user_id = create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
        )

    session["user_id"] = user_id
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password.", email=email
        )

    session["user_id"] = user["id"]
    session.permanent = True
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        flash("Please sign in to view analytics.", "error")
        return redirect(url_for("login"))

    return render_template("analytics.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    created_at = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
    history_start = created_at.date()
    first_expense_date = get_first_expense_date(user["id"])
    if first_expense_date:
        history_start = min(history_start, date.fromisoformat(first_expense_date))

    active_range, range_start, range_end, range_note, filter_error = resolve_date_range(
        request.args, history_start, date.today()
    )
    category_totals = get_category_totals(user["id"], range_start, range_end)
    budget = user["monthly_budget"]
    single_month = (range_start.year, range_start.month) == (range_end.year, range_end.month)
    monthly_budget_rows = []
    # Case (b): a range entirely before history start has no data, so no table
    # (also stops a range like 0001-2000 from building thousands of empty rows).
    if budget is not None and not single_month and range_end >= history_start:
        monthly_budget_rows = build_budget_rows(
            budget, range_start, range_end,
            get_monthly_spend(user["id"], range_start, range_end),
        )
    dashboard = {
        "member_since": created_at.strftime("%b %Y"),
        "category_totals": category_totals,
        "monthly_total": sum(row["total"] for row in category_totals),
        "transaction_count": get_transaction_count(user["id"], range_start, range_end),
        "top_category": category_totals[0]["category"] if category_totals else None,
        "recent_expenses": get_recent_expenses(user["id"], range_start, range_end),
        "original_email": user["email"],
        "budget_amount": user["monthly_budget"],
        "budget_input": "" if budget is None else format_inr(budget).removesuffix(".00"),
        "range_label": DATE_RANGES[active_range],
        "active_range": active_range,
        "range_start": range_start,
        "range_end": range_end,
        "range_start_label": format_day(range_start),
        "range_end_label": format_day(range_end),
        "has_expenses": first_expense_date is not None,
        "range_note": range_note,
        "filter_error": filter_error,
        "show_budget_subtext": budget is not None and single_month,
        "monthly_budget_rows": monthly_budget_rows,
        "today": date.today(),
        "new_expense_id": session.pop("new_expense_id", None),
    }

    if request.method == "GET":
        return render_template(
            "profile.html",
            name=user["name"],
            email=user["email"],
            notes=user["notes"] or "",
            **dashboard,
        )

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    notes = request.form.get("notes", "").strip()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    verification_code = request.form.get("verification_code", "")

    changing_password = bool(current_password or new_password or confirm_password)
    email_changed = email != user["email"]
    bypass_code = os.environ.get("PROFILE_EMAIL_BYPASS_CODE")

    if not name:
        error = "Name is required."
    elif "@" not in email:
        error = "Please enter a valid email address."
    elif len(notes) > 2000:
        error = "Notes must be 2000 characters or fewer."
    elif changing_password and not (current_password and new_password and confirm_password):
        error = "Fill in all three password fields to change your password."
    elif changing_password and not check_password_hash(user["password_hash"], current_password):
        error = "Current password is incorrect."
    elif changing_password and (
        len(new_password) < 8
        or not any(c.isalpha() for c in new_password)
        or not any(c.isdigit() for c in new_password)
    ):
        error = "New password must be at least 8 characters and include a letter and a number."
    elif changing_password and new_password != confirm_password:
        error = "New password and confirmation do not match."
    elif email_changed and (not bypass_code or verification_code != bypass_code):
        error = "Verification code is incorrect."
    else:
        error = None

    if error:
        return render_template(
            "profile.html",
            error=error,
            name=name,
            email=email,
            notes=notes,
            **dashboard,
        )

    try:
        update_user(
            user["id"],
            name,
            email,
            user["monthly_budget"],
            notes or None,
            password=new_password if changing_password else None,
        )
    except sqlite3.IntegrityError:
        return render_template(
            "profile.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
            notes=notes,
            **dashboard,
        )

    flash("Profile updated.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/budget", methods=["POST"])
def save_budget():
    if "user_id" not in session:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    filter_args = {
        key: request.form[key]
        for key in ("range", "start", "end")
        if request.form.get(key)
    }
    raw = request.form.get("monthly_budget", "").replace(",", "").replace(" ", "")

    if not raw:
        update_monthly_budget(session["user_id"], None)
        flash("Budget removed.", "success")
    else:
        try:
            monthly_budget = float(raw)
            valid = math.isfinite(monthly_budget) and monthly_budget >= 0
        except ValueError:
            valid = False
        if not valid:
            flash("Monthly budget must be a non-negative number.", "error")
        else:
            update_monthly_budget(session["user_id"], monthly_budget)
            flash("Budget saved.", "success")

    return redirect(url_for("profile", **filter_args))


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        flash("Please sign in to add an expense.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    today = date.today()
    page = {
        "categories": EXPENSE_CATEGORIES,
        "today": today.isoformat(),
        "budget": user["monthly_budget"],
        "month_spent": sum(
            row["total"] for row in get_monthly_spend(user["id"], today.replace(day=1), today)
        ),
    }

    if request.method == "GET":
        return render_template("add_expense.html", date=today.isoformat(), **page)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "")
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw.replace(",", "").replace(" ", ""))
        amount = round(amount, 2) if math.isfinite(amount) else None
    except ValueError:
        amount = None
    try:
        expense_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        expense_date = None

    if not amount_raw:
        error = "Please enter an amount."
    elif amount is None or amount <= 0:
        error = "Amount must be a number greater than 0."
    elif amount > MAX_EXPENSE_AMOUNT:
        error = "Amount can't be more than ₹1,00,00,000.00."
    elif category not in EXPENSE_CATEGORIES:
        error = "Please choose a category."
    elif expense_date is None:
        error = "Please enter a valid date."
    elif expense_date > today:
        error = "Date can't be in the future."
    elif len(description) > 200:
        error = "Description must be 200 characters or fewer."
    else:
        error = None

    if error:
        return render_template(
            "add_expense.html",
            error=error,
            amount=amount_raw,
            category=category,
            date=date_raw,
            description=description,
            **page,
        )

    session["new_expense_id"] = insert_expense(
        user["id"], amount, category, expense_date.isoformat(), description or None
    )
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if "user_id" not in session:
        flash("Please sign in to delete an expense.", "error")
        return redirect(url_for("login"))

    # Missing, already deleted, or someone else's: the same 404 for all three.
    if not db_delete_expense(session["user_id"], id):
        abort(404)

    filter_args = {
        key: request.form[key]
        for key in ("range", "start", "end")
        if request.form.get(key)
    }
    flash("Expense deleted.", "success")
    return redirect(url_for("profile", **filter_args))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
