from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from ..auth import admin_or_master_required, master_required
from ..config import USERNAME_PATTERN
from ..db import get_db_connection
from ..services.feed import count_master_accounts


def _target_user(conn, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _set_registration_enabled(conn, enabled: bool):
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES ('registration_enabled', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("1" if enabled else "0",),
    )


def _can_manage_actor(actor_role: str, target_role: str) -> bool:
    if actor_role == "master":
        return target_role in {"admin", "user"}
    if actor_role == "admin":
        return target_role == "user"
    return False


def register_admin_routes(app):
    @app.get("/admin")
    @admin_or_master_required
    def admin_page():
        conn = get_db_connection(app.config["DATABASE_PATH"])
        users = conn.execute(
            """
            SELECT id, username, role, status, created_at
              FROM users
             ORDER BY CASE role WHEN 'master' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, username
            """
        ).fetchall()
        reg = conn.execute(
            "SELECT value FROM app_settings WHERE key='registration_enabled'"
        ).fetchone()
        conn.close()
        registration_enabled = (reg["value"] if reg else "1") in {"1", "true", "yes", "on"}
        return render_template(
            "admin.html",
            users=users,
            registration_enabled=registration_enabled,
            can_manage_master_controls=session.get("role") == "master",
        )

    @app.post("/admin/toggle-registration")
    @master_required
    def toggle_registration():
        action = request.form.get("action", "")
        conn = get_db_connection(app.config["DATABASE_PATH"])
        _set_registration_enabled(conn, action == "on")
        conn.commit()
        conn.close()
        flash("Registration settings updated.", "success")
        return redirect(url_for("admin_page"))

    @app.post("/admin/create-user")
    @master_required
    def create_user():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        if role not in {"user", "admin"}:
            flash("Invalid role.", "error")
            return redirect(url_for("admin_page"))
        if not USERNAME_PATTERN.fullmatch(username):
            flash("Invalid username.", "error")
            return redirect(url_for("admin_page"))
        if len(password) < 8:
            flash("Password too short.", "error")
            return redirect(url_for("admin_page"))
        now = datetime.utcnow().isoformat(timespec="seconds")
        conn = get_db_connection(app.config["DATABASE_PATH"])
        try:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, role, status, created_at, updated_at)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (username, generate_password_hash(password), role, now, now),
            )
            conn.commit()
            flash("User created.", "success")
        except Exception:
            flash("Username already exists.", "error")
        finally:
            conn.close()
        return redirect(url_for("admin_page"))

    @app.post("/admin/users/<int:user_id>/archive")
    @admin_or_master_required
    def archive_user(user_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        user = _target_user(conn, user_id)
        if not user:
            conn.close()
            flash("User not found.", "error")
            return redirect(url_for("admin_page"))
        if user["id"] == session.get("user_id") or user["role"] == "master":
            conn.close()
            flash("This user cannot be archived.", "error")
            return redirect(url_for("admin_page"))
        if not _can_manage_actor(session.get("role"), user["role"]):
            conn.close()
            flash("Insufficient permissions.", "error")
            return redirect(url_for("admin_page"))
        if user["role"] == "master" and count_master_accounts(conn) <= 1:
            conn.close()
            flash("Cannot archive the last master account.", "error")
            return redirect(url_for("admin_page"))

        conn.execute("UPDATE users SET status='archived' WHERE id = ?", (user_id,))
        conn.execute(
            """
            UPDATE posts
               SET content_backup = CASE WHEN content_backup IS NULL THEN content ELSE content_backup END,
                   content = '[post from archived user]',
                   author_state = 'archived'
             WHERE author_id = ?
            """,
            (user_id,),
        )
        conn.commit()
        conn.close()
        flash("User archived.", "success")
        return redirect(url_for("admin_page"))

    @app.post("/admin/users/<int:user_id>/restore")
    @admin_or_master_required
    def restore_user(user_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        user = _target_user(conn, user_id)
        if not user:
            conn.close()
            flash("User not found.", "error")
            return redirect(url_for("admin_page"))
        if not _can_manage_actor(session.get("role"), user["role"]):
            conn.close()
            flash("Insufficient permissions.", "error")
            return redirect(url_for("admin_page"))

        conn.execute("UPDATE users SET status='active' WHERE id = ?", (user_id,))
        conn.execute(
            """
            UPDATE posts
               SET content = COALESCE(content_backup, content),
                   content_backup = NULL,
                   author_state = 'active'
             WHERE author_id = ? AND author_state = 'archived'
            """,
            (user_id,),
        )
        conn.commit()
        conn.close()
        flash("User restored.", "success")
        return redirect(url_for("admin_page"))

    @app.post("/admin/users/<int:user_id>/delete")
    @admin_or_master_required
    def delete_user(user_id: int):
        if session.get("role") != "master":
            flash("Only master can permanently delete users.", "error")
            return redirect(url_for("admin_page"))

        conn = get_db_connection(app.config["DATABASE_PATH"])
        user = _target_user(conn, user_id)
        if not user:
            conn.close()
            flash("User not found.", "error")
            return redirect(url_for("admin_page"))
        if user["id"] == session.get("user_id") or user["role"] == "master":
            conn.close()
            flash("This account cannot be deleted.", "error")
            return redirect(url_for("admin_page"))

        conn.execute(
            """
            UPDATE posts
               SET author_id = NULL,
                   author_name_snapshot = 'user deleted',
                   content_backup = CASE WHEN content_backup IS NULL THEN content ELSE content_backup END,
                   content = '[post from deleted user]',
                   author_state = 'deleted'
             WHERE author_id = ?
            """,
            (user_id,),
        )
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("User deleted.", "success")
        return redirect(url_for("admin_page"))
