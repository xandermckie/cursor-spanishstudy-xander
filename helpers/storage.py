"""Read/write helpers for JSON data files."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

DATA_DIR = Path(config.DATA_DIR)

VOCAB_FILE = "vocab.json"
PHRASEBOOK_FILE = "phrasebook.json"
READER_PASSAGES_FILE = "reader_passages.json"
TRANSLATIONS_CACHE_FILE = "translations_cache.json"
GLOSBE_CACHE_FILE = "glosbe_cache.json"
DEFINITIONS_CACHE_FILE = "definitions_cache.json"
DAILY_SENTENCE_FILE = "daily_sentence.json"
LINGUA_CACHE_FILE = "lingua_cache.json"

RUNTIME_FILES = {
    TRANSLATIONS_CACHE_FILE: {},
    GLOSBE_CACHE_FILE: {},
    DEFINITIONS_CACHE_FILE: {},
    DAILY_SENTENCE_FILE: {},
    LINGUA_CACHE_FILE: {},
}


def _path(name: str) -> Path:
    return DATA_DIR / name


def load_json(name: str, default: Any) -> Any:
    path = _path(name)
    if not path.exists():
        save_json(name, default)
        return default
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        save_json(name, default)
        return default


def save_json(name: str, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(name)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def ensure_runtime_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, default in RUNTIME_FILES.items():
        if not _path(name).exists():
            save_json(name, default)
    if not _path(PHRASEBOOK_FILE).exists():
        save_json(PHRASEBOOK_FILE, [])
    if not _path(VOCAB_FILE).exists():
        raise FileNotFoundError(
            f"Missing seed file: {_path(VOCAB_FILE)}. "
            "Ensure vocab.json is committed in the repository."
        )
    if not _path(READER_PASSAGES_FILE).exists():
        raise FileNotFoundError(
            f"Missing seed file: {_path(READER_PASSAGES_FILE)}."
        )


def get_vocab() -> list[dict[str, Any]]:
    data = load_json(VOCAB_FILE, [])
    return data if isinstance(data, list) else []


def get_phrasebook() -> list[dict[str, Any]]:
    data = load_json(PHRASEBOOK_FILE, [])
    return data if isinstance(data, list) else []


def get_reader_passages() -> list[dict[str, Any]]:
    data = load_json(READER_PASSAGES_FILE, [])
    return data if isinstance(data, list) else []


def get_translations_cache() -> dict[str, str]:
    data = load_json(TRANSLATIONS_CACHE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_translations_cache(cache: dict[str, str]) -> None:
    save_json(TRANSLATIONS_CACHE_FILE, cache)


def get_glosbe_cache() -> dict[str, list[dict[str, str]]]:
    data = load_json(GLOSBE_CACHE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_glosbe_cache(cache: dict[str, list[dict[str, str]]]) -> None:
    save_json(GLOSBE_CACHE_FILE, cache)


def get_definitions_cache() -> dict[str, str]:
    data = load_json(DEFINITIONS_CACHE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_definitions_cache(cache: dict[str, str]) -> None:
    save_json(DEFINITIONS_CACHE_FILE, cache)


def get_daily_sentence() -> dict[str, Any]:
    data = load_json(DAILY_SENTENCE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_daily_sentence(sentence: dict[str, Any]) -> None:
    save_json(DAILY_SENTENCE_FILE, sentence)


def add_phrase(es: str, ca: str, en: str, category: str) -> dict[str, Any]:
    phrasebook = get_phrasebook()
    entry = {
        "id": str(uuid.uuid4()),
        "es": es.strip(),
        "ca": ca.strip(),
        "en": en.strip(),
        "category": category.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    phrasebook.append(entry)
    save_json(PHRASEBOOK_FILE, phrasebook)
    return entry


def export_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "id", "category", "es", "ca", "en", "notes", "created_at"])
    for item in get_vocab():
        writer.writerow(
            [
                "vocab",
                item.get("id", ""),
                item.get("category", ""),
                item.get("es", ""),
                item.get("ca", ""),
                item.get("en", ""),
                item.get("notes", ""),
                "",
            ]
        )
    for item in get_phrasebook():
        writer.writerow(
            [
                "phrasebook",
                item.get("id", ""),
                item.get("category", ""),
                item.get("es", ""),
                item.get("ca", ""),
                item.get("en", ""),
                "",
                item.get("created_at", ""),
            ]
        )
    return output.getvalue()


def category_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in get_vocab():
        cat = item.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def weak_area_category() -> str | None:
    """Category with fewest Glosbe cache hits among vocab phrases."""
    cache = get_glosbe_cache()
    categories = ["transit", "food", "places", "phrases", "emergencies"]
    hits: dict[str, int] = {c: 0 for c in categories}
    vocab = get_vocab()
    for item in vocab:
        cat = item.get("category", "")
        if cat not in hits:
            continue
        phrase = item.get("es", "")
        cache_key = f"es:{phrase}"
        cached = cache.get(cache_key) or cache.get(phrase)
        if cached:
            hits[cat] += 1
    if not hits:
        return categories[0] if categories else None
    return min(hits, key=hits.get)
