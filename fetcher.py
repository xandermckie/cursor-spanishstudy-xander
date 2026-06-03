"""
API fetchers for Estudio Abroad — read/write data/cache.json.
Translations via MyMemory (cached). DictionaryAPI.dev for English glosses.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from fetcher_seeds import (
    DAILY_PHRASES_ES,
    DAILY_SENTENCES_ES,
    FLASHCARD_DECK_SEED,
    READER_PASSAGES_SEED,
)
from fetcher_travel import (
    TRAVEL_RECOMMENDATIONS_SEED,
    UB_LAT,
    UB_LNG,
    filter_travel_recommendations,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_FILE = DATA_DIR / "cache.json"

MYMEMORY_URL = os.environ.get(
    "MYMEMORY_URL", "https://api.mymemory.translated.net/get"
)
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "")
DICTIONARY_API_BASE = os.environ.get(
    "DICTIONARY_API_BASE", "https://api.dictionaryapi.dev/api/v2/entries/en"
).rstrip("/")

SPANISH_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "al", "a", "en", "y",
    "o", "que", "es", "está", "están", "más", "por", "con", "se", "su", "sus",
    "¿", "donde", "dónde", "cómo", "como", "qué", "me", "te", "le", "lo",
}

def _utc_day_index(pool_len: int) -> int:
    if pool_len <= 0:
        return 0
    return datetime.now(timezone.utc).timetuple().tm_yday % pool_len


def _reader_passage_index(pool_len: int) -> int:
    if pool_len <= 0:
        return 0
    return (int(datetime.now(timezone.utc).timestamp()) // 900) % pool_len


def _load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with CACHE_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, Any]) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        logger.error("Failed to write cache file: %s", exc)
        return False


def _translation_cache_key(text: str, source: str, target: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{target}:{digest}"


def fetch_translation(
    text: str, source: str, target: str, use_cache: bool = True
) -> tuple[str | None, bool]:
    """
    MyMemory translate with JSON cache. Returns (text, from_cache).
    """
    if not text or not text.strip():
        return None, False

    cache = _load_cache()
    cache.setdefault("translations", {})
    key = _translation_cache_key(text, source, target)

    if use_cache and key in cache["translations"]:
        return cache["translations"][key], True

    try:
        params: dict[str, str] = {
            "q": text[:500],
            "langpair": f"{source}|{target}",
        }
        if MYMEMORY_EMAIL:
            params["de"] = MYMEMORY_EMAIL

        response = requests.get(MYMEMORY_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("responseStatus") != 200:
            logger.warning(
                "MyMemory error: %s", data.get("responseDetails", "unknown")
            )
            if key in cache["translations"]:
                return cache["translations"][key], True
            return None, False

        translated = data.get("responseData", {}).get("translatedText", text)
        cache["translations"][key] = translated
        _save_cache(cache)
        return translated, False
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("fetch_translation failed: %s", exc)
        if key in cache["translations"]:
            return cache["translations"][key], True
        return None, False


def fetch_definition(word: str) -> dict[str, Any] | None:
    """DictionaryAPI.dev for English headword."""
    if not word or not word.strip():
        return None

    key = word.strip().lower()
    try:
        response = requests.get(f"{DICTIONARY_API_BASE}/{key}", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _parse_definition(response.json())
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        logger.exception("fetch_definition failed for %r: %s", word, exc)
        return None


def _parse_definition(data: list) -> dict[str, Any] | None:
    if not data:
        return None
    entry = data[0]
    phonetic = entry.get("phonetic", "")
    if not phonetic and entry.get("phonetics"):
        for p in entry["phonetics"]:
            if p.get("text"):
                phonetic = p["text"]
                break

    definition = ""
    example = ""
    for meaning in entry.get("meanings", []):
        for defn in meaning.get("definitions", []):
            if not definition:
                definition = defn.get("definition", "")
            if not example:
                example = defn.get("example", "")
            if definition and example:
                break

    if not definition:
        return None

    return {
        "word": entry.get("word", ""),
        "definition": definition,
        "phonetic": phonetic,
        "example": example,
    }


def _pick_spanish_headword(sentence: str) -> str:
    for token in re.findall(r"[\wáéíóúñü¿?]+", sentence.lower()):
        clean = token.strip("¿?")
        if len(clean) > 3 and clean not in SPANISH_STOPWORDS:
            return clean
    tokens = re.findall(r"[\wáéíóúñü]+", sentence.lower())
    for token in tokens:
        if len(token) > 2:
            return token
    return "palabra"


def format_refresh_time(iso_timestamp: str | None) -> str:
    """Format ISO UTC timestamp as e.g. 2026-06-03 10:25 AM CST."""
    if not iso_timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo("America/Chicago"))
        return local.strftime("%Y-%m-%d %I:%M %p CST")
    except (ValueError, TypeError):
        return iso_timestamp


def _activity_today() -> str:
    """Calendar day for streak tracking (Europe/Madrid)."""
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")


def _default_user_stats() -> dict[str, Any]:
    return {
        "xp_total": 0,
        "xp_today": 0,
        "xp_daily_goal": 200,
        "level": 1,
        "streak_days": 0,
        "last_activity_date": None,
        "words_learned": 0,
        "accuracy_pct": 0,
        "total_correct": 0,
        "total_answered": 0,
    }


def _level_from_xp(xp_total: int) -> int:
    if xp_total >= 1000:
        return 5
    if xp_total >= 500:
        return 4
    if xp_total >= 250:
        return 3
    if xp_total >= 100:
        return 2
    return 1


def _xp_threshold_for_level(level: int) -> int:
    return {1: 0, 2: 100, 3: 250, 4: 500, 5: 1000}.get(level, 0)


def _xp_next_level_threshold(level: int) -> int | None:
    return {1: 100, 2: 250, 3: 500, 4: 1000}.get(level)


def _ensure_user_stats(cache: dict[str, Any]) -> dict[str, Any]:
    stats = cache.get("user_stats")
    if not stats:
        stats = _default_user_stats()
        cache["user_stats"] = stats
    for key, val in _default_user_stats().items():
        stats.setdefault(key, val)
    return stats


def update_streak(cache: dict[str, Any] | None = None) -> None:
    """Increment streak on first activity of the day (Europe/Madrid)."""
    own_cache = cache is None
    if own_cache:
        cache = _load_cache()
    stats = _ensure_user_stats(cache)
    today = _activity_today()
    last = stats.get("last_activity_date")
    if last == today:
        if own_cache:
            _save_cache(cache)
        return
    if not last:
        stats["streak_days"] = 1
    else:
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d").date()
            today_dt = datetime.strptime(today, "%Y-%m-%d").date()
            delta = (today_dt - last_dt).days
            if delta == 1:
                stats["streak_days"] = stats.get("streak_days", 0) + 1
            else:
                stats["streak_days"] = 1
        except ValueError:
            stats["streak_days"] = 1
    stats["last_activity_date"] = today
    if own_cache:
        _save_cache(cache)


def update_xp(amount: int, cache: dict[str, Any] | None = None) -> None:
    if amount <= 0:
        return
    own_cache = cache is None
    if own_cache:
        cache = _load_cache()
    stats = _ensure_user_stats(cache)
    update_streak(cache)
    stats["xp_total"] = stats.get("xp_total", 0) + amount
    stats["xp_today"] = stats.get("xp_today", 0) + amount
    stats["level"] = _level_from_xp(stats["xp_total"])
    if own_cache:
        _save_cache(cache)


def get_user_stats() -> dict[str, Any]:
    try:
        cache = _load_cache()
        stats = _ensure_user_stats(cache)
        deck = cache.get("flashcard_deck") or FLASHCARD_DECK_SEED
        weak = cache.get("weak_words") or {}
        stats["words_learned"] = max(0, len(deck) - len(weak))
        answered = stats.get("total_answered", 0)
        correct = stats.get("total_correct", 0)
        stats["accuracy_pct"] = (
            round(100 * correct / answered) if answered > 0 else 0
        )
        level = _level_from_xp(stats.get("xp_total", 0))
        stats["level"] = level
        floor_xp = _xp_threshold_for_level(level)
        next_xp = _xp_next_level_threshold(level)
        stats["xp_in_level"] = stats.get("xp_total", 0) - floor_xp
        if next_xp is not None:
            stats["xp_level_max"] = next_xp - floor_xp
            stats["xp_to_next_level"] = next_xp - stats.get("xp_total", 0)
        else:
            stats["xp_level_max"] = 500
            stats["xp_to_next_level"] = 0
        _save_cache(cache)
        return stats
    except Exception as exc:
        logger.exception("get_user_stats failed: %s", exc)
        return _default_user_stats()


def get_last_refresh_display() -> str:
    cache = _load_cache()
    return format_refresh_time(cache.get("last_refresh"))


def reset_vocab_session() -> None:
    cache = _load_cache()
    cache["vocab_session"] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "correct_count": 0,
        "missed_count": 0,
        "complete": False,
    }
    _save_cache(cache)


def _ensure_vocab_session(cache: dict[str, Any]) -> dict[str, Any]:
    session = cache.get("vocab_session")
    if not session:
        session = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "correct_count": 0,
            "missed_count": 0,
            "complete": False,
        }
        cache["vocab_session"] = session
    return session


def award_reader_xp() -> None:
    """+5 XP once per calendar day for opening the reader."""
    cache = _load_cache()
    today = _activity_today()
    awarded = cache.get("reader_xp_dates") or []
    if today in awarded:
        return
    awarded.append(today)
    cache["reader_xp_dates"] = awarded[-30:]
    update_xp(5, cache)
    _save_cache(cache)


def refresh_homepage() -> dict[str, Any]:
    """Fetch daily sentence, phrase, and word-of-day; write cache."""
    logger.info("Refreshing homepage data from APIs…")

    now_iso = datetime.now(timezone.utc).isoformat()
    day_idx = _utc_day_index(len(DAILY_SENTENCES_ES))
    phrase_idx = (day_idx + 11) % len(DAILY_PHRASES_ES) if DAILY_PHRASES_ES else 0

    sentence_es = DAILY_SENTENCES_ES[day_idx]
    phrase_es = DAILY_PHRASES_ES[phrase_idx]

    en_text, _ = fetch_translation(sentence_es, "es", "en")
    if not en_text:
        en_text = sentence_es

    phrase_en, _ = fetch_translation(phrase_es, "es", "en")
    if not phrase_en:
        phrase_en = phrase_es

    daily = {
        "es": sentence_es,
        "en": en_text,
        "fetched_at": now_iso,
    }
    daily_phrase = {
        "es": phrase_es,
        "en": phrase_en,
        "fetched_at": now_iso,
    }

    es_word = _pick_spanish_headword(sentence_es)
    en_gloss, _ = fetch_translation(es_word, "es", "en")
    if not en_gloss:
        en_gloss = es_word

    en_lookup = en_gloss.split()[0].strip(".,?!").lower()
    dict_data = fetch_definition(en_lookup) if en_lookup else None

    word_of_day = {
        "es": es_word,
        "en": en_gloss,
        "definition": dict_data.get("definition", "") if dict_data else "",
        "phonetic": dict_data.get("phonetic", "") if dict_data else "",
        "example_es": sentence_es,
        "example_en": en_text,
    }

    cache = _load_cache()
    cache["daily_sentence"] = daily
    cache["daily_phrase"] = daily_phrase
    cache["word_of_day"] = word_of_day
    cache.setdefault("weak_words", {})
    cache.setdefault("phrasebook", [])
    cache["last_refresh"] = now_iso
    if not _save_cache(cache):
        logger.error("refresh_homepage: failed to write cache")
        return _homepage_fallback()

    return get_homepage(_refreshing=True)


def _homepage_fallback() -> dict[str, Any]:
    return {
        "daily_sentence": None,
        "daily_phrase": None,
        "word_of_day": None,
        "weak_words": [],
        "last_refresh": None,
        "last_refresh_display": "",
        "user_stats": get_user_stats(),
        "error": True,
    }


def _homepage_from_cache(cache: dict[str, Any]) -> dict[str, Any] | None:
    daily = cache.get("daily_sentence")
    daily_phrase = cache.get("daily_phrase")
    if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
        return None
    return {
        "daily_sentence": daily,
        "daily_phrase": daily_phrase,
        "word_of_day": cache.get("word_of_day"),
        "weak_words": get_weak_words(),
        "last_refresh": cache.get("last_refresh"),
        "last_refresh_display": format_refresh_time(cache.get("last_refresh")),
        "user_stats": get_user_stats(),
        "error": True,
    }


def get_homepage(*, _refreshing: bool = False) -> dict[str, Any]:
    try:
        cache = _load_cache()
        daily = cache.get("daily_sentence")
        daily_phrase = cache.get("daily_phrase")

        if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
            if _refreshing:
                logger.error("get_homepage: cache still empty after refresh attempt")
                return _homepage_fallback()
            try:
                return refresh_homepage()
            except Exception as exc:
                logger.exception("refresh_homepage failed: %s", exc)
                return _homepage_from_cache(cache) or _homepage_fallback()

        wod = cache.get("word_of_day")
        if wod and not wod.get("es"):
            try:
                refresh_homepage()
                cache = _load_cache()
                daily = cache.get("daily_sentence")
                daily_phrase = cache.get("daily_phrase")
                wod = cache.get("word_of_day")
            except Exception as exc:
                logger.exception("refresh_homepage (word_of_day) failed: %s", exc)

        return {
            "daily_sentence": daily,
            "daily_phrase": daily_phrase,
            "word_of_day": wod,
            "weak_words": get_weak_words(),
            "last_refresh": cache.get("last_refresh"),
            "last_refresh_display": format_refresh_time(cache.get("last_refresh")),
            "user_stats": get_user_stats(),
            "error": False,
        }
    except Exception as exc:
        logger.exception("get_homepage failed: %s", exc)
        return _homepage_fallback()


def get_weak_words() -> list[dict[str, Any]]:
    cache = _load_cache()
    weak = cache.get("weak_words") or {}
    items = list(weak.values())
    items.sort(key=lambda x: x.get("miss_count", 0), reverse=True)
    return items


def _ensure_flashcard_deck(cache: dict[str, Any]) -> list[dict[str, str]]:
    deck = cache.get("flashcard_deck")
    if not deck or len(deck) < len(FLASHCARD_DECK_SEED):
        deck = [dict(c) for c in FLASHCARD_DECK_SEED]
        cache["flashcard_deck"] = deck
        _save_cache(cache)
    return deck


def get_vocab_session(index: int = 0) -> dict[str, Any]:
    try:
        cache = _load_cache()
        deck = _ensure_flashcard_deck(cache)
        total = len(deck)
        session = cache.get("vocab_session") or {}
        if session.get("complete"):
            results = session.get("results", [])
            correct = session.get("correct_count", 0)
            missed = session.get("missed_count", 0)
            return {
                "complete": True,
                "correct_count": correct,
                "missed_count": missed,
                "xp_earned": correct * 10,
                "missed_words": [r for r in results if r.get("missed")],
                "total": total,
                "section_failed": False,
            }
        if not cache.get("vocab_session"):
            _ensure_vocab_session(cache)
            _save_cache(cache)
            session = cache["vocab_session"]
        idx = index % total if total else 0
        card = deck[idx] if total else {"es": "", "en": ""}
        at_last = total > 0 and idx >= total - 1
        return {
            "card": card,
            "index": idx,
            "total": total,
            "next_index": 0 if at_last else (idx + 1) % total if total else 0,
            "correct_count": session.get("correct_count", 0),
            "missed_count": session.get("missed_count", 0),
            "complete": False,
            "section_failed": False,
        }
    except Exception as exc:
        logger.exception("get_vocab_session failed: %s", exc)
        return {
            "card": {"es": "", "en": ""},
            "index": 0,
            "total": 0,
            "next_index": 0,
            "complete": False,
            "section_failed": True,
        }


def record_flashcard_result(
    es: str, en: str, missed: bool, index: int = 0
) -> bool:
    try:
        cache = _load_cache()
        deck = _ensure_flashcard_deck(cache)
        total = len(deck)
        session = _ensure_vocab_session(cache)
        session.setdefault("results", [])
        session["results"].append({"es": es, "en": en, "missed": missed})
        stats = _ensure_user_stats(cache)
        stats["total_answered"] = stats.get("total_answered", 0) + 1
        if missed:
            session["missed_count"] = session.get("missed_count", 0) + 1
            if es:
                cache.setdefault("weak_words", {})
                key = es.strip().lower()
                entry = cache["weak_words"].get(key, {
                    "es": es,
                    "en": en,
                    "miss_count": 0,
                })
                entry["miss_count"] = entry.get("miss_count", 0) + 1
                entry["last_missed"] = datetime.now(timezone.utc).isoformat()
                entry["en"] = en or entry.get("en", "")
                cache["weak_words"][key] = entry
        else:
            session["correct_count"] = session.get("correct_count", 0) + 1
            stats["total_correct"] = stats.get("total_correct", 0) + 1
            update_xp(10, cache)
        update_streak(cache)
        if total > 0 and index >= total - 1:
            session["complete"] = True
        return _save_cache(cache)
    except Exception as exc:
        logger.exception("record_flashcard_result failed: %s", exc)
        return False


def get_phrasebook() -> list[dict[str, Any]]:
    try:
        cache = _load_cache()
        return cache.get("phrasebook") or []
    except Exception as exc:
        logger.exception("get_phrasebook failed: %s", exc)
        return []


def add_phrase(user_input: str) -> dict[str, Any] | None:
    text = user_input.strip()
    if not text:
        return None
    try:
        es_text, _ = fetch_translation(text, "en", "es")
        if not es_text:
            es_text = text

        cache = _load_cache()
        cache.setdefault("phrasebook", [])
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": str(uuid.uuid4()),
            "input": text,
            "es": es_text,
            "created_at": now,
            "updated_at": now,
        }
        cache["phrasebook"].append(entry)
        update_xp(5, cache)
        update_streak(cache)
        if not _save_cache(cache):
            return None
        return entry
    except Exception as exc:
        logger.exception("add_phrase failed: %s", exc)
        return None


def update_phrase(phrase_id: str, user_input: str) -> bool:
    text = user_input.strip()
    if not text:
        return False
    try:
        es_text, _ = fetch_translation(text, "en", "es")
        if not es_text:
            es_text = text

        cache = _load_cache()
        for entry in cache.get("phrasebook", []):
            if entry.get("id") == phrase_id:
                entry["input"] = text
                entry["es"] = es_text
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                return _save_cache(cache)
        return False
    except Exception as exc:
        logger.exception("update_phrase failed: %s", exc)
        return False


def delete_phrase(phrase_id: str) -> bool:
    try:
        cache = _load_cache()
        book = cache.get("phrasebook", [])
        new_book = [e for e in book if e.get("id") != phrase_id]
        if len(new_book) == len(book):
            return False
        cache["phrasebook"] = new_book
        return _save_cache(cache)
    except Exception as exc:
        logger.exception("delete_phrase failed: %s", exc)
        return False


def export_phrasebook_csv() -> str:
    header = ["input_en", "spanish", "created_at", "updated_at"]
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for entry in get_phrasebook():
            if not isinstance(entry, dict):
                continue
            writer.writerow([
                entry.get("input", ""),
                entry.get("es", ""),
                entry.get("created_at", ""),
                entry.get("updated_at", ""),
            ])
        return output.getvalue()
    except Exception as exc:
        logger.exception("export_phrasebook_csv failed: %s", exc)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        return output.getvalue()


def _ensure_reader_passages(cache: dict[str, Any]) -> list[dict[str, Any]]:
    passages = cache.get("reader_passages")
    if not passages or len(passages) < len(READER_PASSAGES_SEED):
        passages = [dict(p) for p in READER_PASSAGES_SEED]
        cache["reader_passages"] = passages
        _save_cache(cache)
        return passages

    updated = False
    for passage in passages:
        if passage.get("en"):
            continue
        src = "es" if passage.get("lang") == "es" else "ca"
        translated, _ = fetch_translation(passage.get("body", ""), src, "en")
        if translated:
            passage["en"] = translated
            updated = True
    if updated:
        cache["reader_passages"] = passages
        _save_cache(cache)
    return passages


def get_reader() -> dict[str, Any]:
    try:
        cache = _load_cache()
        passages = _ensure_reader_passages(cache)
        idx = _reader_passage_index(len(passages))
        weak_top = get_weak_words()[:5]
        award_reader_xp()
        return {
            "passages": [passages[idx]] if passages else [],
            "weak_words_top": weak_top,
            "section_failed": False,
        }
    except Exception as exc:
        logger.exception("get_reader failed: %s", exc)
        return {
            "passages": [],
            "weak_words_top": [],
            "section_failed": True,
        }


def run_refresh() -> None:
    refresh_homepage()
    cache = _load_cache()
    _ensure_reader_passages(cache)
    _ensure_flashcard_deck(cache)
    cache.setdefault("translations", {})
    cache.setdefault("phrasebook", [])
    cache.setdefault("weak_words", {})
    _save_cache(cache)
    if NEWS_API_KEY:
        get_spain_news()


# --- Travel, news, history, resources pages ---

NEWS_API_URL = os.environ.get(
    "NEWS_API_URL", "https://newsapi.org/v2/everything"
)
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
SPAIN_NEWS_RE = re.compile(
    r"\b(españa|espana|español|espanol|española|espanola|barcelona|madrid|"
    r"cataluña|catalunya|valencia|sevilla|andaluc|galicia|bilbao|zaragoza|"
    r"ibex|sánchez|sanchez|gobierno\s+español|reino\s+de\s+españa)\b",
    re.IGNORECASE,
)
HISTORY_TOPICS = [
    {
        "key": "civil_war",
        "title_es": "La Guerra Civil Española",
        "intro_es": "Conflicto de 1936–1939 que transformó la España del siglo XX.",
        "wiki_url": "https://en.wikipedia.org/wiki/Spanish_Civil_War",
        "summary_es": (
            "La Guerra Civil Española (1936–1939) enfrentó al bando republicano, apoyado por anarquistas, socialistas y catalanes que defendían la Segunda República, contra los sublevados nacionalistas liderados por Francisco Franco, con apoyo de la Alemania nazi y la Italia fascista. "
            "El conflicto empezó con un golpe militar contra el gobierno elegido y se extendió por casi tres años de combates brutales, bombardeos sobre ciudades como Barcelona y Madrid, y una profunda división social. "
            "En Cataluña, el republicanismo y el autogobierno catalán formaron parte del frente leal a la República; Barcelona vivió episodios decisivos y, al final, la ocupación franquista suprimió la Generalitat y el catalán en la escuela y la administración durante décadas. "
            "La guerra dejó cientos de miles de muertos, exilio masivo y un régimen autoritario que duró hasta la muerte de Franco en 1975. "
            "Para entender la España actual — debates sobre memoria histórica, estatutos autonómicos y símbolos en la calle — conviene conocer cómo esta guerra marcó familias, instituciones y el lenguaje político que aún se usa hoy."
        ),
        "summary_en": (
            "The Spanish Civil War (1936–1939) pitted the Republican side—backed by anarchists, socialists, and Catalans defending the Second Republic—against Nationalist rebels led by Francisco Franco, with support from Nazi Germany and Fascist Italy. "
            "The conflict began with a military coup against the elected government and lasted nearly three years of brutal fighting, air raids on cities such as Barcelona and Madrid, and deep social division. "
            "In Catalonia, republicanism and Catalan self-government were part of the loyal front; Barcelona saw decisive episodes and, in the end, Francoist occupation suppressed the Generalitat and Catalan in schools and public life for decades. "
            "The war left hundreds of thousands dead, mass exile, and an authoritarian regime that lasted until Franco's death in 1975. "
            "To understand Spain today—debates on historical memory, autonomy statutes, and symbols in the street—it helps to see how this war shaped families, institutions, and the political language still used now."
        ),
    },
    {
        "key": "picasso",
        "title_es": "Pablo Picasso",
        "intro_es": "Pintor malagueño; figura central del arte moderno y del Museo Picasso en Barcelona.",
        "wiki_url": "https://en.wikipedia.org/wiki/Pablo_Picasso",
        "summary_es": (
            "Pablo Ruiz Picasso nació en Málaga en 1881 y se formó como artista entre España y Francia, pero mantuvo lazos fuertes con Barcelona, donde abrió estudios y expuso en sus primeros años de fama. "
            "En la ciudad catalana convivió con el modernismo y con otros creadores; el Museu Picasso de Barcelona conserva una de las mejores colecciones de su obra juvenil y de las etapas azul y rosa. "
            "Picasso revolucionó el arte del siglo XX: del realismo académico pasó al cubismo, colaboró con Georges Braque y reinterpretó formas, perspectiva y materiales en pintura, escultura y cerámica. "
            "Su mural «Guernica» (1937) se convirtió en símbolo universal contra el bombardeo de la villa vasca durante la Guerra Civil y sigue siendo referencia en protestas y museos de todo el mundo. "
            "Estudiar su trayectoria en español permite conectar vocabulario de arte, política y ciudad: ver una obra en el museo del Born o en Málaga después de leer sobre ella en clase da contexto cultural real, no solo nombres en un libro de texto."
        ),
        "summary_en": (
            "Pablo Ruiz Picasso was born in Málaga in 1881 and trained as an artist in Spain and France, but kept strong ties with Barcelona, where he opened studios and showed work in his early years of fame. "
            "In the Catalan city he moved among modernism and other creators; the Picasso Museum in Barcelona holds one of the finest collections of his youth and Blue and Rose periods. "
            "Picasso revolutionized twentieth-century art: from academic realism he moved to Cubism, worked with Georges Braque, and reshaped form, perspective, and materials in painting, sculpture, and ceramics. "
            "His mural «Guernica» (1937) became a universal symbol against the bombing of the Basque town during the Civil War and remains a reference in protests and museums worldwide. "
            "Studying his career in Spanish connects art, politics, and city vocabulary: seeing a work in the Born museum or in Málaga after reading about it in class gives real cultural context, not only names in a textbook."
        ),
    },
    {
        "key": "football",
        "title_es": "El Fútbol Español (FC Barcelona y Real Madrid)",
        "intro_es": "El clásico entre Barça y Madrid refleja rivalidad deportiva y cultural.",
        "wiki_url": "https://en.wikipedia.org/wiki/El_Cl%C3%A1sico",
        "summary_es": (
            "El fútbol en España es mucho más que deporte: es identidad regional, economía de medios y ritual social semanal. "
            "El FC Barcelona y el Real Madrid encarnan el «clásico», el partido más visto del país, donde se mezclan rivalidad deportiva, símbolos catalanes y castellanos y narrativas políticas según el momento histórico. "
            "El Barça se identifica con el lema «Més que un club» y con la defensa del catalán en el estadio; el Madrid, con éxitos europeos y una imagen internacional muy marcada. "
            "La Liga, la Copa del Rey y la Champions generan un vocabulario útil para estudiantes: gol, fuera de juego, entrenador, afición, descenso, fichaje. "
            "En Barcelona, ir a un partido en el Spotify Camp Nou o verlo en un bar del barrio es una inmersión lingüística: escucharás gritos, cánticos y análisis en español y catalán. "
            "Aunque no sigas el deporte, entender por qué un domingo de clásico vacía calles o llena terrazas ayuda a leer la cultura popular española con más matices."
        ),
        "summary_en": (
            "Football in Spain is far more than sport: it is regional identity, media business, and a weekly social ritual. "
            "FC Barcelona and Real Madrid embody «El Clásico», the country's most watched match, mixing sporting rivalry, Catalan and Castilian symbols, and political narratives depending on the historical moment. "
            "Barça is tied to the motto «More than a club» and to defending Catalan in the stadium; Madrid, to European success and a strong international image. "
            "La Liga, the Copa del Rey, and the Champions League offer useful vocabulary for learners: goal, offside, coach, fans, relegation, signing. "
            "In Barcelona, attending a match at Spotify Camp Nou or watching in a neighborhood bar is language immersion: you will hear shouts, chants, and analysis in Spanish and Catalan. "
            "Even if you do not follow the sport, understanding why a Clásico Sunday empties streets or fills terraces helps you read Spanish popular culture with more nuance."
        ),
    },
    {
        "key": "gaudi",
        "title_es": "La Sagrada Família y Antoni Gaudí",
        "intro_es": "Arquitecto modernista; su obra define el paisaje urbano de Barcelona.",
        "wiki_url": "https://en.wikipedia.org/wiki/Sagrada_Fam%C3%ADlia",
        "summary_es": (
            "Antoni Gaudí i Cornet (1852–1926) es el arquitecto más emblemático del modernismo catalán y define, para muchos visitantes, la imagen de Barcelona. "
            "Su obra mezcla inspiración natural —formas de plantas, animales y oleaje— con estructuras innovadoras, trencadís (mosaico de cerámica rota) y una fe católica que impregna proyectos como la Sagrada Família, aún en construcción más de un siglo después de su inicio. "
            "Además del templo expiatorio, diseñó o intervino en la Casa Batlló, la Pedrera, el Park Güell y la Casa Vicens; caminar por el Eixample o subir al parque permite ver cómo el urbanismo de la ciudad se volvió escenario de su imaginación. "
            "Gaudí murió tras un accidente con un tranvía cuando la Sagrada Família llevaba solo una parte levantada; desde entonces arquitectos y artesanos han continuado el proyecto según sus planos y modelos. "
            "Para un estudiante en Barcelona, visitar estas obras conociendo vocabulario de arquitectura —fachada, nave, catenaria, balcón— convierte una salida de fin de semana en práctica de español ligada al entorno inmediato de la universidad y del metro que usa cada día."
        ),
        "summary_en": (
            "Antoni Gaudí i Cornet (1852–1926) is the most emblematic architect of Catalan modernism and, for many visitors, defines the image of Barcelona. "
            "His work blends natural inspiration—shapes of plants, animals, and waves—with innovative structures, trencadís (broken-tile mosaic), and a Catholic faith that runs through projects such as the Sagrada Família, still under construction more than a century after it began. "
            "Beyond the expiatory temple, he designed or shaped Casa Batlló, La Pedrera, Park Güell, and Casa Vicens; walking the Eixample or climbing the park shows how the city's urban plan became a stage for his imagination. "
            "Gaudí died after a tram accident when the Sagrada Família had only part of its structure raised; since then architects and craftspeople have continued the project from his plans and models. "
            "For a student in Barcelona, visiting these sites with architecture vocabulary—façade, nave, catenary, balcony—turns a weekend outing into Spanish practice tied to the university setting and the metro used every day."
        ),
    },
]

STUDY_RESOURCES = [
    {
        "name": "SpanishPod101",
        "url": "https://www.spanishpod101.com",
        "skill": "listening",
        "skill_es": "escucha",
        "description_es": "Lecciones de audio y vídeo estructuradas por nivel, con vocabulario y diálogos reales.",
        "description_en": "Structured audio and video lessons by level, with vocabulary and real dialogues.",
    },
    {
        "name": "Dreaming Spanish",
        "url": "https://www.youtube.com/c/DreamingSpanish",
        "skill": "listening",
        "skill_es": "escucha",
        "description_es": "Canal de input comprensible: historias en español claro para acostumbrar el oído.",
        "description_en": "Comprehensible input channel: clear Spanish stories to train your ear.",
    },
    {
        "name": "Duolingo Spanish",
        "url": "https://www.duolingo.com",
        "skill": "vocabulary",
        "skill_es": "vocabulario",
        "description_es": "Práctica diaria gamificada; útil para repasar palabras y frases básicas.",
        "description_en": "Gamified daily practice; useful for reviewing basic words and phrases.",
    },
    {
        "name": "BBC Mundo",
        "url": "https://www.bbc.com/mundo",
        "skill": "reading",
        "skill_es": "lectura",
        "description_es": "Noticias en español con texto claro; ideal para leer sobre actualidad internacional.",
        "description_en": "Spanish news with clear writing; ideal for reading about world events.",
    },
    {
        "name": "Forvo",
        "url": "https://forvo.com",
        "skill": "speaking",
        "skill_es": "pronunciación",
        "description_es": "Pronunciación grabada por hablantes nativos; busca cualquier palabra en español.",
        "description_en": "Pronunciation recorded by native speakers; look up any Spanish word.",
    },
    {
        "name": "Conjuguemos",
        "url": "https://conjuguemos.com",
        "skill": "vocabulary",
        "skill_es": "verbos",
        "description_es": "Ejercicios de conjugación verbal; refuerza tiempos y modos del español.",
        "description_en": "Verb conjugation drills; reinforces Spanish tenses and moods.",
    },
]


def _cache_is_fresh(fetched_at: str | None, max_age_seconds: int) -> bool:
    if not fetched_at:
        return False
    try:
        dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        return age < max_age_seconds
    except (ValueError, TypeError):
        return False


def format_news_date(iso_timestamp: str | None) -> str:
    if not iso_timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except (ValueError, TypeError):
        return iso_timestamp


def get_travel_map_center() -> dict[str, float]:
    return {"lat": UB_LAT, "lng": UB_LNG}


def _news_api_request_params() -> dict[str, str | int]:
    """Build NewsAPI query params for Spain-focused Spanish articles."""
    params: dict[str, str | int] = {"pageSize": 12, "apiKey": NEWS_API_KEY}
    if "top-headlines" in NEWS_API_URL:
        params["country"] = "es"
        params["category"] = "general"
    else:
        params["q"] = (
            '(España OR Spain OR Madrid OR Barcelona OR Valencia OR Cataluña) '
            "AND NOT (Mexico OR Argentina OR Chile)"
        )
        params["language"] = "es"
        params["searchIn"] = "title,description"
        params["sortBy"] = "publishedAt"
    return params


def _is_spain_related_article(title: str, description: str) -> bool:
    """Keep articles that clearly mention Spain (filters generic world news)."""
    return bool(SPAIN_NEWS_RE.search(f"{title} {description}"))


def _parse_news_api_articles(
    raw: list[dict[str, Any]], *, spain_only: bool = True
) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for item in raw:
        title = (item.get("title") or "").strip()
        description = (item.get("description") or "").strip()
        if not title or not description:
            continue
        if spain_only and not _is_spain_related_article(title, description):
            continue
        source = item.get("source") or {}
        articles.append({
            "title": title,
            "description": description,
            "url": item.get("url", ""),
            "source": source.get("name", "Desconocido"),
            "publishedAt": item.get("publishedAt", ""),
            "published_display": format_news_date(item.get("publishedAt")),
        })
    return articles


def _news_result(
    articles: list[dict[str, Any]],
    error: str | None,
    fetched_at: str | None,
    *,
    stale_cache: bool = False,
) -> dict[str, Any]:
    cache_ts = fetched_at if stale_cache and fetched_at else None
    display = format_refresh_time(cache_ts) if cache_ts else ""
    section_failed = not articles and bool(error or not fetched_at)
    return {
        "articles": articles,
        "error": error,
        "fetched_at": fetched_at,
        "cache_timestamp": cache_ts,
        "cache_timestamp_display": display,
        "section_failed": section_failed,
    }


def get_spain_news() -> dict[str, Any]:
    try:
        cache = _load_cache()
        cached = cache.get("spain_news")
        if cached and _cache_is_fresh(cached.get("fetched_at"), 3600):
            return _news_result(
                cached.get("articles", []),
                None,
                cached.get("fetched_at"),
            )

        stale_articles = cached.get("articles", []) if cached else []
        stale_at = cached.get("fetched_at") if cached else None

        if not NEWS_API_KEY:
            return _news_result(
                stale_articles,
                "Falta la clave NEWS_API_KEY en el archivo .env.",
                stale_at,
                stale_cache=bool(stale_articles and stale_at),
            )

        try:
            response = requests.get(
                NEWS_API_URL,
                params=_news_api_request_params(),
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "error":
                raise ValueError(data.get("message", "NewsAPI error"))
            raw = data.get("articles") or []
            articles = _parse_news_api_articles(raw)
            if not articles and raw:
                articles = _parse_news_api_articles(raw, spain_only=False)
            now = datetime.now(timezone.utc).isoformat()
            cache["spain_news"] = {"articles": articles, "fetched_at": now}
            _save_cache(cache)
            if not articles:
                return _news_result(
                    [],
                    "No hay artículos disponibles en este momento.",
                    now,
                )
            return _news_result(articles, None, now)
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.exception("get_spain_news failed: %s", exc)
            return _news_result(
                stale_articles,
                "No se pudieron cargar las noticias. Inténtalo más tarde.",
                stale_at,
                stale_cache=bool(stale_articles and stale_at),
            )
    except Exception as exc:
        logger.exception("get_spain_news unexpected failure: %s", exc)
        return _news_result(
            [],
            "No se pudieron cargar las noticias. Inténtalo más tarde.",
            None,
        )


def get_history_topics() -> list[dict[str, Any]]:
    try:
        return [
            {
                "key": t["key"],
                "title_es": t["title_es"],
                "intro_es": t["intro_es"],
                "summary_es": t["summary_es"],
                "summary_en": t["summary_en"],
                "wiki_url": t["wiki_url"],
            }
            for t in HISTORY_TOPICS
        ]
    except Exception as exc:
        logger.exception("get_history_topics failed: %s", exc)
        return []


def get_study_resources() -> list[dict[str, Any]]:
    return [dict(r) for r in STUDY_RESOURCES]
