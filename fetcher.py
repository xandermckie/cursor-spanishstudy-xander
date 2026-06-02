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


def _ensure_reader_passages(cache: dict[str, Any]) -> list[dict[str, Any]]:
    """Load reader passages from cache or seed; optionally refresh EN via API."""
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
        translated = fetch_translation(passage.get("body", ""), src, "en")
        if translated:
            passage["en"] = translated
            updated = True
    if updated:
        cache["reader_passages"] = passages
        _save_cache(cache)
    return passages


def get_reader() -> dict[str, Any]:
    """Return fog-reader passages and weak-area stats for the reader page."""
    cache = _load_cache()
    cache.setdefault("weak_areas", {cat: 0 for cat in CATEGORIES})
    passages = _ensure_reader_passages(cache)

    weak_areas = cache.get("weak_areas") or {cat: 0 for cat in CATEGORIES}
    max_misses = max(weak_areas.values()) if weak_areas else 1
    progress = []
    labels = {
        "transit": "Transit",
        "food": "Food & Drink",
        "places": "Places",
        "phrases": "Phrases",
        "emergencies": "Emergencies",
    }
    for cat in CATEGORIES:
        misses = weak_areas.get(cat, 0)
        pct = max(0, min(100, 100 - int((misses / max(max_misses, 1)) * 50)))
        progress.append({"label": labels.get(cat, cat), "pct": pct, "category": cat})

    return {
        "passages": passages,
        "weak_areas": weak_areas,
        "progress": progress,
    }


def run_refresh() -> None:
    """Full cache refresh — homepage data for now."""
    refresh_homepage()
    cache = _load_cache()
    _ensure_reader_passages(cache)
    cache.setdefault("translations", {})
    cache.setdefault("examples", {})
    cache.setdefault("quiz_history", [])
    _save_cache(cache)
