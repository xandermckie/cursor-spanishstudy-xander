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


def _save_cache(cache: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


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
    _save_cache(cache)

    return get_homepage()


def get_homepage() -> dict[str, Any]:
    cache = _load_cache()
    daily = cache.get("daily_sentence")
    daily_phrase = cache.get("daily_phrase")

    if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
        return refresh_homepage()

    wod = cache.get("word_of_day")
    if wod and not wod.get("es"):
        refresh_homepage()
        cache = _load_cache()
        wod = cache.get("word_of_day")
        daily_phrase = cache.get("daily_phrase")

    return {
        "daily_sentence": daily,
        "daily_phrase": daily_phrase,
        "word_of_day": wod,
        "weak_words": get_weak_words(),
        "last_refresh": cache.get("last_refresh"),
        "last_refresh_display": format_refresh_time(cache.get("last_refresh")),
    }


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
    cache = _load_cache()
    deck = _ensure_flashcard_deck(cache)
    total = len(deck)
    idx = index % total if total else 0
    card = deck[idx] if total else {"es": "", "en": ""}
    return {
        "card": card,
        "index": idx,
        "total": total,
        "next_index": (idx + 1) % total if total else 0,
    }


def record_flashcard_result(es: str, en: str, missed: bool) -> None:
    if not missed or not es:
        return
    cache = _load_cache()
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
    _save_cache(cache)


def get_phrasebook() -> list[dict[str, Any]]:
    cache = _load_cache()
    return cache.get("phrasebook") or []


def add_phrase(user_input: str) -> dict[str, Any] | None:
    text = user_input.strip()
    if not text:
        return None
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
    _save_cache(cache)
    return entry


def update_phrase(phrase_id: str, user_input: str) -> bool:
    text = user_input.strip()
    if not text:
        return False
    es_text, _ = fetch_translation(text, "en", "es")
    if not es_text:
        es_text = text

    cache = _load_cache()
    for entry in cache.get("phrasebook", []):
        if entry.get("id") == phrase_id:
            entry["input"] = text
            entry["es"] = es_text
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_cache(cache)
            return True
    return False


def delete_phrase(phrase_id: str) -> bool:
    cache = _load_cache()
    book = cache.get("phrasebook", [])
    new_book = [e for e in book if e.get("id") != phrase_id]
    if len(new_book) == len(book):
        return False
    cache["phrasebook"] = new_book
    _save_cache(cache)
    return True


def export_phrasebook_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["input_en", "spanish", "created_at", "updated_at"])
    for entry in get_phrasebook():
        writer.writerow([
            entry.get("input", ""),
            entry.get("es", ""),
            entry.get("created_at", ""),
            entry.get("updated_at", ""),
        ])
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
    cache = _load_cache()
    passages = _ensure_reader_passages(cache)
    idx = _reader_passage_index(len(passages))
    weak_top = get_weak_words()[:5]
    return {
        "passages": [passages[idx]] if passages else [],
        "weak_words_top": weak_top,
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


# --- Travel, news, history, resources pages ---

NEWS_API_URL = os.environ.get(
    "NEWS_API_URL", "https://newsapi.org/v2/everything"
)
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

HISTORY_TOPICS = [
    {
        "key": "civil_war",
        "title_es": "La Guerra Civil Española",
        "intro_es": "Conflicto de 1936–1939 que transformó la España del siglo XX.",
        "wiki_title": "Spanish_Civil_War",
    },
    {
        "key": "picasso",
        "title_es": "Pablo Picasso",
        "intro_es": "Pintor malagueño; figura central del arte moderno y del Museo Picasso en Barcelona.",
        "wiki_title": "Pablo_Picasso",
    },
    {
        "key": "football",
        "title_es": "El Fútbol Español (FC Barcelona y Real Madrid)",
        "intro_es": "El clásico entre Barça y Madrid refleja rivalidad deportiva y cultural.",
        "wiki_title": "El_Clásico",
    },
    {
        "key": "gaudi",
        "title_es": "La Sagrada Família y Antoni Gaudí",
        "intro_es": "Arquitecto modernista; su obra define el paisaje urbano de Barcelona.",
        "wiki_title": "Sagrada_Família",
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


def get_spain_news() -> dict[str, Any]:
    cache = _load_cache()
    cached = cache.get("spain_news")
    if cached and _cache_is_fresh(cached.get("fetched_at"), 3600):
        return {
            "articles": cached.get("articles", []),
            "error": None,
            "fetched_at": cached.get("fetched_at"),
        }

    if not NEWS_API_KEY:
        return {
            "articles": cached.get("articles", []) if cached else [],
            "error": "Falta la clave NEWS_API_KEY en el archivo .env.",
            "fetched_at": cached.get("fetched_at") if cached else None,
        }

    try:
        response = requests.get(
            NEWS_API_URL,
            params={
                "q": "Spain",
                "language": "es",
                "sortBy": "publishedAt",
                "pageSize": 12,
                "apiKey": NEWS_API_KEY,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        raw = data.get("articles") or []
        articles = []
        for item in raw:
            title = (item.get("title") or "").strip()
            description = (item.get("description") or "").strip()
            if not title or not description:
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
        now = datetime.now(timezone.utc).isoformat()
        cache["spain_news"] = {"articles": articles, "fetched_at": now}
        _save_cache(cache)
        if not articles:
            return {
                "articles": [],
                "error": "No hay artículos disponibles en este momento.",
                "fetched_at": now,
            }
        return {"articles": articles, "error": None, "fetched_at": now}
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("get_spain_news failed: %s", exc)
        stale = cached.get("articles", []) if cached else []
        return {
            "articles": stale,
            "error": "No se pudieron cargar las noticias. Inténtalo más tarde.",
            "fetched_at": cached.get("fetched_at") if cached else None,
        }


def _wikipedia_hero_image(data: dict[str, Any]) -> str:
    """Prefer a larger image URL; avoid upscaling tiny thumbs in the UI."""
    original = data.get("originalimage") or {}
    if original.get("source"):
        return original["source"]
    thumb = data.get("thumbnail") or {}
    src = thumb.get("source", "")
    if not src:
        return ""
    width = thumb.get("width") or 0
    if width and width >= 640:
        return src
    return re.sub(r"/\d+px-", "/640px-", src, count=1)


def _fetch_wikipedia_summary(wiki_title: str) -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"{WIKIPEDIA_SUMMARY_URL}/{wiki_title}",
            timeout=15,
            headers={"User-Agent": "EstudioAbroad/1.0 (language study app)"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        urls = data.get("content_urls") or {}
        desktop = urls.get("desktop") or {}
        return {
            "extract": data.get("extract", ""),
            "thumbnail": _wikipedia_hero_image(data),
            "wiki_url": desktop.get("page", ""),
        }
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("Wikipedia fetch failed for %r: %s", wiki_title, exc)
        return None


def get_history_topics() -> list[dict[str, Any]]:
    cache = _load_cache()
    cache.setdefault("history", {})
    topics_out = []

    for meta in HISTORY_TOPICS:
        key = meta["key"]
        entry = cache["history"].get(key)
        if entry and _cache_is_fresh(entry.get("fetched_at"), 86400):
            thumb = entry.get("thumbnail", "")
            if thumb and re.search(r"/\d{2,3}px-", thumb):
                wiki = _fetch_wikipedia_summary(meta["wiki_title"])
                if wiki and wiki.get("thumbnail"):
                    entry = {**entry, "thumbnail": wiki["thumbnail"]}
                    cache["history"][key] = entry
            topics_out.append({**meta, **entry})
            continue

        wiki = _fetch_wikipedia_summary(meta["wiki_title"])
        now = datetime.now(timezone.utc).isoformat()
        if wiki:
            entry = {
                "extract": wiki.get("extract", ""),
                "thumbnail": wiki.get("thumbnail", ""),
                "wiki_url": wiki.get("wiki_url", ""),
                "fetched_at": now,
            }
        elif entry:
            entry = dict(entry)
        else:
            entry = {
                "extract": "",
                "thumbnail": "",
                "wiki_url": f"https://en.wikipedia.org/wiki/{meta['wiki_title']}",
                "fetched_at": now,
            }
        cache["history"][key] = entry
        topics_out.append({**meta, **entry})

    _save_cache(cache)
    return topics_out


def get_study_resources() -> list[dict[str, Any]]:
    return [dict(r) for r in STUDY_RESOURCES]
