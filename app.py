import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime, date

from helpers import apology, login_required  # reuse helpers.py from Finance

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///habit_tracker.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# ----------------------
# ROUTES
# ----------------------

@app.route("/")
@login_required
def index():
    """Dashboard: show all habits and today's status"""

    user_id = session["user_id"]

    # Get all habits for user
    habits = db.execute("SELECT * FROM habits WHERE user_id = ?", user_id)

    today_str = date.today().isoformat()

    dashboard = []
    for habit in habits:
        # Check if habit done today
        log = db.execute("SELECT done FROM habit_logs WHERE habit_id = ? AND date = ?", habit["id"], today_str)
        done_today = log[0]["done"] if log else 0

        dashboard.append({
            "id": habit["id"],
            "name": habit["name"],
            "description": habit["description"],
            "done_today": done_today
        })

    return render_template("index.html", habits=dashboard)

# ----------------------
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add a new habit"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            return apology("must provide habit name")

        user_id = session["user_id"]
        db.execute("INSERT INTO habits (user_id, name, description) VALUES (?, ?, ?)",
                   user_id, name, description)

        flash("Habit added!")
        return redirect("/")

    return render_template("add.html")

# ----------------------
@app.route("/track", methods=["POST"])
@login_required
def track():
    """Mark a habit done for today"""
    habit_id = request.form.get("habit_id")
    if not habit_id:
        return apology("invalid habit")

    habit_id = int(habit_id)
    today_str = date.today().isoformat()

    # Check if already logged
    log = db.execute("SELECT * FROM habit_logs WHERE habit_id = ? AND date = ?", habit_id, today_str)
    if log:
        # toggle done status
        done = 0 if log[0]["done"] else 1
        db.execute("UPDATE habit_logs SET done = ? WHERE id = ?", done, log[0]["id"])
    else:
        # create log for today
        db.execute("INSERT INTO habit_logs (habit_id, date, done) VALUES (?, ?, ?)", habit_id, today_str, 1)

    return redirect("/")

# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username")
        if not password:
            return apology("must provide password")
        if password != confirmation:
            return apology("passwords must match")

        # check if username exists
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 0:
            return apology("username already taken")

        # hash password
        hash_pw = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash_pw)

        # log user in
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("must provide username")
        if not password:
            return apology("must provide password")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username or password")

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/login")
