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
    if os.environ.get("FLASK_DEBUG", "0") == "1":
        app.config["TEMPLATES_AUTO_RELOAD"] = True

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
        try:
            reader_data = fetcher.get_reader()
        except Exception as exc:
            logger.exception("reader route failed: %s", exc)
            reader_data = {
                "passages": [],
                "weak_words_top": [],
                "section_failed": True,
            }
        return render_template(
            "reader.html",
            page="reader",
            title="Lector",
            reader=reader_data,
            section_failed=reader_data.get("section_failed", False),
        )

    @app.route("/vocab")
    def vocab():
        idx = request.args.get("i", 0, type=int)
        try:
            session = fetcher.get_vocab_session(idx)
        except Exception as exc:
            logger.exception("vocab route failed: %s", exc)
            session = {
                "card": {"es": "", "en": ""},
                "index": 0,
                "total": 0,
                "next_index": 0,
                "section_failed": True,
            }
        return render_template(
            "vocab.html",
            page="vocab",
            title="Tarjetas",
            session=session,
            section_failed=session.get("section_failed", False),
        )

    @app.route("/vocab/record", methods=["POST"])
    def vocab_record():
        es = request.form.get("es", "")
        en = request.form.get("en", "")
        missed = request.form.get("missed") == "1"
        next_i = request.form.get("next_i", 0, type=int)
        try:
            if not fetcher.record_flashcard_result(es, en, missed):
                flash(
                    "No se pudo guardar el resultado. Inténtalo de nuevo.",
                    "warning",
                )
        except Exception as exc:
            logger.exception("vocab_record failed: %s", exc)
            flash(
                "No se pudo guardar el resultado. Inténtalo de nuevo.",
                "warning",
            )
        return redirect(url_for("vocab", i=next_i))

    @app.route("/phrasebook", methods=["GET", "POST"])
    def phrasebook():
        if request.method == "POST":
            text = request.form.get("input", "").strip()
            if not text:
                flash("Escribe una frase en inglés.", "warning")
            else:
                try:
                    if fetcher.add_phrase(text):
                        flash("Frase guardada.", "success")
                    else:
                        flash(
                            "No se pudo guardar la frase. Inténtalo de nuevo.",
                            "warning",
                        )
                except Exception as exc:
                    logger.exception("phrasebook add failed: %s", exc)
                    flash(
                        "No se pudo guardar la frase. Inténtalo de nuevo.",
                        "warning",
                    )
            return redirect(url_for("phrasebook"))

        try:
            phrases = fetcher.get_phrasebook()
        except Exception as exc:
            logger.exception("phrasebook route failed: %s", exc)
            phrases = []
        return render_template(
            "phrasebook.html",
            page="phrasebook",
            title="Libro de frases",
            phrases=phrases,
            section_failed=False,
        )

    @app.route("/phrasebook/<phrase_id>/edit", methods=["POST"])
    def phrasebook_edit(phrase_id: str):
        text = request.form.get("input", "").strip()
        if not text:
            flash("La frase no puede estar vacía.", "warning")
        else:
            try:
                if fetcher.update_phrase(phrase_id, text):
                    flash("Frase actualizada.", "success")
                else:
                    flash("No se encontró la frase.", "warning")
            except Exception as exc:
                logger.exception("phrasebook_edit failed: %s", exc)
                flash(
                    "No se pudo actualizar la frase. Inténtalo de nuevo.",
                    "warning",
                )
        return redirect(url_for("phrasebook"))

    @app.route("/phrasebook/<phrase_id>/delete", methods=["POST"])
    def phrasebook_delete(phrase_id: str):
        try:
            if fetcher.delete_phrase(phrase_id):
                flash("Frase eliminada.", "success")
            else:
                flash("No se encontró la frase.", "warning")
        except Exception as exc:
            logger.exception("phrasebook_delete failed: %s", exc)
            flash(
                "No se pudo eliminar la frase. Inténtalo de nuevo.",
                "warning",
            )
        return redirect(url_for("phrasebook"))

    @app.route("/phrasebook/export")
    def phrasebook_export():
        try:
            csv_content = fetcher.export_phrasebook_csv()
        except Exception as exc:
            logger.exception("phrasebook_export failed: %s", exc)
            flash(
                "No se pudo exportar el libro de frases. Inténtalo más tarde.",
                "warning",
            )
            return redirect(url_for("phrasebook"))
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
        section_failed = False
        recommendations: list = []
        map_center = {"lat": fetcher.UB_LAT, "lng": fetcher.UB_LNG}
        try:
            recommendations = (
                fetcher.filter_travel_recommendations(**filters) if searched else []
            )
            map_center = fetcher.get_travel_map_center()
        except Exception as exc:
            logger.exception("travel route failed: %s", exc)
            section_failed = True
        return render_template(
            "travel.html",
            page="travel",
            title="Viajes",
            recommendations=recommendations,
            filters=filters,
            searched=searched,
            map_center=map_center,
            section_failed=section_failed,
        )

    @app.route("/news")
    def news():
        try:
            news_data = fetcher.get_spain_news()
        except Exception as exc:
            logger.exception("news route failed: %s", exc)
            news_data = {
                "articles": [],
                "error": "No se pudieron cargar las noticias. Inténtalo más tarde.",
                "fetched_at": None,
                "cache_timestamp": None,
                "cache_timestamp_display": "",
                "section_failed": True,
            }
        return render_template(
            "news.html",
            page="news",
            title="Noticias",
            news=news_data,
            cache_timestamp_display=news_data.get("cache_timestamp_display", ""),
            section_failed=news_data.get("section_failed", False),
        )

    @app.route("/history")
    def history():
        section_failed = False
        try:
            topics = fetcher.get_history_topics()
            if not topics:
                section_failed = True
        except Exception as exc:
            logger.exception("history route failed: %s", exc)
            topics = []
            section_failed = True
        return render_template(
            "history.html",
            page="history",
            title="Historia",
            topics=topics,
            section_failed=section_failed,
        )

    @app.route("/resources")
    def resources():
        try:
            resources_list = fetcher.get_study_resources()
        except Exception as exc:
            logger.exception("resources route failed: %s", exc)
            resources_list = []
        return render_template(
            "resources.html",
            page="resources",
            title="Recursos",
            resources=resources_list,
            section_failed=not resources_list,
        )


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
