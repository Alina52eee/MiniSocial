import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IS_PRODUCTION = os.getenv("FLASK_ENV", "").lower() == "production"

MAX_POST_CONTENT_LENGTH = 280
MAX_POST_IMAGE_BYTES = 300 * 1024
MAX_IMAGES_PER_POST = 4
MAX_IMAGE_URL_LENGTH = 1024
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PIXEL_ART_SIZE = 8
MAX_AVATAR_BYTES = 64 * 1024
AVATAR_MIME = "image/png"
TRENDING_LIKE_WEIGHT = 3.0
TRENDING_DECAY_PER_HOUR = 0.25


def env_truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_flask_config() -> dict:
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if IS_PRODUCTION and not secret_key:
        raise RuntimeError("FLASK_SECRET_KEY is required in production")
    if not secret_key:
        secret_key = "dev-only-insecure-secret-key"

    master_username = os.getenv("MASTER_ADMIN_USERNAME", "admin")
    master_password = os.getenv("MASTER_ADMIN_PASSWORD", "admin12345")
    if IS_PRODUCTION and (not master_username or not master_password):
        raise RuntimeError(
            "MASTER_ADMIN_USERNAME and MASTER_ADMIN_PASSWORD are required in production"
        )

    return {
        "SECRET_KEY": secret_key,
        "DATABASE_PATH": str(BASE_DIR / os.getenv("DATABASE_PATH", "minisocial.db")),
        "REGISTRATION_ENABLED_DEFAULT": env_truthy("REGISTRATION_ENABLED_DEFAULT", True),
        "MASTER_ADMIN_USERNAME": master_username,
        "MASTER_ADMIN_PASSWORD": master_password,
        "MINISOCIAL_AUTO_DEMO_SEED": env_truthy("MINISOCIAL_AUTO_DEMO_SEED", False),
        "MINISOCIAL_SKIP_AUTO_DEMO_SEED": env_truthy("MINISOCIAL_SKIP_AUTO_DEMO_SEED", False),
    }
