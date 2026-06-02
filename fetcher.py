"""
API fetcher stubs for Estudio Personal.

Each function will call an external API and update data/cache.json.
Implementation pending — stubs return None or empty structures for now.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_FILE = DATA_DIR / "cache.json"


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
    logger.debug("fetch_translation stub: %s %s→%s", text[:40], source, target)
    return None


def fetch_glosbe_examples(
    phrase: str, from_lang: str = "es", to_lang: str = "en"
) -> list[dict[str, str]]:
    """
    Glosbe: bilingual example sentences in context.
    GET https://glosbe.com/gapi/v0.1/translate?from=...&dest=...&phrase=...
    """
    logger.debug("fetch_glosbe_examples stub: %r", phrase[:40])
    return []


def fetch_definition(word: str) -> dict[str, Any] | None:
    """
    DictionaryAPI.dev: English definition, phonetic, example.
    GET https://api.dictionaryapi.dev/api/v2/entries/en/{word}
    """
    logger.debug("fetch_definition stub: %r", word)
    return None


def fetch_trivia_questions(amount: int = 5) -> list[dict[str, Any]]:
    """
    Open Trivia DB: multiple-choice quiz questions.
    GET https://opentdb.com/api.php?amount=N&type=multiple
    """
    logger.debug("fetch_trivia_questions stub: amount=%s", amount)
    return []


def run_refresh() -> None:
    """
    Orchestrate a full cache refresh — called by scheduler and GET /refresh.
    Pulls translations, examples, and writes to data/cache.json.
    """
    logger.info("run_refresh stub — no API calls yet.")
    cache = _load_cache()
    cache.setdefault("last_refresh", None)
    cache.setdefault("translations", {})
    cache.setdefault("examples", {})
    cache.setdefault("definitions", {})
    cache.setdefault("quiz_history", [])
    cache.setdefault("weak_areas", {})
    _save_cache(cache)
