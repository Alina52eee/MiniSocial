from datetime import datetime

from ..config import TRENDING_DECAY_PER_HOUR, TRENDING_LIKE_WEIGHT


def count_master_accounts(conn) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role='master'").fetchone()
    return int(row["c"])


def attach_post_galleries(conn, posts: list[dict]) -> list[dict]:
    if not posts:
        return posts
    ids = [post["id"] for post in posts]
    placeholders = ",".join(["?"] * len(ids))
    rows = conn.execute(
        f"""
        SELECT post_id, position, image_url, image_mime,
               CASE WHEN image_blob IS NULL THEN 0 ELSE 1 END AS has_blob
          FROM post_images
         WHERE post_id IN ({placeholders})
         ORDER BY post_id, position
        """,
        ids,
    ).fetchall()
    grouped = {post_id: [] for post_id in ids}
    for row in rows:
        grouped[row["post_id"]].append(dict(row))
    for post in posts:
        post["gallery"] = grouped.get(post["id"], [])
    return posts


def fetch_posts(conn, feed_type: str, current_user_id: int | None):
    user_id = current_user_id or -1
    base_sql = """
        SELECT
            p.id,
            p.content,
            p.likes,
            p.created_at,
            p.updated_at,
            p.author_id,
            p.author_name_snapshot,
            p.author_state,
            u.username AS author_username,
            CASE WHEN u.avatar_blob IS NULL THEN 0 ELSE 1 END AS author_has_avatar,
            CASE WHEN ul.id IS NULL THEN 0 ELSE 1 END AS liked_by_current_user
        FROM posts p
        LEFT JOIN users u ON u.id = p.author_id
        LEFT JOIN post_likes ul ON ul.post_id = p.id AND ul.user_id = ?
    """
    if feed_type == "trending":
        sql = f"""
            SELECT feed_data.*,
                   ROUND(
                       feed_data.likes * {TRENDING_LIKE_WEIGHT} -
                       ((julianday('now') - julianday(feed_data.created_at)) * 24 * {TRENDING_DECAY_PER_HOUR}),
                       2
                   ) AS trending_score
              FROM ({base_sql}) AS feed_data
             ORDER BY trending_score DESC, created_at DESC, id DESC
        """
    else:
        sql = f"""
            SELECT feed_data.*, NULL AS trending_score
              FROM ({base_sql}) AS feed_data
             ORDER BY created_at DESC, id DESC
        """

    posts = [dict(row) for row in conn.execute(sql, (user_id,)).fetchall()]
    return attach_post_galleries(conn, posts)


def toggle_post_like(conn, post_id: int, user_id: int):
    now = datetime.utcnow().isoformat(timespec="seconds")
    existing = conn.execute(
        "SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM post_likes WHERE id = ?", (existing["id"],))
        conn.execute(
            "UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id = ?",
            (post_id,),
        )
        row = conn.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()
        return False, int(row["likes"])

    conn.execute(
        "INSERT INTO post_likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
        (post_id, user_id, now),
    )
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    row = conn.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()
    return True, int(row["likes"])
