import sqlite3
import struct
from datetime import datetime

from werkzeug.security import generate_password_hash

from .config import AVATAR_MIME


def get_db_connection(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def validate_png_dimensions(data: bytes, width: int, height: int) -> bool:
    if len(data) < 24:
        return False
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    if data[12:16] != b"IHDR":
        return False
    w, h = struct.unpack(">II", data[16:24])
    return (w, h) == (width, height)


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def sync_post_like_counts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE posts
           SET likes = (
            SELECT COUNT(*)
              FROM post_likes
             WHERE post_likes.post_id = posts.id
           )
        """
    )


def _ensure_master_account(conn: sqlite3.Connection, username: str, password: str) -> None:
    exists = conn.execute("SELECT id FROM users WHERE role = 'master' LIMIT 1").fetchone()
    if exists:
        return
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, status, created_at, updated_at)
        VALUES (?, ?, 'master', 'active', ?, ?)
        """,
        (username, generate_password_hash(password), now, now),
    )


def init_db(app) -> None:
    conn = get_db_connection(app.config["DATABASE_PATH"])
    now = datetime.utcnow().isoformat(timespec="seconds")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            avatar_blob BLOB,
            avatar_mime TEXT
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            author_id INTEGER,
            author_name_snapshot TEXT,
            author_state TEXT NOT NULL DEFAULT 'active',
            content_backup TEXT,
            image_blob BLOB,
            image_mime TEXT,
            image_url TEXT,
            FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(post_id, user_id),
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS post_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            image_blob BLOB,
            image_mime TEXT,
            image_url TEXT,
            UNIQUE(post_id, position),
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
        );
        """
    )

    if _column_exists(conn, "users", "role"):
        conn.execute("UPDATE users SET role = 'master' WHERE role = 'master_admin'")

    reg_row = conn.execute(
        "SELECT value FROM app_settings WHERE key = 'registration_enabled'"
    ).fetchone()
    if reg_row is None:
        value = "1" if app.config["REGISTRATION_ENABLED_DEFAULT"] else "0"
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES ('registration_enabled', ?)",
            (value,),
        )

    # Migrate legacy single image fields into post_images.
    legacy_posts = conn.execute(
        """
        SELECT id, image_blob, image_mime, image_url
          FROM posts
         WHERE (image_blob IS NOT NULL OR image_url IS NOT NULL)
        """
    ).fetchall()
    for row in legacy_posts:
        has_slot0 = conn.execute(
            "SELECT id FROM post_images WHERE post_id = ? AND position = 0",
            (row["id"],),
        ).fetchone()
        if not has_slot0:
            conn.execute(
                """
                INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
                VALUES (?, 0, ?, ?, ?)
                """,
                (row["id"], row["image_blob"], row["image_mime"], row["image_url"]),
            )

    _ensure_master_account(
        conn,
        app.config["MASTER_ADMIN_USERNAME"],
        app.config["MASTER_ADMIN_PASSWORD"],
    )
    sync_post_like_counts(conn)

    conn.execute(
        """
        UPDATE users
           SET updated_at = COALESCE(updated_at, ?),
               status = COALESCE(status, 'active'),
               role = COALESCE(role, 'user'),
               avatar_mime = CASE
                                WHEN avatar_blob IS NOT NULL AND avatar_mime IS NULL THEN ?
                                ELSE avatar_mime
                             END
        """,
        (now, AVATAR_MIME),
    )
    conn.commit()
    conn.close()
