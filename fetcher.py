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
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

import user_store
from fetcher_seeds import (
    DAILY_PHRASES_ES,
    DAILY_SENTENCES_ES,
    FLASHCARD_DECK_SEED,
    READER_PASSAGES_SEED,
    WIKIPEDIA_ARTICLES_ES,
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

PHRASE_MAX_LENGTH = 500


def _safe_https_url(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    trimmed = url.strip()
    if trimmed.lower().startswith("https://"):
        return trimmed
    return None


def _csv_cell(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text

def _utc_day_index(pool_len: int) -> int:
    if pool_len <= 0:
        return 0
    return datetime.now(timezone.utc).timetuple().tm_yday % pool_len


def _reader_passage_index(pool_len: int) -> int:
    if pool_len <= 0:
        return 0
    return (int(datetime.now(timezone.utc).timestamp()) // 900) % pool_len


def _load_cache_from_disk() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with CACHE_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("Corrupt cache file %s: %s", CACHE_FILE, exc)
        return {}
    except OSError as exc:
        logger.error("Failed to read cache file %s: %s", CACHE_FILE, exc)
        return {}


def _load_cache() -> dict[str, Any]:
    try:
        from flask import g, has_request_context

        if has_request_context():
            cached = getattr(g, "_estudio_global_cache", None)
            if cached is not None:
                return cached
            cached = _load_cache_from_disk()
            g._estudio_global_cache = cached
            return cached
    except ImportError:
        pass
    return _load_cache_from_disk()


def _save_cache(cache: dict[str, Any]) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = CACHE_FILE.with_suffix(".json.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        tmp_path.replace(CACHE_FILE)
        return True
    except OSError as exc:
        logger.error("Failed to write cache file: %s", exc)
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False


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
    if not re.match(r"^[\w.-]+$", key):
        return None
    try:
        response = requests.get(
            f"{DICTIONARY_API_BASE}/{quote(key, safe='')}", timeout=10
        )
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


def _activity_today() -> str:
    """Calendar day for streak tracking (Europe/Madrid)."""
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")


def _default_user_stats() -> dict[str, Any]:
    return {
        "xp_total": 0,
        "xp_today": 0,
        "xp_daily_goal": 200,
        "level": 1,
        "streak_days": 0,
        "last_activity_date": None,
        "words_learned": 0,
        "accuracy_pct": 0,
        "total_correct": 0,
        "total_answered": 0,
    }


def _level_from_xp(xp_total: int) -> int:
    if xp_total >= 1000:
        return 5
    if xp_total >= 500:
        return 4
    if xp_total >= 250:
        return 3
    if xp_total >= 100:
        return 2
    return 1


def _xp_threshold_for_level(level: int) -> int:
    return {1: 0, 2: 100, 3: 250, 4: 500, 5: 1000}.get(level, 0)


def _xp_next_level_threshold(level: int) -> int | None:
    return {1: 100, 2: 250, 3: 500, 4: 1000}.get(level)


def _ensure_user_stats(cache: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    mutated = False
    stats = cache.get("user_stats")
    if not stats:
        stats = _default_user_stats()
        cache["user_stats"] = stats
        mutated = True
    for key, val in _default_user_stats().items():
        if key not in stats:
            stats[key] = val
            mutated = True
    return stats, mutated


def _load_user_cache_from_disk(user_id: str) -> dict[str, Any]:
    return user_store.load_user(user_id) or {}


def _load_user_cache(user_id: str) -> dict[str, Any]:
    try:
        from flask import g, has_request_context

        if has_request_context():
            caches = getattr(g, "_estudio_user_caches", None)
            if caches is None:
                caches = {}
                g._estudio_user_caches = caches
            if user_id in caches:
                return caches[user_id]
            loaded = _load_user_cache_from_disk(user_id)
            caches[user_id] = loaded
            return loaded
    except ImportError:
        pass
    return _load_user_cache_from_disk(user_id)


def _save_user_cache(user_id: str, cache: dict[str, Any]) -> bool:
    return user_store.save_user(user_id, cache)


def update_streak(user_id: str, cache: dict[str, Any] | None = None) -> None:
    """Increment streak on first activity of the day (Europe/Madrid)."""
    own_cache = cache is None
    if own_cache:
        cache = _load_user_cache(user_id)
    stats, _ = _ensure_user_stats(cache)
    today = _activity_today()
    last = stats.get("last_activity_date")
    if last == today:
        return
    stats["xp_today"] = 0
    if not last:
        stats["streak_days"] = 1
    else:
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d").date()
            today_dt = datetime.strptime(today, "%Y-%m-%d").date()
            delta = (today_dt - last_dt).days
            if delta == 1:
                stats["streak_days"] = stats.get("streak_days", 0) + 1
            else:
                stats["streak_days"] = 1
        except ValueError:
            stats["streak_days"] = 1
    stats["last_activity_date"] = today
    if own_cache:
        _save_user_cache(user_id, cache)


def update_xp(user_id: str, amount: int, cache: dict[str, Any] | None = None) -> None:
    if amount <= 0:
        return
    own_cache = cache is None
    if own_cache:
        cache = _load_user_cache(user_id)
    stats, _ = _ensure_user_stats(cache)
    update_streak(user_id, cache)
    stats["xp_total"] = stats.get("xp_total", 0) + amount
    stats["xp_today"] = stats.get("xp_today", 0) + amount
    stats["level"] = _level_from_xp(stats["xp_total"])
    if own_cache:
        _save_user_cache(user_id, cache)


def _stats_global_cache_fallback() -> dict[str, Any]:
    """Deck-only global cache for stats when disk load must be avoided."""
    return {"flashcard_deck": FLASHCARD_DECK_SEED}


def _compute_user_stats(
    cache: dict[str, Any], global_cache: dict[str, Any] | None = None
) -> dict[str, Any]:
    stats, _ = _ensure_user_stats(cache)
    if global_cache is None:
        global_cache = _load_cache()
    deck = global_cache.get("flashcard_deck") or FLASHCARD_DECK_SEED
    weak = cache.get("weak_words") or {}
    answered = stats.get("total_answered", 0)
    correct = stats.get("total_correct", 0)
    level = _level_from_xp(stats.get("xp_total", 0))
    floor_xp = _xp_threshold_for_level(level)
    next_xp = _xp_next_level_threshold(level)
    result = dict(stats)
    result["words_learned"] = max(0, len(deck) - len(weak))
    result["accuracy_pct"] = round(100 * correct / answered) if answered > 0 else 0
    result["level"] = level
    result["xp_in_level"] = stats.get("xp_total", 0) - floor_xp
    if next_xp is not None:
        result["xp_level_max"] = next_xp - floor_xp
        result["xp_to_next_level"] = next_xp - stats.get("xp_total", 0)
    else:
        result["xp_level_max"] = 500
        result["xp_to_next_level"] = 0
    return result


def get_user_stats(user_id: str | None = None) -> dict[str, Any]:
    """Return display-ready stats including xp_in_level, xp_level_max, xp_to_next_level."""
    try:
        if not user_id:
            cache: dict[str, Any] = {"user_stats": _default_user_stats()}
            return _compute_user_stats(cache)
        cache = _load_user_cache(user_id)
        _, mutated = _ensure_user_stats(cache)
        if mutated:
            _save_user_cache(user_id, cache)
        global_cache = _load_cache()
        return _compute_user_stats(cache, global_cache)
    except Exception as exc:
        logger.exception("get_user_stats failed: %s", exc)
        fallback_cache: dict[str, Any] = {"user_stats": _default_user_stats()}
        try:
            return _compute_user_stats(
                fallback_cache, global_cache=_stats_global_cache_fallback()
            )
        except Exception:
            logger.exception("get_user_stats fallback compute failed")
            result = _default_user_stats()
            result.update(
                {
                    "xp_in_level": 0,
                    "xp_level_max": 100,
                    "xp_to_next_level": 100,
                    "level": 1,
                }
            )
            return result


def get_user_nav_info(user_id: str) -> dict[str, Any]:
    """Lightweight user info for nav (avatar ext without extra disk reads)."""
    cache = _load_user_cache(user_id)
    profile = cache.get("profile") or {}
    return {
        "email": cache.get("email"),
        "avatar_ext": profile.get("avatar_ext"),
    }


def get_last_refresh_display() -> str:
    cache = _load_cache()
    return format_refresh_time(cache.get("last_refresh"))


def reset_vocab_session(user_id: str) -> None:
    cache = _load_user_cache(user_id)
    global_cache = _load_cache()
    deck = _ensure_flashcard_deck(global_cache)
    
    # Create shuffled indices
    shuffled_order = list(range(len(deck)))
    random.shuffle(shuffled_order)
    
    cache["vocab_session"] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "correct_count": 0,
        "missed_count": 0,
        "complete": False,
        "expected_index": 0,
        "visited_indices": [],
        "shuffled_order": shuffled_order,
    }
    _save_user_cache(user_id, cache)


def _ensure_vocab_session(cache: dict[str, Any]) -> dict[str, Any]:
    session = cache.get("vocab_session")
    global_cache = _load_cache()
    deck = _ensure_flashcard_deck(global_cache)
    deck_size = len(deck)
    
    if not session:
        # Generate shuffled order for new session
        shuffled_order = list(range(deck_size))
        random.shuffle(shuffled_order)
        
        session = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "correct_count": 0,
            "missed_count": 0,
            "complete": False,
            "expected_index": 0,
            "visited_indices": [],
            "shuffled_order": shuffled_order,
        }
        cache["vocab_session"] = session
    session.setdefault("expected_index", 0)
    session.setdefault("visited_indices", [])
    
    # Ensure shuffled_order exists for existing sessions or regenerate if deck size changed
    if "shuffled_order" not in session or len(session.get("shuffled_order", [])) != deck_size:
        shuffled_order = list(range(deck_size))
        random.shuffle(shuffled_order)
        session["shuffled_order"] = shuffled_order
    
    return session


def award_reader_xp(user_id: str | None) -> None:
    """+5 XP once per calendar day for opening the reader."""
    if not user_id:
        return
    cache = _load_user_cache(user_id)
    today = _activity_today()
    awarded = cache.get("reader_xp_dates") or []
    if today in awarded:
        return
    awarded.append(today)
    cache["reader_xp_dates"] = awarded[-30:]
    update_xp(user_id, 5, cache)
    _save_user_cache(user_id, cache)


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
    cache["last_refresh"] = now_iso
    if not _save_cache(cache):
        logger.error("refresh_homepage: failed to write cache")
        return _homepage_fallback()

    return get_homepage(_refreshing=True)


def _homepage_fallback(user_id: str | None = None) -> dict[str, Any]:
    return {
        "daily_sentence": None,
        "daily_phrase": None,
        "word_of_day": None,
        "weak_words": [],
        "last_refresh": None,
        "last_refresh_display": "",
        "user_stats": get_user_stats(user_id),
        "error": True,
    }


def _homepage_from_cache(
    cache: dict[str, Any], user_id: str | None = None
) -> dict[str, Any] | None:
    daily = cache.get("daily_sentence")
    daily_phrase = cache.get("daily_phrase")
    if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
        return None
    return {
        "daily_sentence": daily,
        "daily_phrase": daily_phrase,
        "word_of_day": cache.get("word_of_day"),
        "weak_words": get_weak_words(user_id),
        "last_refresh": cache.get("last_refresh"),
        "last_refresh_display": format_refresh_time(cache.get("last_refresh")),
        "user_stats": get_user_stats(user_id),
        "error": True,
    }


def get_homepage(
    user_id: str | None = None, *, _refreshing: bool = False
) -> dict[str, Any]:
    try:
        cache = _load_cache()
        daily = cache.get("daily_sentence")
        daily_phrase = cache.get("daily_phrase")

        if not daily or not daily.get("en") or not daily_phrase or not daily_phrase.get("en"):
            if _refreshing:
                logger.error("get_homepage: cache still empty after refresh attempt")
                return _homepage_fallback(user_id)
            logger.info("get_homepage: cache miss; returning fallback (scheduler will refresh)")
            return _homepage_from_cache(cache, user_id) or _homepage_fallback(user_id)

        wod = cache.get("word_of_day")
        if wod and not wod.get("es"):
            logger.info("get_homepage: word_of_day incomplete; skipping inline refresh")

        return {
            "daily_sentence": daily,
            "daily_phrase": daily_phrase,
            "word_of_day": wod,
            "weak_words": get_weak_words(user_id),
            "last_refresh": cache.get("last_refresh"),
            "last_refresh_display": format_refresh_time(cache.get("last_refresh")),
            "user_stats": get_user_stats(user_id),
            "error": False,
        }
    except Exception as exc:
        logger.exception("get_homepage failed: %s", exc)
        return _homepage_fallback(user_id)


def get_weak_words(user_id: str | None = None) -> list[dict[str, Any]]:
    if not user_id:
        return []
    cache = _load_user_cache(user_id)
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


def get_vocab_session(user_id: str | None, index: int = 0) -> dict[str, Any]:
    try:
        global_cache = _load_cache()
        deck = _ensure_flashcard_deck(global_cache)
        total = len(deck)
        if not user_id:
            idx = index % total if total else 0
            card = deck[idx] if total else {"es": "", "en": ""}
            return {
                "card": card,
                "index": idx,
                "total": total,
                "next_index": (idx + 1) % total if total else 0,
                "correct_count": 0,
                "missed_count": 0,
                "complete": False,
                "section_failed": False,
                "read_only": True,
            }
        cache = _load_user_cache(user_id)
        session = cache.get("vocab_session") or {}
        if session.get("complete"):
            results = session.get("results", [])
            correct = session.get("correct_count", 0)
            missed = session.get("missed_count", 0)
            return {
                "complete": True,
                "correct_count": correct,
                "missed_count": missed,
                "xp_earned": correct * 10,
                "missed_words": [r for r in results if r.get("missed")],
                "total": total,
                "section_failed": False,
                "read_only": False,
            }
        if not cache.get("vocab_session"):
            _ensure_vocab_session(cache)
            _save_user_cache(user_id, cache)
            session = cache["vocab_session"]
        idx = session.get("expected_index", 0)
        if total:
            idx = idx % total
        
        # Use shuffled order to get the actual card
        shuffled_order = session.get("shuffled_order", list(range(total)))
        actual_deck_index = shuffled_order[idx] if idx < len(shuffled_order) else idx
        card = deck[actual_deck_index] if total else {"es": "", "en": ""}
        
        at_last = total > 0 and idx >= total - 1
        return {
            "card": card,
            "index": idx,
            "total": total,
            "next_index": 0 if at_last else (idx + 1) % total if total else 0,
            "correct_count": session.get("correct_count", 0),
            "missed_count": session.get("missed_count", 0),
            "complete": False,
            "section_failed": False,
            "read_only": False,
        }
    except Exception as exc:
        logger.exception("get_vocab_session failed: %s", exc)
        return {
            "card": {"es": "", "en": ""},
            "index": 0,
            "total": 0,
            "next_index": 0,
            "complete": False,
            "section_failed": True,
            "read_only": True,
        }


def record_flashcard_result(
    user_id: str, es: str, en: str, missed: bool, index: int = 0
) -> bool:
    if not user_id:
        return False
    try:
        global_cache = _load_cache()
        deck = _ensure_flashcard_deck(global_cache)
        total = len(deck)
        if total == 0 or index < 0 or index >= total:
            logger.warning("record_flashcard_result: invalid index %s", index)
            return False
        cache = _load_user_cache(user_id)
        session = _ensure_vocab_session(cache)
        if session.get("complete"):
            logger.warning("record_flashcard_result: session already complete")
            return False
        expected = session.get("expected_index", 0)
        if index != expected:
            logger.warning(
                "record_flashcard_result: index %s != expected %s",
                index,
                expected,
            )
            return False
        visited = session.setdefault("visited_indices", [])
        if index in visited:
            logger.warning("record_flashcard_result: index %s already visited", index)
            return False
        card = deck[index]
        if card.get("es", "").strip() != es.strip() or card.get("en", "").strip() != en.strip():
            logger.warning("record_flashcard_result: card mismatch at index %s", index)
            return False
        session.setdefault("results", [])
        session["results"].append({"es": es, "en": en, "missed": missed})
        visited.append(index)
        stats, _ = _ensure_user_stats(cache)
        stats["total_answered"] = stats.get("total_answered", 0) + 1
        if missed:
            session["missed_count"] = session.get("missed_count", 0) + 1
            if es:
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
        else:
            session["correct_count"] = session.get("correct_count", 0) + 1
            stats["total_correct"] = stats.get("total_correct", 0) + 1
            update_xp(user_id, 10, cache)
        update_streak(user_id, cache)
        if index >= total - 1:
            session["complete"] = True
        else:
            session["expected_index"] = index + 1
        return _save_user_cache(user_id, cache)
    except Exception as exc:
        logger.exception("record_flashcard_result failed: %s", exc)
        return False


def get_phrasebook(user_id: str | None) -> list[dict[str, Any]]:
    if not user_id:
        return []
    try:
        cache = _load_user_cache(user_id)
        return cache.get("phrasebook") or []
    except Exception as exc:
        logger.exception("get_phrasebook failed: %s", exc)
        return []


def add_phrase(user_id: str, user_input: str) -> dict[str, Any] | None:
    if not user_id:
        return None
    text = user_input.strip()
    if not text or len(text) > PHRASE_MAX_LENGTH:
        return None
    try:
        es_text, _ = fetch_translation(text, "en", "es")
        if not es_text:
            es_text = text

        cache = _load_user_cache(user_id)
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
        update_xp(user_id, 5, cache)
        update_streak(user_id, cache)
        if not _save_user_cache(user_id, cache):
            return None
        return entry
    except Exception as exc:
        logger.exception("add_phrase failed: %s", exc)
        return None


def update_phrase(user_id: str, phrase_id: str, user_input: str) -> bool:
    if not user_id:
        return False
    text = user_input.strip()
    if not text or len(text) > PHRASE_MAX_LENGTH:
        return False
    try:
        es_text, _ = fetch_translation(text, "en", "es")
        if not es_text:
            es_text = text

        cache = _load_user_cache(user_id)
        for entry in cache.get("phrasebook", []):
            if entry.get("id") == phrase_id:
                entry["input"] = text
                entry["es"] = es_text
                entry["updated_at"] = datetime.now(timezone.utc).isoformat()
                return _save_user_cache(user_id, cache)
        return False
    except Exception as exc:
        logger.exception("update_phrase failed: %s", exc)
        return False


def delete_phrase(user_id: str, phrase_id: str) -> bool:
    if not user_id:
        return False
    try:
        cache = _load_user_cache(user_id)
        book = cache.get("phrasebook", [])
        new_book = [e for e in book if e.get("id") != phrase_id]
        if len(new_book) == len(book):
            return False
        cache["phrasebook"] = new_book
        return _save_user_cache(user_id, cache)
    except Exception as exc:
        logger.exception("delete_phrase failed: %s", exc)
        return False


def export_phrasebook_csv(user_id: str | None) -> str:
    header = ["input_en", "spanish", "created_at", "updated_at"]
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for entry in get_phrasebook(user_id):
            if not isinstance(entry, dict):
                continue
            writer.writerow([
                _csv_cell(entry.get("input", "")),
                _csv_cell(entry.get("es", "")),
                _csv_cell(entry.get("created_at", "")),
                _csv_cell(entry.get("updated_at", "")),
            ])
        return output.getvalue()
    except Exception as exc:
        logger.exception("export_phrasebook_csv failed: %s", exc)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        return output.getvalue()


def _fetch_wikipedia_article(title: str, lang: str = "es") -> dict[str, Any] | None:
    """Fetch main section of a Wikipedia article in the specified language."""
    try:
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "extracts",
            "exintro": True,  # Only the introduction section
            "explaintext": True,  # Plain text, no HTML
            "redirects": 1,
        }
        headers = {
            "User-Agent": "EstudioAbroadApp/1.0 (Spanish Learning App; educational use)"
        }
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None
        
        # Get the first (and should be only) page
        page = next(iter(pages.values()))
        extract = page.get("extract", "").strip()
        
        if not extract or len(extract) < 100:
            return None
        
        # Limit to reasonable length for reading practice (~800-1500 chars)
        # Take first 3-4 paragraphs
        paragraphs = [p.strip() for p in extract.split("\n\n") if p.strip()]
        main_content = "\n\n".join(paragraphs[:3])
        
        # If still too long, trim to ~1200 chars at sentence boundary
        if len(main_content) > 1500:
            sentences = main_content.split(". ")
            trimmed = ""
            for sentence in sentences:
                if len(trimmed + sentence) > 1200:
                    break
                trimmed += sentence + ". "
            main_content = trimmed.strip()
        
        return {
            "title": page.get("title", title),
            "body": main_content,
            "lang": lang,
            "source": "wikipedia",
        }
    except Exception as exc:
        logger.warning("Failed to fetch Wikipedia article %r: %s", title, exc)
        return None


def _ensure_wikipedia_passages(cache: dict[str, Any]) -> None:
    """Fetch and cache Wikipedia articles for reader rotation."""
    wiki_passages = cache.get("wikipedia_passages")
    last_fetch = cache.get("wikipedia_last_fetch")
    
    # Refresh every 24 hours
    now = datetime.now(timezone.utc)
    should_refresh = (
        not wiki_passages
        or not last_fetch
        or (now - datetime.fromisoformat(last_fetch)).total_seconds() > 86400
    )
    
    if not should_refresh:
        return
    
    logger.info("Fetching Wikipedia articles for reader...")
    wiki_passages = []
    
    for title in WIKIPEDIA_ARTICLES_ES:
        article = _fetch_wikipedia_article(title, "es")
        if article:
            # Generate unique ID
            article["id"] = f"wiki-{hashlib.md5(title.encode()).hexdigest()[:8]}"
            
            # Translate to English
            translated, _ = fetch_translation(article["body"], "es", "en")
            article["en"] = translated if translated else article["body"]
            
            wiki_passages.append(article)
    
    if wiki_passages:
        cache["wikipedia_passages"] = wiki_passages
        cache["wikipedia_last_fetch"] = now.isoformat()
        _save_cache(cache)
        logger.info("Cached %d Wikipedia articles", len(wiki_passages))


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


def get_reader(user_id: str | None = None) -> dict[str, Any]:
    try:
        cache = _load_cache()
        
        # Get both seed passages and Wikipedia articles
        seed_passages = _ensure_reader_passages(cache)
        _ensure_wikipedia_passages(cache)
        wiki_passages = cache.get("wikipedia_passages", [])
        
        # Combine all passages for daily rotation
        all_passages = seed_passages + wiki_passages
        
        if not all_passages:
            return {
                "passages": [],
                "weak_words_top": [],
                "section_failed": True,
            }
        
        # Use daily rotation (based on day of year)
        idx = _utc_day_index(len(all_passages))
        weak_top = get_weak_words(user_id)[:5]
        award_reader_xp(user_id)
        
        return {
            "passages": [all_passages[idx]],
            "weak_words_top": weak_top,
            "section_failed": False,
        }
    except Exception as exc:
        logger.exception("get_reader failed: %s", exc)
        return {
            "passages": [],
            "weak_words_top": [],
            "section_failed": True,
        }


def run_refresh() -> None:
    refresh_homepage()
    cache = _load_cache()
    _ensure_reader_passages(cache)
    _ensure_wikipedia_passages(cache)
    _ensure_flashcard_deck(cache)
    cache.setdefault("translations", {})
    _save_cache(cache)
    if NEWS_API_KEY:
        get_spain_news()


# --- Travel, news, history, resources pages ---

NEWS_API_URL = os.environ.get(
    "NEWS_API_URL", "https://newsapi.org/v2/everything"
)
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
SPAIN_NEWS_RE = re.compile(
    r"\b(españa|espana|español|espanol|española|espanola|barcelona|madrid|"
    r"cataluña|catalunya|valencia|sevilla|andaluc|galicia|bilbao|zaragoza|"
    r"ibex|sánchez|sanchez|gobierno\s+español|reino\s+de\s+españa)\b",
    re.IGNORECASE,
)
HISTORY_TOPICS = [
    {
        "key": "civil_war",
        "title_es": "La Guerra Civil Española",
        "intro_es": "Conflicto de 1936–1939 que transformó la España del siglo XX.",
        "wiki_url": "https://en.wikipedia.org/wiki/Spanish_Civil_War",
        "summary_es": (
            "La Guerra Civil Española (1936–1939) enfrentó al bando republicano, apoyado por anarquistas, socialistas y catalanes que defendían la Segunda República, contra los sublevados nacionalistas liderados por Francisco Franco, con apoyo de la Alemania nazi y la Italia fascista. "
            "El conflicto empezó con un golpe militar contra el gobierno elegido y se extendió por casi tres años de combates brutales, bombardeos sobre ciudades como Barcelona y Madrid, y una profunda división social. "
            "En Cataluña, el republicanismo y el autogobierno catalán formaron parte del frente leal a la República; Barcelona vivió episodios decisivos y, al final, la ocupación franquista suprimió la Generalitat y el catalán en la escuela y la administración durante décadas. "
            "La guerra dejó cientos de miles de muertos, exilio masivo y un régimen autoritario que duró hasta la muerte de Franco en 1975. "
            "Para entender la España actual — debates sobre memoria histórica, estatutos autonómicos y símbolos en la calle — conviene conocer cómo esta guerra marcó familias, instituciones y el lenguaje político que aún se usa hoy."
        ),
        "summary_en": (
            "The Spanish Civil War (1936–1939) pitted the Republican side—backed by anarchists, socialists, and Catalans defending the Second Republic—against Nationalist rebels led by Francisco Franco, with support from Nazi Germany and Fascist Italy. "
            "The conflict began with a military coup against the elected government and lasted nearly three years of brutal fighting, air raids on cities such as Barcelona and Madrid, and deep social division. "
            "In Catalonia, republicanism and Catalan self-government were part of the loyal front; Barcelona saw decisive episodes and, in the end, Francoist occupation suppressed the Generalitat and Catalan in schools and public life for decades. "
            "The war left hundreds of thousands dead, mass exile, and an authoritarian regime that lasted until Franco's death in 1975. "
            "To understand Spain today—debates on historical memory, autonomy statutes, and symbols in the street—it helps to see how this war shaped families, institutions, and the political language still used now."
        ),
    },
    {
        "key": "picasso",
        "title_es": "Pablo Picasso",
        "intro_es": "Pintor malagueño; figura central del arte moderno y del Museo Picasso en Barcelona.",
        "wiki_url": "https://en.wikipedia.org/wiki/Pablo_Picasso",
        "summary_es": (
            "Pablo Ruiz Picasso nació en Málaga en 1881 y se formó como artista entre España y Francia, pero mantuvo lazos fuertes con Barcelona, donde abrió estudios y expuso en sus primeros años de fama. "
            "En la ciudad catalana convivió con el modernismo y con otros creadores; el Museu Picasso de Barcelona conserva una de las mejores colecciones de su obra juvenil y de las etapas azul y rosa. "
            "Picasso revolucionó el arte del siglo XX: del realismo académico pasó al cubismo, colaboró con Georges Braque y reinterpretó formas, perspectiva y materiales en pintura, escultura y cerámica. "
            "Su mural «Guernica» (1937) se convirtió en símbolo universal contra el bombardeo de la villa vasca durante la Guerra Civil y sigue siendo referencia en protestas y museos de todo el mundo. "
            "Estudiar su trayectoria en español permite conectar vocabulario de arte, política y ciudad: ver una obra en el museo del Born o en Málaga después de leer sobre ella en clase da contexto cultural real, no solo nombres en un libro de texto."
        ),
        "summary_en": (
            "Pablo Ruiz Picasso was born in Málaga in 1881 and trained as an artist in Spain and France, but kept strong ties with Barcelona, where he opened studios and showed work in his early years of fame. "
            "In the Catalan city he moved among modernism and other creators; the Picasso Museum in Barcelona holds one of the finest collections of his youth and Blue and Rose periods. "
            "Picasso revolutionized twentieth-century art: from academic realism he moved to Cubism, worked with Georges Braque, and reshaped form, perspective, and materials in painting, sculpture, and ceramics. "
            "His mural «Guernica» (1937) became a universal symbol against the bombing of the Basque town during the Civil War and remains a reference in protests and museums worldwide. "
            "Studying his career in Spanish connects art, politics, and city vocabulary: seeing a work in the Born museum or in Málaga after reading about it in class gives real cultural context, not only names in a textbook."
        ),
    },
    {
        "key": "football",
        "title_es": "El Fútbol Español (FC Barcelona y Real Madrid)",
        "intro_es": "El clásico entre Barça y Madrid refleja rivalidad deportiva y cultural.",
        "wiki_url": "https://en.wikipedia.org/wiki/El_Cl%C3%A1sico",
        "summary_es": (
            "El fútbol en España es mucho más que deporte: es identidad regional, economía de medios y ritual social semanal. "
            "El FC Barcelona y el Real Madrid encarnan el «clásico», el partido más visto del país, donde se mezclan rivalidad deportiva, símbolos catalanes y castellanos y narrativas políticas según el momento histórico. "
            "El Barça se identifica con el lema «Més que un club» y con la defensa del catalán en el estadio; el Madrid, con éxitos europeos y una imagen internacional muy marcada. "
            "La Liga, la Copa del Rey y la Champions generan un vocabulario útil para estudiantes: gol, fuera de juego, entrenador, afición, descenso, fichaje. "
            "En Barcelona, ir a un partido en el Spotify Camp Nou o verlo en un bar del barrio es una inmersión lingüística: escucharás gritos, cánticos y análisis en español y catalán. "
            "Aunque no sigas el deporte, entender por qué un domingo de clásico vacía calles o llena terrazas ayuda a leer la cultura popular española con más matices."
        ),
        "summary_en": (
            "Football in Spain is far more than sport: it is regional identity, media business, and a weekly social ritual. "
            "FC Barcelona and Real Madrid embody «El Clásico», the country's most watched match, mixing sporting rivalry, Catalan and Castilian symbols, and political narratives depending on the historical moment. "
            "Barça is tied to the motto «More than a club» and to defending Catalan in the stadium; Madrid, to European success and a strong international image. "
            "La Liga, the Copa del Rey, and the Champions League offer useful vocabulary for learners: goal, offside, coach, fans, relegation, signing. "
            "In Barcelona, attending a match at Spotify Camp Nou or watching in a neighborhood bar is language immersion: you will hear shouts, chants, and analysis in Spanish and Catalan. "
            "Even if you do not follow the sport, understanding why a Clásico Sunday empties streets or fills terraces helps you read Spanish popular culture with more nuance."
        ),
    },
    {
        "key": "gaudi",
        "title_es": "La Sagrada Família y Antoni Gaudí",
        "intro_es": "Arquitecto modernista; su obra define el paisaje urbano de Barcelona.",
        "wiki_url": "https://en.wikipedia.org/wiki/Sagrada_Fam%C3%ADlia",
        "summary_es": (
            "Antoni Gaudí i Cornet (1852–1926) es el arquitecto más emblemático del modernismo catalán y define, para muchos visitantes, la imagen de Barcelona. "
            "Su obra mezcla inspiración natural —formas de plantas, animales y oleaje— con estructuras innovadoras, trencadís (mosaico de cerámica rota) y una fe católica que impregna proyectos como la Sagrada Família, aún en construcción más de un siglo después de su inicio. "
            "Además del templo expiatorio, diseñó o intervino en la Casa Batlló, la Pedrera, el Park Güell y la Casa Vicens; caminar por el Eixample o subir al parque permite ver cómo el urbanismo de la ciudad se volvió escenario de su imaginación. "
            "Gaudí murió tras un accidente con un tranvía cuando la Sagrada Família llevaba solo una parte levantada; desde entonces arquitectos y artesanos han continuado el proyecto según sus planos y modelos. "
            "Para un estudiante en Barcelona, visitar estas obras conociendo vocabulario de arquitectura —fachada, nave, catenaria, balcón— convierte una salida de fin de semana en práctica de español ligada al entorno inmediato de la universidad y del metro que usa cada día."
        ),
        "summary_en": (
            "Antoni Gaudí i Cornet (1852–1926) is the most emblematic architect of Catalan modernism and, for many visitors, defines the image of Barcelona. "
            "His work blends natural inspiration—shapes of plants, animals, and waves—with innovative structures, trencadís (broken-tile mosaic), and a Catholic faith that runs through projects such as the Sagrada Família, still under construction more than a century after it began. "
            "Beyond the expiatory temple, he designed or shaped Casa Batlló, La Pedrera, Park Güell, and Casa Vicens; walking the Eixample or climbing the park shows how the city's urban plan became a stage for his imagination. "
            "Gaudí died after a tram accident when the Sagrada Família had only part of its structure raised; since then architects and craftspeople have continued the project from his plans and models. "
            "For a student in Barcelona, visiting these sites with architecture vocabulary—façade, nave, catenary, balcony—turns a weekend outing into Spanish practice tied to the university setting and the metro used every day."
        ),
    },
    {
        "key": "reconquista",
        "title_es": "La Reconquista y los Reyes Católicos",
        "intro_es": "Siglos de reconquista cristiana y la unificación de España bajo Isabel y Fernando.",
        "wiki_url": "https://en.wikipedia.org/wiki/Reconquista",
        "summary_es": (
            "La Reconquista (siglos VIII–XV) fue el proceso gradual mediante el cual los reinos cristianos del norte de la península ibérica recuperaron territorios bajo control musulmán tras la invasión omeya del año 711. "
            "En 1469, el matrimonio de Isabel de Castilla y Fernando de Aragón unió las dos coronas más poderosas y permitió la conquista final del reino nazarí de Granada en 1492, poniendo fin a casi ochocientos años de presencia musulmana en la península. "
            "Ese mismo año, los Reyes Católicos financiaron el viaje de Cristóbal Colón al Nuevo Mundo y firmaron el Edicto de Granada, que expulsó a los judíos no conversos, marcando el inicio de la Inquisición española y de una monarquía católica centralizada. "
            "Cataluña, bajo la Corona de Aragón, mantuvo instituciones propias (la Generalitat, el Consell de Cent en Barcelona) y proyección mediterránea hacia Nápoles y Sicilia. "
            "Esta época sienta las bases de la España moderna: lenguas regionales, tensiones centro-periferia, identidad católica y expansión imperial son temas que siguen vivos en debates actuales sobre autonomía, símbolos religiosos y memoria histórica."
        ),
        "summary_en": (
            "The Reconquista (8th–15th centuries) was the gradual process by which Christian kingdoms in the north of the Iberian Peninsula reclaimed territories under Muslim rule after the Umayyad invasion of 711. "
            "In 1469, the marriage of Isabella of Castile and Ferdinand of Aragon united the two most powerful crowns and enabled the final conquest of the Nasrid kingdom of Granada in 1492, ending nearly eight hundred years of Muslim presence in the peninsula. "
            "That same year, the Catholic Monarchs financed Christopher Columbus's voyage to the New World and signed the Edict of Granada, expelling unconverted Jews, marking the start of the Spanish Inquisition and a centralized Catholic monarchy. "
            "Catalonia, under the Crown of Aragon, kept its own institutions (the Generalitat, the Consell de Cent in Barcelona) and Mediterranean reach toward Naples and Sicily. "
            "This era lays the groundwork for modern Spain: regional languages, center-periphery tensions, Catholic identity, and imperial expansion remain alive in today's debates on autonomy, religious symbols, and historical memory."
        ),
    },
    {
        "key": "spanish_empire",
        "title_es": "El Imperio Español y el Siglo de Oro",
        "intro_es": "Expansión colonial y florecimiento cultural en los siglos XVI y XVII.",
        "wiki_url": "https://en.wikipedia.org/wiki/Spanish_Empire",
        "summary_es": (
            "Durante los siglos XVI y XVII, España construyó un imperio que se extendía desde las Filipinas hasta América Latina, convirtiéndose en la primera potencia global tras las conquistas de Hernán Cortés en México y Francisco Pizarro en Perú. "
            "La plata y el oro de las minas americanas financiaron guerras europeas, palacios reales y una corte en Madrid que atrajo a escritores, pintores y pensadores: Cervantes escribió el «Quijote», Velázquez pintó «Las Meninas», Lope de Vega y Calderón de la Barca renovaron el teatro. "
            "Este período, conocido como el Siglo de Oro, dejó un legado literario y artístico que define la lengua española hasta hoy; frases del Quijote, vocabulario náutico de la exploración y términos del barroco siguen presentes en clase y en museos. "
            "Barcelona, aunque parte de un reino con menos protagonismo colonial directo, se benefició del comercio mediterráneo y de las rutas que conectaban la península con Italia y el norte de África. "
            "El declive del imperio tras derrotas militares y crisis económicas en el siglo XVII sentó las bases de tensiones regionales y debates sobre centralismo que perduran en la política española contemporánea."
        ),
        "summary_en": (
            "During the 16th and 17th centuries, Spain built an empire stretching from the Philippines to Latin America, becoming the first global power after the conquests of Hernán Cortés in Mexico and Francisco Pizarro in Peru. "
            "Silver and gold from American mines financed European wars, royal palaces, and a court in Madrid that drew writers, painters, and thinkers: Cervantes wrote «Don Quixote», Velázquez painted «Las Meninas», Lope de Vega and Calderón de la Barca renewed theater. "
            "This period, known as the Golden Age, left a literary and artistic legacy that defines the Spanish language today; phrases from Quixote, nautical vocabulary from exploration, and Baroque terms remain present in class and museums. "
            "Barcelona, though part of a kingdom with less direct colonial prominence, benefited from Mediterranean trade and routes connecting the peninsula with Italy and North Africa. "
            "The empire's decline after military defeats and economic crises in the 17th century laid the groundwork for regional tensions and debates on centralism that persist in contemporary Spanish politics."
        ),
    },
    {
        "key": "catalan_modernism",
        "title_es": "El Modernismo Catalán",
        "intro_es": "Movimiento arquitectónico y artístico que transformó Barcelona a finales del siglo XIX.",
        "wiki_url": "https://en.wikipedia.org/wiki/Modernisme",
        "summary_es": (
            "El modernismo catalán (modernisme) fue un movimiento artístico y arquitectónico que floreció en Cataluña entre 1890 y 1910, coincidiendo con el crecimiento industrial de Barcelona y la Renaixença, el resurgimiento cultural y lingüístico catalán. "
            "Más allá de Gaudí, arquitectos como Lluís Domènech i Montaner (Palau de la Música Catalana, Hospital de Sant Pau) y Josep Puig i Cadafalch (Casa Amatller, Casa de les Punxes) diseñaron edificios que mezclan vidrieras, hierro forjado, cerámica de colores y referencias medievales con innovación estructural. "
            "El movimiento no se limitó a arquitectura: pintores como Ramon Casas y Santiago Rusiñol, escultores, diseñadores de muebles y tipógrafos crearon un estilo distintivo que identificaba modernidad con identidad catalana. "
            "La burguesía industrial de Barcelona financió muchos de estos proyectos, convirtiendo el Eixample en un museo al aire libre; hoy caminar por el Passeig de Gràcia permite ver fachadas modernistas en casi cada esquina. "
            "Estudiar este período en español permite practicar vocabulario de arte (fachada, azulejo, mosaico, hierro forjado) y de historia cultural, conectando clase con salidas reales a edificios que forman parte del día a día urbano."
        ),
        "summary_en": (
            "Catalan modernism (modernisme) was an artistic and architectural movement that flourished in Catalonia between 1890 and 1910, coinciding with Barcelona's industrial growth and the Renaixença, the Catalan cultural and linguistic revival. "
            "Beyond Gaudí, architects such as Lluís Domènech i Montaner (Palau de la Música Catalana, Hospital de Sant Pau) and Josep Puig i Cadafalch (Casa Amatller, Casa de les Punxes) designed buildings mixing stained glass, wrought iron, colorful ceramics, and medieval references with structural innovation. "
            "The movement was not limited to architecture: painters like Ramon Casas and Santiago Rusiñol, sculptors, furniture designers, and typographers created a distinctive style that identified modernity with Catalan identity. "
            "Barcelona's industrial bourgeoisie financed many of these projects, turning the Eixample into an open-air museum; today walking along Passeig de Gràcia lets you see modernist façades on nearly every corner. "
            "Studying this period in Spanish allows practicing art vocabulary (façade, tile, mosaic, wrought iron) and cultural history, connecting class with real visits to buildings that are part of daily urban life."
        ),
    },
    {
        "key": "transition",
        "title_es": "La Transición Española",
        "intro_es": "Paso de la dictadura franquista a la democracia (1975–1982).",
        "wiki_url": "https://en.wikipedia.org/wiki/Spanish_transition_to_democracy",
        "summary_es": (
            "La Transición Española es el proceso político que llevó a España de la dictadura de Franco, muerta con él en 1975, a una monarquía parlamentaria democrática con la Constitución de 1978. "
            "El rey Juan Carlos I, nombrado sucesor por Franco, jugó un papel clave al apoyar reformas democráticas; Adolfo Suárez, primer presidente del gobierno electo, negoció con partidos prohibidos (comunistas, socialistas, nacionalistas catalanes y vascos) para redactar una constitución que reconociera autonomías regionales y derechos civiles. "
            "En Cataluña, el retorno del presidente Tarradellas del exilio en 1977 y el restablecimiento de la Generalitat marcaron el inicio de la recuperación de la lengua y las instituciones catalanas suprimidas bajo el franquismo. "
            "La Transición no estuvo exenta de violencia: el intento de golpe de estado del 23-F en 1981, con el teniente coronel Tejero ocupando el Congreso a punta de pistola, casi descarrila el proceso democrático. "
            "Entender esta época es clave para leer la España actual: debates sobre memoria histórica, el papel de la monarquía, y tensiones autonómicas en Cataluña y el País Vasco tienen raíces directas en cómo se pactó y qué quedó sin resolver en aquellos años."
        ),
        "summary_en": (
            "The Spanish Transition is the political process that took Spain from Franco's dictatorship, which died with him in 1975, to a democratic parliamentary monarchy with the Constitution of 1978. "
            "King Juan Carlos I, named successor by Franco, played a key role by supporting democratic reforms; Adolfo Suárez, the first elected prime minister, negotiated with banned parties (communists, socialists, Catalan and Basque nationalists) to draft a constitution recognizing regional autonomies and civil rights. "
            "In Catalonia, the return of President Tarradellas from exile in 1977 and the reestablishment of the Generalitat marked the start of recovering the Catalan language and institutions suppressed under Francoism. "
            "The Transition was not without violence: the attempted coup d'état on February 23, 1981, with Lieutenant Colonel Tejero occupying Congress at gunpoint, nearly derailed the democratic process. "
            "Understanding this era is key to reading Spain today: debates on historical memory, the monarchy's role, and autonomy tensions in Catalonia and the Basque Country have direct roots in what was negotiated and what was left unresolved in those years."
        ),
    },
    {
        "key": "diada",
        "title_es": "La Diada y la Identidad Catalana",
        "intro_es": "Día nacional de Cataluña; símbolo de identidad y reivindicación autonómica.",
        "wiki_url": "https://en.wikipedia.org/wiki/National_Day_of_Catalonia",
        "summary_es": (
            "La Diada Nacional de Catalunya, celebrada cada 11 de septiembre, conmemora la caída de Barcelona ante las tropas borbónicas en 1714, al final de la Guerra de Sucesión Española, cuando Cataluña perdió sus instituciones propias y el catalán quedó relegado de la administración. "
            "Desde finales del siglo XIX, la Diada se convirtió en una fecha de reivindicación cultural y política: manifestaciones, actos institucionales, y desde 2012 grandes concentraciones independentistas que han reunido a cientos de miles de personas en el centro de Barcelona pidiendo un referéndum de autodeterminación. "
            "La senyera (bandera catalana), la estelada (bandera independentista), el himbre «Els Segadors» y el lema «Catalunya, nou estat d'Europa» forman parte del vocabulario visual y simbólico de la ciudad en septiembre. "
            "Para un estudiante en Barcelona, vivir la Diada es una inmersión en política y lengua: carteles, discursos, conversaciones en bares y metros mezclan catalán y español, y permiten entender tensiones entre identidad regional, nacionalismo español y proyecto europeo. "
            "Comprender la Diada ayuda a contextualizar por qué edificios públicos cuelgan lazos amarillos, por qué ciertos barrios son más independentistas que otros, y cómo el debate territorial domina las elecciones catalanas y españolas cada año."
        ),
        "summary_en": (
            "The National Day of Catalonia (Diada), celebrated every September 11, commemorates the fall of Barcelona to Bourbon troops in 1714, at the end of the War of the Spanish Succession, when Catalonia lost its own institutions and Catalan was sidelined from administration. "
            "Since the late 19th century, the Diada became a date of cultural and political vindication: demonstrations, institutional acts, and since 2012 large pro-independence gatherings that have brought hundreds of thousands to Barcelona's center demanding a self-determination referendum. "
            "The senyera (Catalan flag), the estelada (pro-independence flag), the anthem «Els Segadors», and the slogan «Catalunya, nou estat d'Europa» form part of the city's visual and symbolic vocabulary in September. "
            "For a student in Barcelona, experiencing the Diada is an immersion in politics and language: posters, speeches, conversations in bars and metros mix Catalan and Spanish, and allow understanding tensions between regional identity, Spanish nationalism, and the European project. "
            "Understanding the Diada helps contextualize why public buildings hang yellow ribbons, why certain neighborhoods are more pro-independence than others, and how the territorial debate dominates Catalan and Spanish elections every year."
        ),
    },
    {
        "key": "miro",
        "title_es": "Joan Miró y el Arte Contemporáneo",
        "intro_es": "Pintor y escultor catalán; figura clave del surrealismo europeo.",
        "wiki_url": "https://en.wikipedia.org/wiki/Joan_Mir%C3%B3",
        "summary_es": (
            "Joan Miró i Ferrà (1893–1983) nació en Barcelona y se convirtió en uno de los artistas más influyentes del siglo XX, reconocido por sus obras surrealistas con formas orgánicas, colores primarios y símbolos que mezclan lo onírico con referencias a la tierra catalana. "
            "A diferencia de Picasso, Miró mantuvo toda su vida un compromiso profundo con Barcelona y con Mallorca, donde pasó sus últimos años; la Fundació Joan Miró, inaugurada en Montjuïc en 1975, exhibe más de diez mil obras entre pinturas, esculturas, grabados y tapices. "
            "Su estilo evolucionó desde el fauvismo inicial hacia un lenguaje abstracto que influyó en el expresionismo abstracto estadounidense; artistas como Jackson Pollock reconocieron su impacto. "
            "El mosaico de Miró en el pavimento de las Ramblas, el mural «El vol de l'alosa» en el aeropuerto de Barcelona, y esculturas repartidas por la ciudad forman parte del día a día urbano, no solo de visitas de museo. "
            "Para estudiantes de español, conocer a Miró abre vocabulario de arte contemporáneo (surrealismo, abstracción, grabado, tapiz) y permite conversaciones sobre identidad catalana, exilio durante la Guerra Civil, y cómo el arte puede ser político sin ser literal."
        ),
        "summary_en": (
            "Joan Miró i Ferrà (1893–1983) was born in Barcelona and became one of the most influential artists of the 20th century, recognized for his surrealist works with organic forms, primary colors, and symbols mixing the dreamlike with references to the Catalan land. "
            "Unlike Picasso, Miró kept a deep commitment to Barcelona and Mallorca throughout his life, where he spent his final years; the Fundació Joan Miró, opened on Montjuïc in 1975, displays over ten thousand works including paintings, sculptures, prints, and tapestries. "
            "His style evolved from early Fauvism toward an abstract language that influenced American Abstract Expressionism; artists like Jackson Pollock acknowledged his impact. "
            "Miró's mosaic on the pavement of Las Ramblas, the mural «El vol de l'alosa» at Barcelona airport, and sculptures scattered around the city are part of daily urban life, not only museum visits. "
            "For Spanish students, knowing Miró opens contemporary art vocabulary (surrealism, abstraction, print, tapestry) and allows conversations about Catalan identity, exile during the Civil War, and how art can be political without being literal."
        ),
    },
    {
        "key": "medieval_barcelona",
        "title_es": "Las Ramblas y la Barcelona Medieval",
        "intro_es": "Casco antiguo, Barrio Gótico y el corazón histórico de la ciudad.",
        "wiki_url": "https://en.wikipedia.org/wiki/Gothic_Quarter,_Barcelona",
        "summary_es": (
            "El Barrio Gótico (Barri Gòtic) conserva el trazado medieval de Barcelona, con callejones estrechos, plazas ocultas y restos romanos (murallas, columnas del templo de Augusto) que muestran la continuidad histórica desde Barcino, la colonia romana fundada en el siglo I a.C. "
            "Las Ramblas, el paseo más famoso de la ciudad, eran originalmente un torrente (rambla en árabe significa «lecho de río seco») que marcaba el límite de la ciudad amurallada; a lo largo de los siglos se convirtió en eje comercial, social y turístico, flanqueado por el mercado de la Boquería, el Gran Teatre del Liceu y edificios modernistas. "
            "La catedral gótica de Barcelona, la basílica de Santa Maria del Mar (escenario de la novela «La catedral del mar» de Ildefonso Falcones), y el Palau de la Generalitat son ejemplos de arquitectura gótica catalana que combinan función religiosa, comercial y política. "
            "Caminar por el Born, el Call (antiguo barrio judío) o la plaza del Rei es recorrer siglos de historia en pocos metros; las placas bilingües en catalán y español, los nombres de calles (carrer, plaça) y el contraste con el Eixample modernista enseñan urbanismo y lengua al mismo tiempo. "
            "Para estudiantes, este barrio es aula al aire libre: practicar direcciones, describir edificios, pedir en terrazas y leer carteles históricos conecta vocabulario de clase con la experiencia diaria de vivir en Barcelona."
        ),
        "summary_en": (
            "The Gothic Quarter (Barri Gòtic) preserves Barcelona's medieval layout, with narrow alleys, hidden plazas, and Roman remains (walls, columns of the Temple of Augustus) showing historical continuity from Barcino, the Roman colony founded in the 1st century BC. "
            "Las Ramblas, the city's most famous promenade, was originally a stream (rambla in Arabic means «dry riverbed») marking the boundary of the walled city; over centuries it became a commercial, social, and tourist axis, flanked by the Boquería market, the Gran Teatre del Liceu, and modernist buildings. "
            "Barcelona's Gothic cathedral, the basilica of Santa Maria del Mar (setting of the novel «Cathedral of the Sea» by Ildefonso Falcones), and the Palau de la Generalitat are examples of Catalan Gothic architecture combining religious, commercial, and political functions. "
            "Walking through El Born, the Call (old Jewish quarter), or Plaça del Rei means crossing centuries of history in a few meters; bilingual plaques in Catalan and Spanish, street names (carrer, plaça), and the contrast with the modernist Eixample teach urbanism and language simultaneously. "
            "For students, this neighborhood is an open-air classroom: practicing directions, describing buildings, ordering at terraces, and reading historical signs connects class vocabulary with the daily experience of living in Barcelona."
        ),
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


def _news_api_request_params() -> dict[str, str | int]:
    """Build NewsAPI query params for Spain-focused Spanish articles."""
    params: dict[str, str | int] = {"pageSize": 12, "apiKey": NEWS_API_KEY}
    if "top-headlines" in NEWS_API_URL:
        params["country"] = "es"
        params["category"] = "general"
    else:
        params["q"] = (
            '(España OR Spain OR Madrid OR Barcelona OR Valencia OR Cataluña) '
            "AND NOT (Mexico OR Argentina OR Chile)"
        )
        params["language"] = "es"
        params["searchIn"] = "title,description"
        params["sortBy"] = "publishedAt"
    return params


def _is_spain_related_article(title: str, description: str) -> bool:
    """Keep articles that clearly mention Spain (filters generic world news)."""
    return bool(SPAIN_NEWS_RE.search(f"{title} {description}"))


def _parse_news_api_articles(
    raw: list[dict[str, Any]], *, spain_only: bool = True
) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for item in raw:
        title = (item.get("title") or "").strip()
        description = (item.get("description") or "").strip()
        if not title or not description:
            continue
        if spain_only and not _is_spain_related_article(title, description):
            continue
        source = item.get("source") or {}
        safe_url = _safe_https_url(item.get("url", ""))
        if not safe_url:
            continue
        articles.append({
            "title": title,
            "description": description,
            "url": safe_url,
            "source": source.get("name", "Desconocido"),
            "publishedAt": item.get("publishedAt", ""),
            "published_display": format_news_date(item.get("publishedAt")),
        })
    return articles


def _news_result(
    articles: list[dict[str, Any]],
    error: str | None,
    fetched_at: str | None,
    *,
    stale_cache: bool = False,
) -> dict[str, Any]:
    cache_ts = fetched_at if stale_cache and fetched_at else None
    display = format_refresh_time(cache_ts) if cache_ts else ""
    section_failed = not articles and bool(error or not fetched_at)
    return {
        "articles": articles,
        "error": error,
        "fetched_at": fetched_at,
        "cache_timestamp": cache_ts,
        "cache_timestamp_display": display,
        "section_failed": section_failed,
    }


def get_spain_news() -> dict[str, Any]:
    try:
        cache = _load_cache()
        cached = cache.get("spain_news")
        if cached and _cache_is_fresh(cached.get("fetched_at"), 3600):
            return _news_result(
                cached.get("articles", []),
                None,
                cached.get("fetched_at"),
            )

        stale_articles = cached.get("articles", []) if cached else []
        stale_at = cached.get("fetched_at") if cached else None

        if not NEWS_API_KEY:
            return _news_result(
                stale_articles,
                "Falta la clave NEWS_API_KEY en el archivo .env.",
                stale_at,
                stale_cache=bool(stale_articles and stale_at),
            )

        try:
            response = requests.get(
                NEWS_API_URL,
                params=_news_api_request_params(),
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "error":
                raise ValueError(data.get("message", "NewsAPI error"))
            raw = data.get("articles") or []
            articles = _parse_news_api_articles(raw)
            if not articles and raw:
                articles = _parse_news_api_articles(raw, spain_only=False)
            now = datetime.now(timezone.utc).isoformat()
            cache["spain_news"] = {"articles": articles, "fetched_at": now}
            _save_cache(cache)
            if not articles:
                return _news_result(
                    [],
                    "No hay artículos disponibles en este momento.",
                    now,
                )
            return _news_result(articles, None, now)
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.exception("get_spain_news failed: %s", exc)
            return _news_result(
                stale_articles,
                "No se pudieron cargar las noticias. Inténtalo más tarde.",
                stale_at,
                stale_cache=bool(stale_articles and stale_at),
            )
    except Exception as exc:
        logger.exception("get_spain_news unexpected failure: %s", exc)
        return _news_result(
            [],
            "No se pudieron cargar las noticias. Inténtalo más tarde.",
            None,
        )


def get_history_topics() -> list[dict[str, Any]]:
    try:
        return [
            {
                "key": t["key"],
                "title_es": t["title_es"],
                "intro_es": t["intro_es"],
                "summary_es": t["summary_es"],
                "summary_en": t["summary_en"],
                "wiki_url": t["wiki_url"],
            }
            for t in HISTORY_TOPICS
        ]
    except Exception as exc:
        logger.exception("get_history_topics failed: %s", exc)
        return []


def get_study_resources() -> list[dict[str, Any]]:
    return [dict(r) for r in STUDY_RESOURCES]
