import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_db,
    get_monthly_category_totals,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    update_user,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

with app.app_context():
    init_db()
    seed_db()


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


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    category_totals = get_monthly_category_totals(user["id"])
    monthly_total = sum(row["total"] for row in category_totals)
    recent_expenses = get_recent_expenses(user["id"], 5)
    member_since = datetime.strptime(
        user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%b %Y")

    if request.method == "GET":
        return render_template(
            "profile.html",
            name=user["name"],
            email=user["email"],
            monthly_budget=(
                "" if user["monthly_budget"] is None else f"{user['monthly_budget']:g}"
            ),
            notes=user["notes"] or "",
            member_since=member_since,
            category_totals=category_totals,
            monthly_total=monthly_total,
            recent_expenses=recent_expenses,
            original_email=user["email"],
            budget_amount=user["monthly_budget"],
        )

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    monthly_budget_raw = request.form.get("monthly_budget", "").strip()
    notes = request.form.get("notes", "").strip()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    verification_code = request.form.get("verification_code", "")

    monthly_budget = None
    budget_error = False
    if monthly_budget_raw:
        try:
            monthly_budget = float(monthly_budget_raw)
            if monthly_budget < 0:
                budget_error = True
        except ValueError:
            budget_error = True

    changing_password = bool(current_password or new_password or confirm_password)
    email_changed = email != user["email"]
    bypass_code = os.environ.get("PROFILE_EMAIL_BYPASS_CODE")

    if not name:
        error = "Name is required."
    elif "@" not in email:
        error = "Please enter a valid email address."
    elif budget_error:
        error = "Monthly budget must be a non-negative number."
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
            monthly_budget=monthly_budget_raw,
            notes=notes,
            member_since=member_since,
            category_totals=category_totals,
            monthly_total=monthly_total,
            recent_expenses=recent_expenses,
            original_email=user["email"],
            budget_amount=user["monthly_budget"],
        )

    try:
        update_user(
            user["id"],
            name,
            email,
            monthly_budget,
            notes or None,
            password=new_password if changing_password else None,
        )
    except sqlite3.IntegrityError:
        return render_template(
            "profile.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
            monthly_budget=monthly_budget_raw,
            notes=notes,
            member_since=member_since,
            category_totals=category_totals,
            monthly_total=monthly_total,
            recent_expenses=recent_expenses,
            original_email=user["email"],
            budget_amount=user["monthly_budget"],
        )

    flash("Profile updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
