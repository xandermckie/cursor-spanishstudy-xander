"""Global JSON cache I/O for Estudio Abroad."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "cache.json"


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


def _invalidate_global_cache() -> None:
    try:
        from flask import g, has_request_context

        if has_request_context() and hasattr(g, "_estudio_global_cache"):
            delattr(g, "_estudio_global_cache")
    except ImportError:
        pass


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
