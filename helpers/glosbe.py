"""Glosbe v0.1 API — bilingual example sentences with MyMemory fallback."""

from __future__ import annotations

import logging
import time

import requests

import config
from helpers import storage, translate

logger = logging.getLogger(__name__)

MAX_EXAMPLES = 5

# Glosbe uses ISO 639-3 three-letter codes
GLOSBE_LANG = {"es": "spa", "ca": "cat", "en": "eng", "spa": "spa", "cat": "cat", "eng": "eng"}


def _to_glosbe_lang(code: str) -> str:
    return GLOSBE_LANG.get(code.lower(), code.lower())


def fetch_examples(
    phrase: str,
    from_lang: str = "es",
    to_lang: str = "en",
    use_cache: bool = True,
) -> list[dict[str, str]]:
    """Fetch bilingual example sentences for a phrase."""
    if not phrase or not phrase.strip():
        return []

    cache_key = f"{from_lang}:{phrase}"
    cache = storage.get_glosbe_cache()
    if use_cache and cache_key in cache:
        return cache[cache_key]

    examples: list[dict[str, str]] = []
    try:
        examples = _fetch_from_glosbe(phrase, from_lang, to_lang)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("Glosbe fetch failed for %r: %s", phrase, exc)

    if not examples:
        examples = translate.fetch_memory_examples(phrase, from_lang, to_lang, MAX_EXAMPLES)
        if examples:
            logger.info("Using MyMemory examples for %r (Glosbe unavailable).", phrase[:40])

    cache[cache_key] = examples
    storage.save_glosbe_cache(cache)
    return examples


def _headers() -> dict[str, str]:
    return {"User-Agent": config.GLOSBE_USER_AGENT, "Accept": "application/json"}


def _fetch_from_glosbe(
    phrase: str, from_lang: str, to_lang: str
) -> list[dict[str, str]]:
    """Call Glosbe gapi v0.1 translate with translation memory examples."""
    glosbe_from = _to_glosbe_lang(from_lang)
    glosbe_to = _to_glosbe_lang(to_lang)

    params = {
        "from": glosbe_from,
        "dest": glosbe_to,
        "phrase": phrase,
        "format": "json",
        "tm": "true",
    }
    response = requests.get(
        config.GLOSBE_URL, params=params, headers=_headers(), timeout=15
    )
    if response.status_code == 404:
        return []
    response.raise_for_status()
    data = response.json()
    return _parse_glosbe_response(data, glosbe_from, glosbe_to)


def _parse_glosbe_response(
    data: dict, from_lang: str, to_lang: str
) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []

    for ex in data.get("examples", [])[:MAX_EXAMPLES]:
        first = ex.get("first") or ex.get("source", "")
        second = ex.get("second") or ex.get("target", "")
        if first and second:
            examples.append({"source": first, "target": second})

    if examples:
        return examples

    for ex in data.get("tm", [])[:MAX_EXAMPLES]:
        first = ex.get("first", "")
        second = ex.get("second", "")
        if first and second:
            examples.append({"source": first, "target": second})

    if examples:
        return examples

    for tuc in data.get("tuc", [])[:MAX_EXAMPLES]:
        phrase_obj = tuc.get("phrase", {})
        text = phrase_obj.get("text", "")
        if text:
            examples.append({"source": data.get("phrase", phrase), "target": text})

    return examples[:MAX_EXAMPLES]


def fetch_examples_with_delay(
    phrase: str,
    from_lang: str = "es",
    to_lang: str = "en",
    delay: float = 0.5,
) -> list[dict[str, str]]:
    """Fetch examples with optional rate-limit delay."""
    if delay > 0:
        time.sleep(delay)
    return fetch_examples(phrase, from_lang, to_lang, use_cache=False)
