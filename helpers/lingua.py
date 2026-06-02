"""Lingua Robot API — Spanish/Catalan conjugation and morphology (optional)."""

from __future__ import annotations

import logging
from typing import Any

import requests

import config
from helpers import storage

logger = logging.getLogger(__name__)

LINGUA_CACHE_FILE = "lingua_cache.json"


def _get_cache() -> dict[str, Any]:
    return storage.load_json(LINGUA_CACHE_FILE, {})


def _save_cache(cache: dict[str, Any]) -> None:
    storage.save_json(LINGUA_CACHE_FILE, cache)


def fetch_conjugation(
    word: str, lang: str = "es", use_cache: bool = True
) -> dict[str, Any] | None:
    """
    Fetch verb conjugation / morphology for a Spanish or Catalan word.
    Returns parsed tables or None when disabled or unavailable.
    """
    if not config.LINGUA_ROBOT_ENABLED:
        return None
    if not word or not word.strip():
        return None

    key = f"{lang}:{word.strip().lower()}"
    cache = _get_cache()
    if use_cache and key in cache:
        return cache[key] or None

    try:
        data = _request_lingua(word.strip(), lang)
        cache[key] = data or {}
        _save_cache(cache)
        return data
    except requests.ConnectionError as exc:
        logger.warning("Lingua Robot unavailable for %r: %s", word, exc)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Lingua Robot failed for %r: %s", word, exc)
        if key in cache and cache[key]:
            return cache[key]
        return None


def _request_lingua(word: str, lang: str) -> dict[str, Any] | None:
    """Try common Lingua Robot path patterns."""
    base = config.LINGUA_ROBOT_BASE
    headers = {"User-Agent": config.GLOSBE_USER_AGENT, "Accept": "application/json"}
    candidates = [
        f"{base}/verbs/{lang}/{word}",
        f"{base}/entries/{lang}/{word}",
        f"{base}/conjugate/{lang}/{word}",
    ]
    for url in candidates:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        data = response.json()
        return _normalize_response(data, word, lang)
    return None


def _normalize_response(
    data: dict | list, word: str, lang: str
) -> dict[str, Any] | None:
    if isinstance(data, list):
        if not data:
            return None
        data = data[0] if isinstance(data[0], dict) else {"entries": data}

    if not isinstance(data, dict):
        return None

    conjugations = data.get("conjugations") or data.get("conjugation")
    forms = data.get("forms") or data.get("inflections")
    tenses = data.get("tenses")

    if conjugations or forms or tenses:
        return {
            "word": word,
            "lang": lang,
            "conjugations": conjugations or forms or tenses,
            "raw": data,
        }

    if data.get("entries") or data.get("lexemes"):
        return {"word": word, "lang": lang, "entries": data.get("entries", data)}

    if len(data) > 0:
        return {"word": word, "lang": lang, "summary": data}

    return None
