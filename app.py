"""Estudio Abroad — Flask app for Barcelona Spanish study."""

from __future__ import annotations

import logging
import os
import secrets
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.wrappers.response import Response

import encryption
import fetcher
import greetings
import user_store
from scheduler import init_scheduler

load_dotenv()

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_FILE = DATA_DIR / "cache.json"
DEFAULT_SECRET_KEY = "dev-change-me"
PHRASE_MAX_LENGTH = 500
MIN_PASSWORD_LEN = 8
SUPPORTED_LANGS = frozenset({"en", "es", "ca"})
LANG_LABELS = {"en": "Inglés", "es": "Español", "ca": "Catalán"}

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)


def _is_mobile_user_agent(user_agent: str | None) -> bool:
    """Heuristic for phones/tablets — used to fast-path Web Speech on /voice."""
    ua = (user_agent or "").lower()
    mobile_tokens = (
        "iphone",
        "ipad",
        "ipod",
        "android",
        "mobile",
        "webos",
        "opera mini",
        "iemobile",
    )
    return any(token in ua for token in mobile_tokens)


def _parse_refresh_interval_minutes() -> int:
    raw = os.environ.get("REFRESH_INTERVAL_MINUTES", "15")
    try:
        interval = int(raw)
        if interval < 1:
            raise ValueError("interval must be positive")
        return interval
    except ValueError:
        logger.warning(
            "Invalid REFRESH_INTERVAL_MINUTES=%r; using 15.", raw
        )
        return 15


def generate_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def validate_csrf(token: str | None) -> bool:
    expected = session.get("csrf_token")
    return bool(token and expected and secrets.compare_digest(token, expected))


def get_current_user_id() -> str | None:
    return session.get("user_id")


def get_current_user_email() -> str | None:
    return session.get("email")


def _translation_requires_auth() -> bool:
    """Optional prod flag: require login before translation API calls."""
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    return not debug and os.environ.get("TRANSLATION_REQUIRES_AUTH", "0") == "1"


def _safe_next_url(target: str | None) -> str:
    if not target:
        return url_for("home")
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme:
        return url_for("home")
    if not target.startswith("/"):
        return url_for("home")
    return target


def _establish_session(user_id: str, email: str) -> None:
    """Regenerate session ID after authentication to prevent session fixation."""
    session.clear()
    session["user_id"] = user_id
    session["email"] = email
    generate_csrf_token()


def _current_user_context() -> dict[str, Any]:
    user_id = get_current_user_id()
    email = get_current_user_email()
    avatar_url = None
    if user_id:
        nav = fetcher.get_user_nav_info(user_id)
        email = nav.get("email") or email
        if nav.get("avatar_ext"):
            avatar_url = url_for("profile_avatar")
    return {
        "is_authenticated": bool(user_id),
        "email": email,
        "avatar_url": avatar_url,
    }


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Response:
        if not get_current_user_id():
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def ensure_cache_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        CACHE_FILE.write_text("{}", encoding="utf-8")
    cache = fetcher._load_cache_from_disk()
    daily = cache.get("daily_sentence")
    daily_phrase = cache.get("daily_phrase")
    if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
        fetcher._bootstrap_homepage_cache()


