"""Estudio Personal — Flask application factory and routes."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from io import BytesIO

from apscheduler.schedulers.background import BackgroundScheduler
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

import config
from helpers import dictionary, glosbe, lingua, quiz, refresh, storage

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"transit", "food", "places", "phrases", "emergencies"}
_scheduler: BackgroundScheduler | None = None


def _spanish_headword(phrase: str) -> str:
    """Pick a plausible Spanish headword for grammar lookup."""
    for word in phrase.split():
        cleaned = word.strip("¿?,.'\"¡!").lower()
        if len(cleaned) > 2 and cleaned.isalpha():
            return cleaned
    return ""


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.FLASK_DEBUG

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    storage.ensure_runtime_files()
    from helpers import translate as translate_mod

    translate_mod.warm_cache_from_vocab()
    register_routes(app)
    init_scheduler(app)

    @app.context_processor
    def inject_globals():
        return {
            "app_name": "Estudio Personal",
            "categories": sorted(VALID_CATEGORIES),
            "api_warning": getattr(g, "api_warning", None),
        }

    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        pass

    return app


def register_routes(app: Flask) -> None:
    @app.route("/")
    def dashboard():
        daily = storage.get_daily_sentence()
        if not daily:
            from helpers import translate as translate_mod

            try:
                daily = translate_mod.refresh_daily_sentence()
            except Exception:
                daily = {
                    "es": "Bienvenido a Estudio Personal.",
                    "ca": "Benvingut a Estudio Personal.",
                    "en": "Welcome to Estudio Personal.",
                }

        word_details = None
        if daily.get("en"):
            word = daily["en"].split()[0].strip(".,?!").lower()
            word_details = dictionary.fetch_word_details(word)

        return render_template(
            "dashboard.html",
            daily=daily,
            category_counts=storage.category_counts(),
            weak_area=storage.weak_area_category(),
            word_details=word_details,
        )

    @app.route("/reader")
    def reader():
        lang = request.args.get("lang", "es")
        if lang not in ("es", "ca"):
            lang = "es"

        passages = storage.get_reader_passages()
        passage = next((p for p in passages if p.get("lang") == lang), None)
        if not passage and passages:
            passage = passages[0]
            lang = passage.get("lang", "es")

        if passage:
            body = passage.get("body", "")
            source_text = body
            translation = passage.get("en", "")
        else:
            source_text = "No passage available."
            translation = ""

        return render_template(
            "reader.html",
            passage=passage,
            lang=lang,
            source_text=source_text,
            translation=translation,
        )

    @app.route("/vocab")
    def vocab():
        category = request.args.get("category", "")
        items = storage.get_vocab()
        if category and category in VALID_CATEGORIES:
            items = [v for v in items if v.get("category") == category]

        examples = []
        grammar = None
        if items:
            first_phrase = items[0].get("es", "")
            if first_phrase:
                examples = glosbe.fetch_examples(
                    first_phrase, from_lang="es", to_lang="en"
                )
                verb_candidate = _spanish_headword(first_phrase)
                grammar = (
                    lingua.fetch_conjugation(verb_candidate, lang="es")
                    if verb_candidate
                    else None
                )

        return render_template(
            "vocab.html",
            items=items,
            active_category=category,
            examples=examples,
            example_phrase=items[0].get("es", "") if items else "",
            grammar=grammar,
        )

    @app.route("/quiz", methods=["GET", "POST"])
    def quiz_page():
        score = None
        total = None

        if request.method == "GET":
            questions = quiz.build_quiz_session()
            session["quiz_questions"] = questions
        else:
            questions = session.get("quiz_questions", [])
            if questions:
                answers = {
                    key.replace("answer_", ""): value
                    for key, value in request.form.items()
                    if key.startswith("answer_")
                }
                score, total = quiz.score_quiz(questions, answers)
                flash(f"You scored {score} out of {total}.", "success")

        return render_template(
            "quiz.html",
            questions=questions,
            score=score,
            total=total,
        )

    @app.route("/phrasebook", methods=["GET", "POST"])
    def phrasebook():
        if request.method == "POST":
            es = request.form.get("es", "").strip()
            ca = request.form.get("ca", "").strip()
            en = request.form.get("en", "").strip()
            category = request.form.get("category", "").strip()

            if not all([es, ca, en, category]):
                flash("All fields are required.", "warning")
            elif category not in VALID_CATEGORIES:
                flash("Please choose a valid category.", "warning")
            else:
                storage.add_phrase(es, ca, en, category)
                flash("Phrase added to your phrasebook.", "success")
                return redirect(url_for("phrasebook"))

        phrases = storage.get_phrasebook()
        return render_template("phrasebook.html", phrases=phrases)

    @app.route("/refresh")
    def refresh_data():
        result = refresh.run_full_refresh()
        if result["ok"]:
            flash("Data refreshed successfully.", "success")
        else:
            g.api_warning = (
                "Refresh completed with some issues: "
                + "; ".join(result["errors"][:3])
            )
            flash(
                "Refresh finished with warnings. Using cached data where needed.",
                "warning",
            )
        return redirect(url_for("dashboard"))

    @app.route("/export")
    def export_data():
        csv_content = storage.export_csv()
        buffer = BytesIO(csv_content.encode("utf-8"))
        buffer.seek(0)
        filename = f"estudio_personal_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        return send_file(
            buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )


def init_scheduler(app: Flask) -> None:
    global _scheduler

    if not config.SCHEDULER_ENABLED:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            try:
                refresh.run_full_refresh()
            except Exception as exc:
                logger.exception("Scheduled refresh failed: %s", exc)

    _scheduler.add_job(job, "interval", hours=6, id="refresh_cache")
    _scheduler.start()
    logger.info("APScheduler started: refresh every 6 hours.")

    @app.teardown_appcontext
    def _noop(exc=None):
        pass


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=config.FLASK_DEBUG)
