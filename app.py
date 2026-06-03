"""Estudio Abroad — Flask app for Barcelona Spanish study."""

from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_file, url_for

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
            title="Inicio",
            homepage=homepage,
        )

    @app.route("/reader")
    def reader():
        reader_data = fetcher.get_reader()
        return render_template(
            "reader.html",
            page="reader",
            title="Lector",
            reader=reader_data,
        )

    @app.route("/vocab")
    def vocab():
        idx = request.args.get("i", 0, type=int)
        session = fetcher.get_vocab_session(idx)
        return render_template(
            "vocab.html",
            page="vocab",
            title="Tarjetas",
            session=session,
        )

    @app.route("/vocab/record", methods=["POST"])
    def vocab_record():
        es = request.form.get("es", "")
        en = request.form.get("en", "")
        missed = request.form.get("missed") == "1"
        next_i = request.form.get("next_i", 0, type=int)
        fetcher.record_flashcard_result(es, en, missed)
        return redirect(url_for("vocab", i=next_i))

    @app.route("/phrasebook", methods=["GET", "POST"])
    def phrasebook():
        if request.method == "POST":
            text = request.form.get("input", "").strip()
            if not text:
                flash("Escribe una frase en inglés.", "warning")
            else:
                fetcher.add_phrase(text)
                flash("Frase guardada.", "success")
            return redirect(url_for("phrasebook"))

        phrases = fetcher.get_phrasebook()
        return render_template(
            "phrasebook.html",
            page="phrasebook",
            title="Libro de frases",
            phrases=phrases,
        )

    @app.route("/phrasebook/<phrase_id>/edit", methods=["POST"])
    def phrasebook_edit(phrase_id: str):
        text = request.form.get("input", "").strip()
        if not text:
            flash("La frase no puede estar vacía.", "warning")
        elif fetcher.update_phrase(phrase_id, text):
            flash("Frase actualizada.", "success")
        else:
            flash("No se encontró la frase.", "warning")
        return redirect(url_for("phrasebook"))

    @app.route("/phrasebook/<phrase_id>/delete", methods=["POST"])
    def phrasebook_delete(phrase_id: str):
        if fetcher.delete_phrase(phrase_id):
            flash("Frase eliminada.", "success")
        return redirect(url_for("phrasebook"))

    @app.route("/phrasebook/export")
    def phrasebook_export():
        csv_content = fetcher.export_phrasebook_csv()
        buffer = BytesIO(csv_content.encode("utf-8"))
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name="estudio_abroad_phrasebook.csv",
        )

    @app.route("/travel", methods=["GET", "POST"])
    def travel():
        filters = {
            "time": request.values.get("time", "").strip() or None,
            "location": request.values.get("location", "").strip() or None,
            "distance": request.values.get("distance", "").strip() or None,
            "mood": request.values.get("mood", "").strip() or None,
        }
        searched = request.method == "POST" or any(filters.values())
        recommendations = (
            fetcher.filter_travel_recommendations(**filters) if searched else []
        )
        return render_template(
            "travel.html",
            page="travel",
            title="Viajes",
            recommendations=recommendations,
            filters=filters,
            searched=searched,
            map_center=fetcher.get_travel_map_center(),
        )

    @app.route("/news")
    def news():
        news_data = fetcher.get_spain_news()
        return render_template(
            "news.html",
            page="news",
            title="Noticias",
            news=news_data,
        )

    @app.route("/history")
    def history():
        topics = fetcher.get_history_topics()
        return render_template(
            "history.html",
            page="history",
            title="Historia",
            topics=topics,
        )

    @app.route("/resources")
    def resources():
        resources_list = fetcher.get_study_resources()
        return render_template(
            "resources.html",
            page="resources",
            title="Recursos",
            resources=resources_list,
        )


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
