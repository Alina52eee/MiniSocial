from datetime import datetime
from urllib.parse import urlparse

from flask import flash, jsonify, redirect, request, session, url_for

from ..auth import current_user_can_manage_post, login_required
from ..config import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_IMAGE_URL_LENGTH,
    MAX_IMAGES_PER_POST,
    MAX_POST_CONTENT_LENGTH,
    MAX_POST_IMAGE_BYTES,
)
from ..db import get_db_connection
from ..services.feed import toggle_post_like


def _valid_image_url(value: str) -> bool:
    if not value or len(value) > MAX_IMAGE_URL_LENGTH:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def register_post_routes(app):
    @app.post("/create-post")
    @login_required
    def create_post():
        content = request.form.get("content", "").strip()
        if not content:
            flash("Текст поста не может быть пустым.", "error")
            return redirect(url_for("feed_newest"))
        if len(content) > MAX_POST_CONTENT_LENGTH:
            flash("Текст поста слишком длинный.", "error")
            return redirect(url_for("feed_newest"))

        raw_gallery_count = request.form.get("gallery_count", "0")
        try:
            gallery_count = int(raw_gallery_count or 0)
        except (TypeError, ValueError):
            flash("Некорректная конфигурация галереи.", "error")
            return redirect(url_for("feed_newest"))
        if gallery_count < 0:
            flash("Некорректная конфигурация галереи.", "error")
            return redirect(url_for("feed_newest"))
        gallery_count = min(gallery_count, MAX_IMAGES_PER_POST)
        items = []
        for i in range(gallery_count):
            kind = request.form.get(f"gallery_kind_{i}", "")
            if kind == "url":
                value = request.form.get(f"gallery_url_{i}", "").strip()
                if not _valid_image_url(value):
                    flash("Некорректный URL изображения.", "error")
                    return redirect(url_for("feed_newest"))
                items.append({"position": i, "image_url": value, "image_blob": None, "image_mime": None})
            elif kind == "file":
                upload = request.files.get(f"gallery_file_{i}")
                if not upload or not upload.filename:
                    continue
                mime = (upload.mimetype or "").lower()
                if mime not in ALLOWED_IMAGE_MIME_TYPES:
                    flash("Неподдерживаемый формат изображения.", "error")
                    return redirect(url_for("feed_newest"))
                data = upload.read(MAX_POST_IMAGE_BYTES + 1)
                if len(data) > MAX_POST_IMAGE_BYTES:
                    flash("Загруженное изображение слишком большое.", "error")
                    return redirect(url_for("feed_newest"))
                items.append({"position": i, "image_url": None, "image_blob": data, "image_mime": mime})

        now = datetime.utcnow().isoformat(timespec="seconds")
        conn = get_db_connection(app.config["DATABASE_PATH"])
        cur = conn.execute(
            """
            INSERT INTO posts (content, likes, created_at, updated_at, author_id, author_name_snapshot, author_state)
            VALUES (?, 0, ?, ?, ?, ?, 'active')
            """,
            (content, now, now, session["user_id"], session["username"]),
        )
        post_id = cur.lastrowid
        for item in items:
            conn.execute(
                """
                INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (post_id, item["position"], item["image_blob"], item["image_mime"], item["image_url"]),
            )
        conn.commit()
        conn.close()
        flash("Пост создан.", "success")
        return redirect(url_for("feed_newest"))

    @app.post("/delete-post/<int:post_id>")
    @login_required
    def delete_post(post_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        post = conn.execute("SELECT author_id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            conn.close()
            flash("Пост не найден.", "error")
            return redirect(url_for("feed_newest"))
        if not current_user_can_manage_post(post["author_id"]):
            conn.close()
            flash("Вы не можете удалить этот пост.", "error")
            return redirect(url_for("feed_newest"))

        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        flash("Пост удалён.", "success")
        return redirect(url_for("feed_newest"))

    @app.post("/like-post/<int:post_id>")
    @login_required
    def like_post(post_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        exists = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not exists:
            conn.close()
            flash("Пост не найден.", "error")
            return redirect(url_for("feed_newest"))
        toggle_post_like(conn, post_id, session["user_id"])
        conn.commit()
        conn.close()
        return redirect(request.referrer or url_for("feed_newest"))

    @app.post("/api/posts/<int:post_id>/like")
    @login_required
    def api_like_post(post_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        exists = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not exists:
            conn.close()
            return jsonify({"ok": False, "error": "not_found"}), 404
        liked, likes = toggle_post_like(conn, post_id, session["user_id"])
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "likes": likes, "liked": liked})
