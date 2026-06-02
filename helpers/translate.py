"""MyMemory translation API wrapper with cache fallback."""

from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timezone

import requests

import config
from helpers import storage

logger = logging.getLogger(__name__)

# ISO 639-1 codes used by MyMemory langpair
LANG_CODES = {"es", "ca", "en", "eng", "spa", "cat"}


def _normalize_lang(code: str) -> str:
    """Map ISO 639-3 / aliases to MyMemory ISO 639-1 codes."""
    mapping = {
        "spa": "es",
        "es": "es",
        "cat": "ca",
        "ca": "ca",
        "eng": "en",
        "en": "en",
    }
    return mapping.get(code.lower(), code.lower()[:2])


def _cache_key(text: str, source: str, target: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{_normalize_lang(source)}:{_normalize_lang(target)}:{digest}"


def translate_text(
    text: str, source: str, target: str
) -> tuple[str, bool]:
    """
    Translate text via MyMemory.
    Returns (translated_text, from_cache).
    """
    if not text or not text.strip():
        return text, False

    source = _normalize_lang(source)
    target = _normalize_lang(target)
    key = _cache_key(text, source, target)
    cache = storage.get_translations_cache()

    if key in cache:
        return cache[key], True

    try:
        params: dict[str, str] = {
            "q": text[:500],
            "langpair": f"{source}|{target}",
        }
        if config.MYMEMORY_EMAIL:
            params["de"] = config.MYMEMORY_EMAIL

        response = requests.get(config.MYMEMORY_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("responseStatus") != 200:
            raise ValueError(data.get("responseDetails", "Translation failed"))

        translated = data.get("responseData", {}).get("translatedText", text)
        cache[key] = translated
        storage.save_translations_cache(cache)
        return translated, False
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("MyMemory translation failed: %s", exc)
        if key in cache:
            return cache[key], True
        return text, True


def fetch_memory_examples(
    phrase: str,
    source: str = "es",
    target: str = "en",
    limit: int = 5,
) -> list[dict[str, str]]:
    """
    Pull bilingual example segments from MyMemory match results.
    Used when Glosbe is unavailable.
    """
    if not phrase or not phrase.strip():
        return []

    source = _normalize_lang(source)
    target = _normalize_lang(target)

    try:
        params: dict[str, str] = {
            "q": phrase[:500],
            "langpair": f"{source}|{target}",
        }
        if config.MYMEMORY_EMAIL:
            params["de"] = config.MYMEMORY_EMAIL

        response = requests.get(config.MYMEMORY_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        examples = []
        for match in data.get("matches", [])[:limit]:
            segment = match.get("segment", "")
            translation = match.get("translation", "")
            if segment and translation:
                if source in ("es", "ca"):
                    examples.append({"source": segment, "target": translation})
                else:
                    examples.append({"source": translation, "target": segment})
        return examples
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception("MyMemory examples failed: %s", exc)
        return []


def warm_cache_from_vocab() -> None:
    """Populate translation cache from seeded English without API calls."""
    cache = storage.get_translations_cache()
    updated = False
    for item in storage.get_vocab():
        es_text = item.get("es", "")
        en_text = item.get("en", "")
        if not es_text or not en_text:
            continue
        key = _cache_key(es_text, "es", "en")
        if key not in cache:
            cache[key] = en_text
            updated = True
    if updated:
        storage.save_translations_cache(cache)


def refresh_daily_sentence() -> dict:
    """Pick random vocab entry and ensure daily sentence is stored."""
    vocab = storage.get_vocab()
    if not vocab:
        sentence = {
            "es": "Bienvenido a Barcelona.",
            "ca": "Benvingut a Barcelona.",
            "en": "Welcome to Barcelona.",
            "source_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        storage.save_daily_sentence(sentence)
        return sentence

    item = random.choice(vocab)
    es_text = item.get("es", "")
    en_text = item.get("en", "")

    translated, _from_cache = translate_text(es_text, "es", "en")
    if not translated or translated == es_text:
        translated = en_text

    sentence = {
        "es": es_text,
        "ca": item.get("ca", ""),
        "en": translated,
        "source_id": item.get("id"),
        "category": item.get("category"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.save_daily_sentence(sentence)
    return sentence
