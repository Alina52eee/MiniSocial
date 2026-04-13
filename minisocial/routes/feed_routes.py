from flask import redirect, render_template, session, url_for

from ..db import get_db_connection
from ..services.feed import fetch_posts


def register_feed_routes(app):
    @app.get("/")
    def root():
        return redirect(url_for("feed_newest"))

    @app.get("/feed/newest")
    def feed_newest():
        conn = get_db_connection(app.config["DATABASE_PATH"])
        posts = fetch_posts(conn, "newest", session.get("user_id"))
        conn.close()
        return render_template("index.html", posts=posts, feed_type="newest")

    @app.get("/feed/trending")
    def feed_trending():
        conn = get_db_connection(app.config["DATABASE_PATH"])
        posts = fetch_posts(conn, "trending", session.get("user_id"))
        conn.close()
        return render_template("index.html", posts=posts, feed_type="trending")
