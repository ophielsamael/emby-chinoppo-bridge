"""
Xnoppo — Emby ↔ Oppo 203 Bridge Client
Main application entry point.
"""

import sys
import logging
import logging.handlers
import threading
from pathlib import Path
from flask import Flask

from config import XnoppoConfig

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = BASE_DIR / "xnoppo.log"
LANG_DIR = BASE_DIR / "lang"
TV_LIB_DIR = BASE_DIR / "web" / "libraries" / "TV"
AV_LIB_DIR = BASE_DIR / "web" / "libraries" / "AV"

# ─── App Factory ──────────────────────────────────────────────────────────────

def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Load configuration
    config = XnoppoConfig.load(CONFIG_FILE)
    app.config["XNOPPO"] = config
    app.config["BASE_DIR"] = BASE_DIR

    # ── Logging setup ─────────────────────────────────────────────────────
    setup_logging(config)

    # ── Register blueprints ───────────────────────────────────────────────
    from routes.pages import pages_bp
    from routes.api import api_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # ── Start WebSocket thread (Emby listener) ────────────────────────────
    from lib.ws_launcher import start_ws_thread
    start_ws_thread(config)

    logging.info("Xnoppo v%s started", config.get_version())
    return app


def setup_logging(config: XnoppoConfig):
    """Configure or reconfigure logging based on DebugLevel in config."""
    debug_level = int(config.get("DebugLevel", 0))
    fmt = "%(asctime)s %(levelname)s [%(name)s]: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        
    if debug_level == 0:
        root.setLevel(logging.WARNING)
    else:
        level = logging.INFO if debug_level == 1 else logging.DEBUG
        root.setLevel(level)
        
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=2,
    )
    handler.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(handler)
    
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(console)

    logging.info("Logging reconfigured: Level %s (DebugLevel %s)", logging.getLevelName(root.level), debug_level)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = create_app()
    port = 8090
    print(f"\n  * Xnoppo v{XnoppoConfig.get_version()} running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
