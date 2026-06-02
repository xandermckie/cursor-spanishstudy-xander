"""
API fetchers for Estudio Personal — read/write data/cache.json.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

CATEGORIES = ["transit", "food", "places", "phrases", "emergencies"]

# Barcelona study seed — daily sentence source text
DAILY_SENTENCE_ES = (
    "¿Dónde está la estación de metro más cercana a la Plaça de Catalunya?"
)


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


def fetch_translation(text: str, source: str, target: str) -> str | None:
    """
    MyMemory: translate text between languages.
    GET https://api.mymemory.translated.net/get?q=...&langpair=source|target
    """
    if not text or not text.strip():
        return None

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
            return None

        return data.get("responseData", {}).get("translatedText")
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("fetch_translation failed: %s", exc)
        return None


def fetch_glosbe_examples(
    phrase: str, from_lang: str = "es", to_lang: str = "en"
) -> list[dict[str, str]]:
    """Glosbe stub — not used on homepage yet."""
    logger.debug("fetch_glosbe_examples stub: %r", phrase[:40])
    return []


def fetch_definition(word: str) -> dict[str, Any] | None:
    """
    DictionaryAPI.dev: English definition, phonetic, example.
    GET https://api.dictionaryapi.dev/api/v2/entries/en/{word}
    """
    if not word or not word.strip():
        return None

    key = word.strip().lower()
    try:
        response = requests.get(f"{DICTIONARY_API_BASE}/{key}", timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return _parse_definition(data)
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


def fetch_trivia_questions(amount: int = 5) -> list[dict[str, Any]]:
    """Open Trivia DB stub — not used on homepage yet."""
    logger.debug("fetch_trivia_questions stub: amount=%s", amount)
    return []


def refresh_homepage() -> dict[str, Any]:
    """Fetch daily sentence + word-of-day and write to cache."""
    logger.info("Refreshing homepage data from APIs…")

    en_text = fetch_translation(DAILY_SENTENCE_ES, "es", "en")
    if not en_text:
        en_text = "Where is the nearest metro station to Plaça de Catalunya?"

    daily = {
        "es": DAILY_SENTENCE_ES,
        "en": en_text,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    word_of_day = None
    first_word = en_text.split()[0].strip(".,?!").lower() if en_text else ""
    if first_word:
        word_of_day = fetch_definition(first_word)

    cache = _load_cache()
    cache["daily_sentence"] = daily
    cache["word_of_day"] = word_of_day
    cache["weak_areas"] = cache.get("weak_areas") or {
        cat: 0 for cat in CATEGORIES
    }
    cache["last_refresh"] = datetime.now(timezone.utc).isoformat()
    _save_cache(cache)

    return get_homepage()


def get_homepage() -> dict[str, Any]:
    """
    Return homepage payload from cache.
    If daily_sentence is missing, refresh from APIs first.
    """
    cache = _load_cache()
    daily = cache.get("daily_sentence")

    if not daily or not daily.get("en"):
        return refresh_homepage()

    return {
        "daily_sentence": daily,
        "word_of_day": cache.get("word_of_day"),
        "weak_areas": cache.get("weak_areas")
        or {cat: 0 for cat in CATEGORIES},
        "last_refresh": cache.get("last_refresh"),
        "from_cache": True,
    }


def run_refresh() -> None:
    """Full cache refresh — homepage data for now."""
    refresh_homepage()
    cache = _load_cache()
    cache.setdefault("translations", {})
    cache.setdefault("examples", {})
    cache.setdefault("quiz_history", [])
    _save_cache(cache)
