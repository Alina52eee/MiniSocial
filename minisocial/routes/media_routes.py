from flask import abort, make_response, request, session

from ..auth import login_required
from ..config import (
    ALLOWED_IMAGE_MIME_TYPES,
    AVATAR_MIME,
    MAX_AVATAR_BYTES,
    MAX_IMAGES_PER_POST,
    PIXEL_ART_SIZE,
)
from ..db import get_db_connection, validate_png_dimensions


def register_media_routes(app):
    @app.get("/user-avatar/<int:user_id>")
    def user_avatar(user_id: int):
        conn = get_db_connection(app.config["DATABASE_PATH"])
        user = conn.execute(
            """
            SELECT avatar_blob, avatar_mime, status
              FROM users
             WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        conn.close()
        if (
            not user
            or user["status"] != "active"
            or not user["avatar_blob"]
            or user["avatar_mime"] != AVATAR_MIME
        ):
            abort(404)

        resp = make_response(user["avatar_blob"])
        resp.headers["Content-Type"] = AVATAR_MIME
        resp.headers["Cache-Control"] = "private, no-cache"
        return resp

    @app.post("/profile/avatar")
    @login_required
    def upload_avatar():
        upload = request.files.get("avatar")
        if not upload or not upload.filename:
            abort(400)
        # Some browsers send generic MIME for canvas-generated files.
        # Trust validated PNG signature + dimensions below.
        data = upload.read(MAX_AVATAR_BYTES + 1)
        if len(data) > MAX_AVATAR_BYTES:
            abort(400)
        if not validate_png_dimensions(data, PIXEL_ART_SIZE, PIXEL_ART_SIZE):
            abort(400)

        conn = get_db_connection(app.config["DATABASE_PATH"])
        conn.execute(
            "UPDATE users SET avatar_blob = ?, avatar_mime = ? WHERE id = ?",
            (data, AVATAR_MIME, session["user_id"]),
        )
        conn.commit()
        conn.close()
        return ("", 204)

    @app.get("/post-image/<int:post_id>/<int:slot>")
    def post_image(post_id: int, slot: int):
        if slot < 0 or slot >= MAX_IMAGES_PER_POST:
            abort(404)
        conn = get_db_connection(app.config["DATABASE_PATH"])
        row = conn.execute(
            """
            SELECT pi.image_blob, pi.image_mime, p.author_state
              FROM post_images pi
              JOIN posts p ON p.id = pi.post_id
             WHERE pi.post_id = ? AND pi.position = ?
            """,
            (post_id, slot),
        ).fetchone()
        conn.close()
        if (
            not row
            or not row["image_blob"]
            or not row["image_mime"]
            or row["image_mime"] not in ALLOWED_IMAGE_MIME_TYPES
            or row["author_state"] != "active"
        ):
            abort(404)

        resp = make_response(row["image_blob"])
        resp.headers["Content-Type"] = row["image_mime"]
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