def create_app() -> Flask:
    app = Flask(__name__)
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    secret_key = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    if not debug and secret_key in ("", DEFAULT_SECRET_KEY):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random value in production. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    app.config["SECRET_KEY"] = secret_key
    app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not debug,
    )
    if debug:
        app.config["TEMPLATES_AUTO_RELOAD"] = True

    limiter.init_app(app)

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://maps.googleapis.com "
            "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://cdn.jsdelivr.net https://huggingface.co "
            "https://*.huggingface.co; "
            "frame-ancestors 'self';"
        )
        return response

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        encryption.get_encryption_key()
        logger.info("Encryption key validated successfully")
    except ValueError as exc:
        logger.warning(
            "Encryption key unavailable (%s). User cache encryption disabled.",
            exc,
        )

    ensure_cache_file()

    interval = _parse_refresh_interval_minutes()
    scheduler_on = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    init_scheduler(app, interval_minutes=interval, enabled=scheduler_on)

    @app.context_processor
    def inject_globals():
        user_id = get_current_user_id()
        return {
            "last_refresh_display": fetcher.get_last_refresh_display(),
            "user_stats": fetcher.get_user_stats(user_id),
            "csrf_token": generate_csrf_token,
            "current_user": _current_user_context(),
        }

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("10 per minute", methods=["POST"])
    def register():
        if get_current_user_id():
            return redirect(url_for("profile"))
        if request.method == "POST":
            if not validate_csrf(request.form.get("csrf_token")):
                flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
                return redirect(url_for("register"))
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not user_store.normalize_email(email):
                flash("Introduce un correo electrónico válido.", "warning")
            elif len(password) < MIN_PASSWORD_LEN:
                flash(
                    f"La contraseña debe tener al menos {MIN_PASSWORD_LEN} caracteres.",
                    "warning",
                )
            elif password != confirm:
                flash("Las contraseñas no coinciden.", "warning")
            else:
                user_id = user_store.register_user(email, password)
                if user_id:
                    _establish_session(
                        user_id, user_store.normalize_email(email) or ""
                    )
                    flash("Cuenta creada. ¡Bienvenido!", "success")
                    return redirect(url_for("profile"))
                flash("Ese correo ya está registrado.", "warning")
        return render_template(
            "register.html",
            page="register",
            title="Registrarse",
        )

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute", methods=["POST"])
    def login():
        if get_current_user_id():
            return redirect(url_for("home"))
        if request.method == "POST":
            if not validate_csrf(request.form.get("csrf_token")):
                flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
                return redirect(url_for("login"))
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            user_id = user_store.authenticate(email, password)
            if user_id:
                _establish_session(
                    user_id, user_store.normalize_email(email) or ""
                )
                flash("Sesión iniciada.", "success")
                return redirect(_safe_next_url(request.args.get("next")))
            flash("Correo o contraseña incorrectos.", "warning")
        return render_template(
            "login.html",
            page="login",
            title="Iniciar sesión",
            next_url=request.args.get("next", ""),
        )

    @app.route("/logout", methods=["POST"])
    def logout():
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
            return redirect(url_for("home"))
        session.pop("user_id", None)
        session.pop("email", None)
        flash("Sesión cerrada.", "success")
        return redirect(url_for("home"))

    @app.route("/profile")
    @login_required
    def profile():
        user_id = get_current_user_id()
        stats = fetcher.get_user_stats(user_id)
        phrase_count = len(fetcher.get_phrasebook(user_id))
        return render_template(
            "profile.html",
            page="profile",
            title="Perfil",
            stats=stats,
            phrase_count=phrase_count,
            has_avatar=user_store.has_avatar(user_id),
        )

    @app.route("/profile/avatar", methods=["GET", "POST"])
    @login_required
    def profile_avatar():
        user_id = get_current_user_id()
        if request.method == "POST":
            if not validate_csrf(request.form.get("csrf_token")):
                flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
                return redirect(url_for("profile"))
            file = request.files.get("avatar")
            if not file or not file.filename:
                flash("Selecciona una imagen.", "warning")
                return redirect(url_for("profile"))
            data = file.read()
            ext = user_store.save_avatar(user_id, data, file.content_type)
            if ext:
                flash("Foto de perfil actualizada.", "success")
            else:
                flash(
                    "No se pudo guardar la imagen. Usa JPG, PNG o WebP (máx. 2 MB).",
                    "warning",
                )
            return redirect(url_for("profile"))

        path = user_store.avatar_path(user_id)
        if not path:
            return redirect(url_for("profile"))
        ext = path.suffix.lower()
        mimetype = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")
        return send_file(path, mimetype=mimetype)

    @app.route("/")
    def home():
        user_id = get_current_user_id()
        homepage = fetcher.get_homepage(user_id)
        return render_template(
            "index.html",
            page="home",
            title="Inicio",
            homepage=homepage,
            gallery_items=fetcher.get_home_gallery(),
            greeting=greetings.get_time_greeting(),
        )

    @app.route("/reader")
    def reader():
        user_id = get_current_user_id()
        try:
            reader_data = fetcher.get_reader(user_id)
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
            spain_accent=fetcher.get_spain_accent(0),
        )

    @app.route("/vocab")
    def vocab():
        user_id = get_current_user_id()
        try:
            vocab_session = fetcher.get_vocab_session(user_id)
        except Exception as exc:
            logger.exception("vocab route failed: %s", exc)
            vocab_session = {
                "card": {"es": "", "en": ""},
                "index": 0,
                "total": 0,
                "next_index": 0,
                "section_failed": True,
                "read_only": True,
            }
        return render_template(
            "vocab.html",
            page="vocab",
            title="Tarjetas",
            session=vocab_session,
            section_failed=vocab_session.get("section_failed", False),
        )

    @app.route("/vocab/restart", methods=["POST"])
    @login_required
    def vocab_restart():
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
            return redirect(url_for("vocab"))
        user_id = get_current_user_id()
        fetcher.reset_vocab_session(user_id)
        return redirect(url_for("vocab"))

    @app.route("/vocab/record", methods=["POST"])
    @login_required
    def vocab_record():
        user_id = get_current_user_id()
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
            return redirect(url_for("vocab"))
        es = request.form.get("es", "")
        en = request.form.get("en", "")
        missed = request.form.get("missed") == "1"
        current_i = request.form.get("current_i", 0, type=int)
        try:
            if not fetcher.record_flashcard_result(
                user_id, es, en, missed, current_i
            ):
                flash(
                    "No se pudo guardar el resultado. Inténtalo de nuevo.",
                    "warning",
                )
            return redirect(url_for("vocab"))
        except Exception as exc:
            logger.exception("vocab_record failed: %s", exc)
            flash(
                "No se pudo guardar el resultado. Inténtalo de nuevo.",
                "warning",
            )
            return redirect(url_for("vocab"))

    @app.route("/phrasebook", methods=["GET", "POST"])
    def phrasebook():
        user_id = get_current_user_id()
        if request.method == "POST":
            if not user_id:
                flash("Inicia sesión para guardar frases.", "warning")
                return redirect(url_for("login", next=url_for("phrasebook")))
            if not validate_csrf(request.form.get("csrf_token")):
                flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
                return redirect(url_for("phrasebook"))
            text = request.form.get("input", "").strip()
            if not text:
                flash("Escribe una frase en inglés.", "warning")
            elif len(text) > PHRASE_MAX_LENGTH:
                flash(
                    f"La frase es demasiado larga (máximo {PHRASE_MAX_LENGTH} caracteres).",
                    "warning",
                )
            else:
                try:
                    if fetcher.add_phrase(user_id, text):
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
            phrases = fetcher.get_phrasebook(user_id)
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
    @login_required
    def phrasebook_edit(phrase_id: str):
        user_id = get_current_user_id()
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
            return redirect(url_for("phrasebook"))
        text = request.form.get("input", "").strip()
        if not text:
            flash("La frase no puede estar vacía.", "warning")
        elif len(text) > PHRASE_MAX_LENGTH:
            flash(
                f"La frase es demasiado larga (máximo {PHRASE_MAX_LENGTH} caracteres).",
                "warning",
            )
        else:
            try:
                if fetcher.update_phrase(user_id, phrase_id, text):
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
    @login_required
    def phrasebook_delete(phrase_id: str):
        user_id = get_current_user_id()
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
            return redirect(url_for("phrasebook"))
        try:
            if fetcher.delete_phrase(user_id, phrase_id):
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
    @login_required
    def phrasebook_export():
        user_id = get_current_user_id()
        try:
            csv_content = fetcher.export_phrasebook_csv(user_id)
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

    @app.route("/voice")
    def voice():
        prefer_webspeech = _is_mobile_user_agent(request.headers.get("User-Agent"))
        return render_template(
            "voice.html",
            page="voice",
            title="Voz",
            prefer_webspeech=prefer_webspeech,
        )

    @app.route("/voice/translate", methods=["POST"])
    @limiter.limit("30 per minute")
    def voice_translate():
        if _translation_requires_auth() and not get_current_user_id():
            return jsonify({"error": "Inicia sesión para traducir."}), 401
        if not validate_csrf(request.headers.get("X-CSRF-Token")):
            return jsonify({"error": "Solicitud no válida."}), 403
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        source_lang = (data.get("source_lang") or "").strip()
        if source_lang not in ("en", "es"):
            return jsonify({"error": "Idioma de origen no válido."}), 400
        if not text:
            return jsonify({"error": "Escribe o dicta una frase."}), 400
        if len(text) > PHRASE_MAX_LENGTH:
            return jsonify(
                {
                    "error": (
                        f"La frase es demasiado larga "
                        f"(máximo {PHRASE_MAX_LENGTH} caracteres)."
                    )
                }
            ), 400
        target_lang = "es" if source_lang == "en" else "en"
        try:
            translated, _ = fetcher.fetch_translation_fast(
                text, source_lang, target_lang
            )
        except Exception as exc:
            logger.exception("voice_translate failed: %s", exc)
            return jsonify({"error": "No se pudo traducir. Inténtalo de nuevo."}), 500
        if not translated:
            return jsonify(
                {"error": "No se pudo traducir. Inténtalo de nuevo."}
            ), 504
        return jsonify(
            {
                "spoken": text,
                "translated": translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
        )

    @app.route("/voice/save", methods=["POST"])
    def voice_save():
        if not get_current_user_id():
            return jsonify({"error": "Inicia sesión para guardar frases."}), 401
        if not validate_csrf(request.headers.get("X-CSRF-Token")):
            return jsonify({"error": "Solicitud no válida."}), 403
        data = request.get_json(silent=True) or {}
        spoken = (data.get("spoken") or "").strip()
        translated = (data.get("translated") or "").strip()
        source_lang = (data.get("source_lang") or "").strip()
        if source_lang not in ("en", "es"):
            return jsonify({"error": "Idioma de origen no válido."}), 400
        if not spoken or not translated:
            return jsonify({"error": "Faltan datos de la frase."}), 400
        if len(spoken) > PHRASE_MAX_LENGTH or len(translated) > PHRASE_MAX_LENGTH:
            return jsonify(
                {
                    "error": (
                        f"La frase es demasiado larga "
                        f"(máximo {PHRASE_MAX_LENGTH} caracteres)."
                    )
                }
            ), 400
        user_id = get_current_user_id()
        try:
            entry = fetcher.add_phrase_bidirectional(
                user_id, spoken, translated, source_lang
            )
        except Exception as exc:
            logger.exception("voice_save failed: %s", exc)
            return jsonify({"error": "No se pudo guardar la frase."}), 500
        if not entry:
            return jsonify({"error": "No se pudo guardar la frase."}), 500
        return jsonify({"ok": True, "phrase_id": entry["id"]})

    @app.route("/translate")
    def translate():
        return render_template(
            "translate.html",
            page="translate",
            title="Traductor",
        )

    @app.route("/translate/api", methods=["POST"])
    @limiter.limit("30 per minute")
    def translate_api():
        if _translation_requires_auth() and not get_current_user_id():
            return jsonify({"error": "Inicia sesión para traducir."}), 401
        if not validate_csrf(request.headers.get("X-CSRF-Token")):
            return jsonify({"error": "Solicitud no válida."}), 403
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        source_lang = (data.get("source_lang") or "").strip()
        target_lang = (data.get("target_lang") or "").strip()
        if source_lang not in SUPPORTED_LANGS:
            return jsonify({"error": "Idioma de origen no válido."}), 400
        if target_lang not in SUPPORTED_LANGS:
            return jsonify({"error": "Idioma de destino no válido."}), 400
        if source_lang == target_lang:
            return jsonify({"error": "Elige idiomas de origen y destino distintos."}), 400
        if not text:
            return jsonify({"error": "Escribe una frase para traducir."}), 400
        if len(text) > PHRASE_MAX_LENGTH:
            return jsonify(
                {
                    "error": (
                        f"La frase es demasiado larga "
                        f"(máximo {PHRASE_MAX_LENGTH} caracteres)."
                    )
                }
            ), 400
        try:
            translated, from_cache = fetcher.fetch_translation(
                text, source_lang, target_lang
            )
        except Exception as exc:
            logger.exception("translate_api failed: %s", exc)
            return jsonify({"error": "No se pudo traducir. Inténtalo de nuevo."}), 500
        if not translated:
            return jsonify({"error": "No se pudo traducir. Inténtalo de nuevo."}), 500
        return jsonify(
            {
                "source": text,
                "translated": translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "from_cache": from_cache,
            }
        )

    @app.route("/translate/save", methods=["POST"])
    def translate_save():
        if not get_current_user_id():
            return jsonify({"error": "Inicia sesión para guardar frases."}), 401
        if not validate_csrf(request.headers.get("X-CSRF-Token")):
            return jsonify({"error": "Solicitud no válida."}), 403
        data = request.get_json(silent=True) or {}
        spoken = (data.get("spoken") or "").strip()
        translated = (data.get("translated") or "").strip()
        source_lang = (data.get("source_lang") or "").strip()
        if source_lang not in ("en", "es"):
            return jsonify({"error": "Solo se pueden guardar frases en inglés o español."}), 400
        if not spoken or not translated:
            return jsonify({"error": "Faltan datos de la frase."}), 400
        if len(spoken) > PHRASE_MAX_LENGTH or len(translated) > PHRASE_MAX_LENGTH:
            return jsonify(
                {
                    "error": (
                        f"La frase es demasiado larga "
                        f"(máximo {PHRASE_MAX_LENGTH} caracteres)."
                    )
                }
            ), 400
        user_id = get_current_user_id()
        try:
            entry = fetcher.add_phrase_bidirectional(
                user_id, spoken, translated, source_lang
            )
        except Exception as exc:
            logger.exception("translate_save failed: %s", exc)
            return jsonify({"error": "No se pudo guardar la frase."}), 500
        if not entry:
            return jsonify({"error": "No se pudo guardar la frase."}), 500
        return jsonify({"ok": True, "phrase_id": entry["id"]})

    @app.route("/travel", methods=["GET", "POST"])
    def travel():
        if request.method == "POST":
            if not validate_csrf(request.form.get("csrf_token")):
                flash("Solicitud no válida. Inténtalo de nuevo.", "warning")
                return redirect(url_for("travel"))
        filters = {
            "time": request.values.get("time", "").strip() or None,
            "location": request.values.get("location", "").strip() or None,
            "distance": request.values.get("distance", "").strip() or None,
            "mood": request.values.get("mood", "").strip() or None,
        }
        searched = request.method == "POST" or any(filters.values())
        section_failed = False
        recommendations: list = []
        origin = fetcher.get_origin_coordinates(filters["location"])
        origin_label = fetcher.get_origin_label(filters["location"])
        map_center = origin
        try:
            if searched:
                seed_recommendations = fetcher.filter_travel_recommendations(**filters)
                
                google_recommendations = []
                if filters["mood"]:
                    google_recommendations = fetcher.fetch_google_places(
                        mood=filters["mood"],
                        location=filters["location"],
                        max_results=3,
                    )
                
                if google_recommendations:
                    combined = seed_recommendations + google_recommendations
                    
                    seen_ids = set()
                    unique_combined = []
                    for rec in combined:
                        if rec["id"] not in seen_ids:
                            seen_ids.add(rec["id"])
                            unique_combined.append(rec)
                    
                    scored = []
                    for rec in unique_combined:
                        score = 0
                        if filters["time"] and filters["time"] in rec.get("time", []):
                            score += 2
                        elif not filters["time"]:
                            score += 1
                        if filters["location"] and filters["location"] in rec.get("location", []):
                            score += 2
                        elif not filters["location"]:
                            score += 1
                        if filters["distance"] and filters["distance"] in rec.get("distance", []):
                            score += 2
                        elif not filters["distance"]:
                            score += 1
                        if filters["mood"] and filters["mood"] in rec.get("mood", []):
                            score += 2
                        elif not filters["mood"]:
                            score += 1
                        
                        if rec.get("_source") == "google_api":
                            score += 1
                        
                        scored.append((score, rec))
                    
                    scored.sort(key=lambda x: x[0], reverse=True)
                    recommendations = [r for _, r in scored[:5]]
                else:
                    recommendations = seed_recommendations
            else:
                recommendations = []
            
            map_center = fetcher.get_travel_map_center(filters["location"])
        except Exception as exc:
            logger.exception("travel route failed: %s", exc)
            section_failed = True
        google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
        return render_template(
            "travel.html",
            page="travel",
            title="Viajes",
            recommendations=recommendations,
            filters=filters,
            searched=searched,
            map_center=map_center,
            origin=origin,
            origin_label=origin_label,
            section_failed=section_failed,
            google_maps_api_key=google_maps_api_key,
            spain_accent=fetcher.get_spain_accent(1),
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
            spain_accent=fetcher.get_spain_accent(2),
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
            spain_accent=fetcher.get_spain_accent(3),
        )


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
