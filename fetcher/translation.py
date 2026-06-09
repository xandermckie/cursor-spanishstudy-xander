"""Translation API orchestration and caching."""

from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any
from urllib.parse import quote

import requests

from fetcher.cache import _load_cache, _save_cache

logger = logging.getLogger(__name__)

MYMEMORY_URL = os.environ.get(
    "MYMEMORY_URL", "https://api.mymemory.translated.net/get"
)
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "")
_DEFAULT_LINGVA_URLS = ("https://lingva.ml/api/v1",)
LINGVA_URLS: tuple[str, ...] = tuple(
    url.rstrip("/")
    for url in (
        os.environ.get("LINGVA_URLS")
        or os.environ.get("LINGVA_URL")
        or ",".join(_DEFAULT_LINGVA_URLS)
    ).split(",")
    if url.strip()
)
LIBRETRANSLATE_URL = os.environ.get("LIBRETRANSLATE_URL", "").rstrip("/")

MAX_TRANSLATION_CACHE = 500


def _translation_cache_key(text: str, source: str, target: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{target}:{digest}"


def _is_valid_translation(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    return "MYMEMORY WARNING" not in cleaned.upper()


def _fetch_mymemory(
    text: str, source: str, target: str, *, timeout: int = 15
) -> str | None:
    params: dict[str, str] = {
        "q": text[:500],
        "langpair": f"{source}|{target}",
    }
    if MYMEMORY_EMAIL:
        params["de"] = MYMEMORY_EMAIL

    try:
        response = requests.get(MYMEMORY_URL, params=params, timeout=timeout)
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            return None

        if data.get("responseStatus") != 200:
            logger.warning(
                "MyMemory error: %s", data.get("responseDetails", "unknown")
            )
            return None

        translated = (data.get("responseData", {}).get("translatedText") or "").strip()
        if not _is_valid_translation(translated):
            return None
        return translated
    except requests.RequestException as exc:
        logger.warning("MyMemory request failed: %s", exc)
        return None


def _fetch_lingva_instance(
    base_url: str,
    text: str,
    source: str,
    target: str,
    *,
    timeout: int = 20,
) -> str | None:
    supported = {"en", "es", "ca"}
    if source not in supported or target not in supported:
        return None

    try:
        path = (
            f"{base_url}/{source}/{target}/"
            f"{quote(text[:500], safe='')}"
        )
        response = requests.get(path, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        translated = (data.get("translation") or "").strip()
        if not _is_valid_translation(translated):
            return None
        return translated
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Lingva fallback failed (%s): %s", base_url, exc)
        return None


def _fetch_libretranslate(
    text: str, source: str, target: str, *, timeout: int = 20
) -> str | None:
    if not LIBRETRANSLATE_URL:
        return None

    try:
        response = requests.post(
            LIBRETRANSLATE_URL,
            json={
                "q": text[:500],
                "source": source,
                "target": target,
                "format": "text",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        translated = (data.get("translatedText") or "").strip()
        if not _is_valid_translation(translated):
            return None
        return translated
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning("LibreTranslate fallback failed: %s", exc)
        return None


def _translation_provider_calls(
    text: str, source: str, target: str, *, timeout: int
) -> list[tuple[str, Any]]:
    calls: list[tuple[str, Any]] = []
    for base_url in LINGVA_URLS:
        calls.append(
            (
                f"lingva:{base_url}",
                lambda url=base_url: _fetch_lingva_instance(
                    url, text, source, target, timeout=timeout
                ),
            )
        )
    calls.append(
        ("mymemory", lambda: _fetch_mymemory(text, source, target, timeout=timeout)),
    )
    if LIBRETRANSLATE_URL:
        calls.append(
            (
                "libretranslate",
                lambda: _fetch_libretranslate(text, source, target, timeout=timeout),
            )
        )
    return calls


def _fetch_translation_live(
    text: str, source: str, target: str, *, timeout: int = 12
) -> str | None:
    """Race free translation providers; return the first valid result."""
    calls = _translation_provider_calls(text, source, target, timeout=timeout)
    if not calls:
        return None

    executor = ThreadPoolExecutor(max_workers=len(calls))
    futures = {executor.submit(call): name for name, call in calls}
    pending = set(futures)
    translated = None

    try:
        while pending and translated is None:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                provider = futures[future]
                try:
                    candidate = future.result()
                except Exception as exc:
                    logger.warning("Translation provider %s crashed: %s", provider, exc)
                    continue
                if candidate:
                    logger.info("Translation succeeded via %s", provider)
                    translated = candidate
                    break
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return translated


def _store_translation(
    cache: dict[str, Any], key: str, translated: str
) -> tuple[str, bool]:
    translations = cache.setdefault("translations", {})
    translations[key] = translated
    while len(translations) > MAX_TRANSLATION_CACHE:
        del translations[next(iter(translations))]
    _save_cache(cache)
    return translated, False


def _fetch_translation_with_timeout(
    text: str,
    source: str,
    target: str,
    *,
    timeout: int,
    use_cache: bool = True,
) -> tuple[str | None, bool]:
    if not text or not text.strip():
        return None, False

    cache = _load_cache()
    cache.setdefault("translations", {})
    key = _translation_cache_key(text, source, target)

    if use_cache and key in cache["translations"]:
        return cache["translations"][key], True

    translated = _fetch_translation_live(text, source, target, timeout=timeout)

    if translated:
        return _store_translation(cache, key, translated)

    if key in cache["translations"]:
        return cache["translations"][key], True
    return None, False


def fetch_translation(
    text: str, source: str, target: str, use_cache: bool = True
) -> tuple[str | None, bool]:
    """
    Translate with JSON cache. Races MyMemory, Lingva, and LibreTranslate.
    Returns (text, from_cache).
    """
    return _fetch_translation_with_timeout(
        text, source, target, timeout=12, use_cache=use_cache
    )


def fetch_translation_fast(
    text: str, source: str, target: str, use_cache: bool = True
) -> tuple[str | None, bool]:
    """
    Voice UI translation — same parallel providers with a shorter per-call timeout.
    """
    return _fetch_translation_with_timeout(
        text, source, target, timeout=8, use_cache=use_cache
    )
