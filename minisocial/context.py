from flask import session

from .config import MAX_IMAGES_PER_POST, MAX_POST_CONTENT_LENGTH


def build_template_context():
    return {
        "max_post_content_length": MAX_POST_CONTENT_LENGTH,
        "max_images_per_post": MAX_IMAGES_PER_POST,
        "current_user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("role"),
            "is_authenticated": "user_id" in session,
        },
    }
