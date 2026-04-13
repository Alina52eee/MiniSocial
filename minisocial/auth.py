from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_or_master_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") not in {"admin", "master"}:
            flash("Admin access required.", "error")
            return redirect(url_for("feed_newest"))
        return view(*args, **kwargs)

    return wrapped


def master_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "master":
            flash("Master admin access required.", "error")
            return redirect(url_for("admin_page"))
        return view(*args, **kwargs)

    return wrapped


def current_user_can_manage_post(post_author_id: int | None) -> bool:
    if "user_id" not in session:
        return False
    if session.get("role") in {"admin", "master"}:
        return True
    return post_author_id is not None and post_author_id == session.get("user_id")
