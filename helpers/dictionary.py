"""DictionaryAPI.dev — definitions, phonetics, and usage examples."""

from __future__ import annotations

import logging
from typing import Any

import requests

import config
from helpers import storage

logger = logging.getLogger(__name__)


def fetch_word_details(word: str, use_cache: bool = True) -> dict[str, Any] | None:
    """
    Return definition, phonetic, and example for an English word.
    Cached as a dict per word key.
    """
    if not word or not word.strip():
        return None

    key = word.strip().lower()
    cache = storage.get_definitions_cache()

    if use_cache and key in cache:
        cached = cache[key]
        if isinstance(cached, dict):
            return cached if cached.get("definition") else None
        if isinstance(cached, str) and cached:
            return {"definition": cached, "phonetic": "", "example": ""}
        return None

    try:
        url = f"{config.DICTIONARY_API_BASE}/{key}"
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            cache[key] = {}
            storage.save_definitions_cache(cache)
            return None
        response.raise_for_status()
        data = response.json()
        details = _extract_details(data)
        cache[key] = details or {}
        storage.save_definitions_cache(cache)
        return details if details and details.get("definition") else None
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        logger.exception("Dictionary API failed for %r: %s", word, exc)
        cached = cache.get(key)
        if isinstance(cached, dict) and cached.get("definition"):
            return cached
        if isinstance(cached, str) and cached:
            return {"definition": cached, "phonetic": "", "example": ""}
        return None


def fetch_definition(word: str, use_cache: bool = True) -> str | None:
    """Return first definition text (backward-compatible helper)."""
    details = fetch_word_details(word, use_cache=use_cache)
    if details:
        return details.get("definition")
    return None


def _extract_details(data: list) -> dict[str, str] | None:
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
        if definition and example:
            break

    if not definition:
        return None

    return {
        "definition": definition,
        "phonetic": phonetic or "",
        "example": example or "",
    }
