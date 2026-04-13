import os
import random
import sqlite3
import struct
import zlib
from datetime import datetime

from werkzeug.security import generate_password_hash

from minisocial.config import env_truthy
from minisocial.db import get_db_connection, sync_post_like_counts

SNIPPETS = [
    "Hello from demo seed.",
    "SQLite + Flask is cozy.",
    "Pixel art avatars are fun.",
    "Trending feed test post.",
    "This is a random seeded post.",
]


def _png_8x8_random() -> bytes:
    width, height = 8, 8
    raw = bytearray()
    for _y in range(height):
        raw.append(0)
        for _x in range(width):
            raw.extend([random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _setting(conn: sqlite3.Connection, key: str):
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_setting(conn: sqlite3.Connection, key: str, value: str):
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def run_demo_seed(app, auto: bool = False):
    if not env_truthy("DEMO_SEED_ENABLED", False):
        return
    conn = get_db_connection(app.config["DATABASE_PATH"])
    conn.execute("BEGIN IMMEDIATE")

    forced = env_truthy("DEMO_SEED_FORCE", False) and not auto
    if _setting(conn, "demo_seed_v1") == "1" and not forced:
        conn.commit()
        conn.close()
        return

    if forced:
        demo_ids = [
            r["id"]
            for r in conn.execute("SELECT id FROM users WHERE username LIKE 'demo_seed_%'").fetchall()
        ]
        if demo_ids:
            placeholders = ",".join(["?"] * len(demo_ids))
            conn.execute(f"DELETE FROM users WHERE id IN ({placeholders})", demo_ids)

    total_users = max(2, int(os.getenv("DEMO_SEED_USERS", "6")))
    now = datetime.utcnow().isoformat(timespec="seconds")
    password_hash = generate_password_hash("DemoSeed123!")
    users = []
    for i in range(total_users):
        username = f"demo_seed_{i:02d}"
        try:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, role, status, created_at, updated_at, avatar_blob, avatar_mime)
                VALUES (?, ?, 'user', 'active', ?, ?, ?, 'image/png')
                """,
                (username, password_hash, now, now, _png_8x8_random()),
            )
            users.append(cur.lastrowid)
        except Exception:
            row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                users.append(row["id"])

    post_ids = []
    for uid in users:
        uname = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()["username"]
        for pos in range(random.randint(2, 5)):
            content = random.choice(SNIPPETS)
            cur = conn.execute(
                """
                INSERT INTO posts (content, likes, created_at, updated_at, author_id, author_name_snapshot, author_state)
                VALUES (?, 0, ?, ?, ?, ?, 'active')
                """,
                (content, now, now, uid, uname),
            )
            post_id = cur.lastrowid
            post_ids.append(post_id)
            for slot in range(random.randint(0, 4)):
                conn.execute(
                    """
                    INSERT INTO post_images (post_id, position, image_blob, image_mime)
                    VALUES (?, ?, ?, 'image/png')
                    """,
                    (post_id, slot, _png_8x8_random()),
                )

    for pid in post_ids:
        random.shuffle(users)
        for uid in users[: random.randint(0, min(4, len(users)) )]:
            author = conn.execute("SELECT author_id FROM posts WHERE id = ?", (pid,)).fetchone()["author_id"]
            if uid == author:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO post_likes (post_id, user_id, created_at)
                VALUES (?, ?, ?)
                """,
                (pid, uid, now),
            )

    sync_post_like_counts(conn)
    _set_setting(conn, "demo_seed_v1", "1")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    from minisocial import create_app

    app = create_app()
    with app.app_context():
        run_demo_seed(app, auto=False)
    print("Demo seed completed")
