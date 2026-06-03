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

DAILY_SENTENCE_ES = (
    "¿Dónde está la estación de metro más cercana a la Plaça de Catalunya?"
)

SPANISH_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "al", "a", "en", "y",
    "o", "que", "es", "está", "están", "más", "por", "con", "se", "su", "sus",
    "¿", "donde", "dónde", "cómo", "como", "qué", "me", "te", "le", "lo",
}

FLASHCARD_DECK_SEED = [
    {"es": "la estación de metro", "en": "the metro station"},
    {"es": "¿Cuánto cuesta?", "en": "How much does it cost?"},
    {"es": "el menú del día", "en": "the set lunch menu"},
    {"es": "la cuenta, por favor", "en": "the bill, please"},
    {"es": "¿Dónde está el baño?", "en": "Where is the bathroom?"},
    {"es": "un billete de bus", "en": "a bus ticket"},
    {"es": "la playa", "en": "the beach"},
    {"es": "buenos días", "en": "good morning"},
    {"es": "gracias", "en": "thank you"},
    {"es": "necesito ayuda", "en": "I need help"},
]

READER_PASSAGES_SEED = [
    {
        "id": "es-barcelona",
        "lang": "es",
        "title": "Lectura del día — La Ciudad Condal",
        "body": (
            "Barcelona es una ciudad única en el mundo. Sus calles están llenas de "
            "historia, arte y vida. Puedes pasear por el Barrio Gótico, visitar el "
            "mercado de La Boqueria, o simplemente sentarte en la terraza de un café "
            "y observar la gente pasar. El idioma de la calle es el catalán, pero "
            "todo el mundo habla castellano también."
        ),
        "en": (
            "Barcelona is a unique city in the world. Its streets are full of "
            "history, art and life. You can walk through the Gothic Quarter, visit "
            "La Boqueria market, or simply sit on a café terrace and watch people "
            "pass by. The language of the street is Catalan, but everyone speaks "
            "Spanish too."
        ),
    },
    {
        "id": "ca-phrases",
        "lang": "ca",
        "title": "Frase en Català",
        "body": (
            "Bon dia! Com estàs? Vull un cafè amb llet, si us plau. Quant costa? "
            "Moltes gràcies, fins aviat."
        ),
        "en": (
            "Good morning! How are you? I'd like a coffee with milk, please. "
            "How much does it cost? Thank you very much, see you soon."
        ),
    },
]


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
    """Fetch daily sentence + Spanish word-of-day; write cache."""
    logger.info("Refreshing homepage data from APIs…")

    en_text, _ = fetch_translation(DAILY_SENTENCE_ES, "es", "en")
    if not en_text:
        en_text = "Where is the nearest metro station to Plaça de Catalunya?"

    daily = {
        "es": DAILY_SENTENCE_ES,
        "en": en_text,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    es_word = _pick_spanish_headword(DAILY_SENTENCE_ES)
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
        "example_es": DAILY_SENTENCE_ES,
        "example_en": en_text,
    }

    cache = _load_cache()
    cache["daily_sentence"] = daily
    cache["word_of_day"] = word_of_day
    cache.setdefault("weak_words", {})
    cache.setdefault("phrasebook", [])
    cache["last_refresh"] = datetime.now(timezone.utc).isoformat()
    _save_cache(cache)

    return get_homepage()


def get_homepage() -> dict[str, Any]:
    cache = _load_cache()
    daily = cache.get("daily_sentence")

    if not daily or not daily.get("en"):
        return refresh_homepage()

    wod = cache.get("word_of_day")
    if wod and not wod.get("es"):
        refresh_homepage()
        cache = _load_cache()
        wod = cache.get("word_of_day")

    return {
        "daily_sentence": daily,
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
    if not deck:
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
    if not passages:
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
    weak_top = get_weak_words()[:5]
    return {
        "passages": passages,
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
