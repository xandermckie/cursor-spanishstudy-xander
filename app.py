"""Estudio Personal — Flask skeleton (routes stubbed, no business logic yet)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

import fetcher
from scheduler import init_scheduler

load_dotenv()

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_FILE = DATA_DIR / "cache.json"


def ensure_cache_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        CACHE_FILE.write_text("{}", encoding="utf-8")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ensure_cache_file()

    interval = int(os.environ.get("REFRESH_INTERVAL_MINUTES", "15"))
    scheduler_on = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    init_scheduler(app, interval_minutes=interval, enabled=scheduler_on)

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.route("/")
    def home():
        homepage = fetcher.get_homepage()
        return render_template(
            "index.html",
            page="home",
            title="Estudio Personal",
            homepage=homepage,
        )

    @app.route("/reader")
    def reader():
        reader_data = fetcher.get_reader()
        return render_template(
            "reader.html",
            page="reader",
            title="Fog-reveal reader",
            reader=reader_data,
        )

    @app.route("/vocab")
    def vocab():
        category = request.args.get("category", "")
        return render_template(
            "index.html",
            page="vocab",
            title="Vocabulary",
            message=f"Vocab browser placeholder{f' (category: {category})' if category else ''}.",
        )

    @app.route("/quiz")
    def quiz():
        return render_template(
            "index.html",
            page="quiz",
            title="Quiz",
            message="Quiz placeholder — Open Trivia DB + vocab questions will go here.",
        )

    @app.route("/phrasebook", methods=["GET", "POST"])
    def phrasebook():
        if request.method == "POST":
            return render_template(
                "index.html",
                page="phrasebook",
                title="Phrasebook",
                message="POST /phrasebook placeholder — phrase saving not implemented yet.",
            )
        return render_template(
            "index.html",
            page="phrasebook",
            title="Phrasebook",
            message="Phrasebook placeholder — your saved phrases will appear here.",
        )

    @app.route("/refresh")
    def refresh():
        fetcher.run_refresh()
        return redirect(url_for("home"))

    @app.route("/export")
    def export():
        return render_template(
            "index.html",
            page="export",
            title="Export",
            message="Export placeholder — CSV download of phrasebook will go here.",
        )


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
