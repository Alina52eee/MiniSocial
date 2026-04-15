from functools import wraps

from flask import current_app, flash, redirect, session, url_for

from .db import get_db_connection


def load_active_session_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None

    conn = get_db_connection(current_app.config["DATABASE_PATH"])
    user = conn.execute(
        """
        SELECT id, username, role, status
          FROM users
         WHERE id = ?
         LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not user or user["status"] != "active":
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = load_active_session_user()
        if not user:
            session.clear()
            flash("Сначала войдите в аккаунт.", "warning")
            return redirect(url_for("login"))
        session["username"] = user["username"]
        session["role"] = user["role"]
        return view(*args, **kwargs)

    return wrapped


def admin_or_master_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = load_active_session_user()
        if not user:
            session.clear()
            flash("Сначала войдите в аккаунт.", "warning")
            return redirect(url_for("login"))
        session["username"] = user["username"]
        session["role"] = user["role"]
        if user["role"] not in {"admin", "master"}:
            flash("Нужен доступ администратора.", "error")
            return redirect(url_for("feed_newest"))
        return view(*args, **kwargs)

    return wrapped


def master_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = load_active_session_user()
        if not user:
            session.clear()
            flash("Сначала войдите в аккаунт.", "warning")
            return redirect(url_for("login"))
        session["username"] = user["username"]
        session["role"] = user["role"]
        if user["role"] != "master":
            flash("Нужен доступ главного администратора.", "error")
            return redirect(url_for("admin_page"))
        return view(*args, **kwargs)

    return wrapped


def current_user_can_manage_post(post_author_id: int | None) -> bool:
    user = load_active_session_user()
    if not user:
        return False
    if user["role"] in {"admin", "master"}:
        return True
    return post_author_id is not None and post_author_id == user["id"]
