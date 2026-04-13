from pathlib import Path

from flask import Flask

from .config import build_flask_config
from .context import build_template_context
from .db import init_db
from .routes.admin import register_admin_routes
from .routes.auth_routes import register_auth_routes
from .routes.feed_routes import register_feed_routes
from .routes.media_routes import register_media_routes
from .routes.post_routes import register_post_routes


def create_app():
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config.update(build_flask_config())

    @app.context_processor
    def inject_shared_context():
        return build_template_context()

    with app.app_context():
        init_db(app)
        if not app.config.get("MINISOCIAL_SKIP_AUTO_DEMO_SEED", False):
            try:
                from seed_demo import run_demo_seed

                run_demo_seed(app, auto=True)
            except Exception:
                pass

    register_feed_routes(app)
    register_auth_routes(app)
    register_post_routes(app)
    register_media_routes(app)
    register_admin_routes(app)
    return app
