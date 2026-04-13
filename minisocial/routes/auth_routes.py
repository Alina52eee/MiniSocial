from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import login_required
from ..config import USERNAME_PATTERN
from ..db import get_db_connection


def _is_registration_enabled(conn):
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = 'registration_enabled'"
    ).fetchone()
    if not row:
        return True
    return str(row["value"]).strip().lower() in {"1", "true", "yes", "on"}


def register_auth_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        conn = get_db_connection(app.config["DATABASE_PATH"])
        registration_enabled = _is_registration_enabled(conn)
        if request.method == "POST":
            if not registration_enabled:
                conn.close()
                flash("Registration is currently disabled.", "error")
                return redirect(url_for("login"))

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not USERNAME_PATTERN.fullmatch(username):
                flash("Username must be 3-32 chars: letters, numbers, underscore.", "error")
                conn.close()
                return render_template("register.html", registration_enabled=registration_enabled)
            if len(password) < 8:
                flash("Password must be at least 8 characters.", "error")
                conn.close()
                return render_template("register.html", registration_enabled=registration_enabled)

            now = datetime.utcnow().isoformat(timespec="seconds")
            try:
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, status, created_at, updated_at)
                    VALUES (?, ?, 'user', 'active', ?, ?)
                    """,
                    (username, generate_password_hash(password), now, now),
                )
                conn.commit()
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except Exception:
                flash("Username is already taken.", "error")
        response = render_template("register.html", registration_enabled=registration_enabled)
        conn.close()
        return response

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            conn = get_db_connection(app.config["DATABASE_PATH"])
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone()
            conn.close()
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.", "error")
                return render_template("login.html")
            if user["status"] != "active":
                session.clear()
                flash("This account is archived.", "error")
                return render_template("login.html")
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("feed_newest"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))
