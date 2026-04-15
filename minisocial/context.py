from flask import session

from .auth import load_active_session_user
from .config import MAX_IMAGES_PER_POST, MAX_POST_CONTENT_LENGTH


def build_template_context():
    active_user = load_active_session_user()
    if not active_user and "user_id" in session:
        session.clear()
    if active_user:
        session["username"] = active_user["username"]
        session["role"] = active_user["role"]

    return {
        "max_post_content_length": MAX_POST_CONTENT_LENGTH,
        "max_images_per_post": MAX_IMAGES_PER_POST,
        "current_user": {
            "id": active_user["id"] if active_user else None,
            "username": active_user["username"] if active_user else None,
            "role": active_user["role"] if active_user else None,
            "is_authenticated": active_user is not None,
        },
    }
