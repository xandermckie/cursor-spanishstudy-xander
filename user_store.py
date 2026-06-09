"""Per-user JSON storage, registration, and avatar uploads."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import InvalidToken
from werkzeug.security import check_password_hash, generate_password_hash

import encryption

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_DIR = DATA_DIR / "users"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_FILE = USERS_DIR / "index.json"
GLOBAL_CACHE_FILE = DATA_DIR / "cache.json"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
MAX_AVATAR_BYTES = 2 * 1024 * 1024

AVATAR_MAGIC: dict[bytes, str] = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",
}

LEGACY_USER_KEYS = ("phrasebook", "weak_words", "user_stats", "vocab_session", "reader_xp_dates")


def normalize_email(email: str) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        return None
    return normalized


def user_id_from_email(email: str) -> str:
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError("invalid email")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


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


def _default_user_data(email: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "email": email,
        "password_hash": "",
        "created_at": now,
        "profile": {"avatar_ext": None},
        "phrasebook": [],
        "weak_words": {},
        "user_stats": _default_user_stats(),
        "vocab_session": None,
        "reader_xp_dates": [],
    }


def _ensure_dirs() -> None:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _user_file(user_id: str) -> Path:
    return USERS_DIR / f"{user_id}.json"


def _load_index() -> dict[str, str]:
    _ensure_dirs()
    if not INDEX_FILE.exists():
        return {}
    
    try:
        file_bytes = INDEX_FILE.read_bytes()
        
        try:
            data = encryption.decrypt_json(file_bytes)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (InvalidToken, ValueError):
            try:
                file_text = file_bytes.decode("utf-8")
                data = json.loads(file_text)
                if isinstance(data, dict):
                    logger.info("Migrating plaintext index file to encrypted format")
                    index_dict = {str(k): str(v) for k, v in data.items()}
                    if _save_index(index_dict):
                        logger.info("Successfully migrated index to encrypted format")
                    return index_dict
            except (json.JSONDecodeError, UnicodeDecodeError) as decode_exc:
                logger.error("Failed to decrypt or parse index: %s", decode_exc)
                return {}
    except OSError as exc:
        logger.error("Failed to read user index: %s", exc)
    
    return {}


def _save_index(index: dict[str, str]) -> bool:
    _ensure_dirs()
    tmp = INDEX_FILE.with_suffix(".json.tmp")
    try:
        encrypted_data = encryption.encrypt_json(index)
        tmp.write_bytes(encrypted_data)
        tmp.replace(INDEX_FILE)
        return True
    except (OSError, ValueError) as exc:
        logger.error("Failed to write user index: %s", exc)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False


def get_user_by_email(email: str) -> str | None:
    normalized = normalize_email(email)
    if not normalized:
        return None
    return _load_index().get(normalized)


def load_user(user_id: str) -> dict[str, Any] | None:
    path = _user_file(user_id)
    if not path.exists():
        return None
    
    try:
        file_bytes = path.read_bytes()
        
        try:
            data = encryption.decrypt_json(file_bytes)
            if isinstance(data, dict):
                return data
        except (InvalidToken, ValueError):
            try:
                file_text = file_bytes.decode("utf-8")
                data = json.loads(file_text)
                if isinstance(data, dict):
                    logger.info("Migrating plaintext user file to encrypted: %s", user_id)
                    if save_user(user_id, data):
                        logger.info("Successfully migrated user %s to encrypted format", user_id)
                    return data
            except (json.JSONDecodeError, UnicodeDecodeError) as decode_exc:
                logger.error("Failed to decrypt or parse user %s: %s", user_id, decode_exc)
                return None
    except OSError as exc:
        logger.error("Failed to read user file %s: %s", user_id, exc)
    
    return None


def save_user(user_id: str, data: dict[str, Any]) -> bool:
    _ensure_dirs()
    path = _user_file(user_id)
    tmp = path.with_suffix(".json.tmp")
    try:
        encrypted_data = encryption.encrypt_json(data)
        tmp.write_bytes(encrypted_data)
        tmp.replace(path)
        return True
    except (OSError, ValueError) as exc:
        logger.error("Failed to save user %s: %s", user_id, exc)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False


def _global_cache_has_legacy_user_data() -> bool:
    if not GLOBAL_CACHE_FILE.exists():
        return False
    try:
        with GLOBAL_CACHE_FILE.open(encoding="utf-8") as f:
            global_cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    return any(global_cache.get(key) for key in LEGACY_USER_KEYS)


def _merge_legacy_into_user_data(user_data: dict[str, Any]) -> bool:
    """Copy legacy user keys from global cache into user_data without mutating global cache."""
    index = _load_index()
    if index:
        return False
    if not _global_cache_has_legacy_user_data():
        return False
    if not GLOBAL_CACHE_FILE.exists():
        return False
    try:
        with GLOBAL_CACHE_FILE.open(encoding="utf-8") as f:
            global_cache = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Legacy migration skipped: %s", exc)
        return False

    migrated = False
    for key in LEGACY_USER_KEYS:
        if key in global_cache and global_cache[key]:
            user_data[key] = global_cache[key]
            migrated = True

    if not migrated:
        return False

    user_data.setdefault("phrasebook", [])
    user_data.setdefault("weak_words", {})
    user_data.setdefault("user_stats", _default_user_stats())
    user_data.setdefault("reader_xp_dates", [])
    return True


def _clean_legacy_from_global_cache(user_id: str) -> None:
    """Remove legacy user keys from global cache after user file is saved."""
    if not GLOBAL_CACHE_FILE.exists():
        return
    try:
        with GLOBAL_CACHE_FILE.open(encoding="utf-8") as f:
            global_cache = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Legacy cache cleanup skipped: %s", exc)
        return

    cleaned = False
    for key in LEGACY_USER_KEYS:
        if key in global_cache:
            global_cache.pop(key)
            cleaned = True

    if not cleaned:
        return

    tmp = GLOBAL_CACHE_FILE.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(global_cache, f, ensure_ascii=False, indent=2)
        tmp.replace(GLOBAL_CACHE_FILE)
        logger.info("Migrated legacy user data into user %s", user_id)
    except OSError as exc:
        logger.error("Failed to clean global cache after migration: %s", exc)


def register_user(email: str, password: str) -> str | None:
    normalized = normalize_email(email)
    if not normalized or len(password) < MIN_PASSWORD_LEN:
        return None
    if get_user_by_email(normalized):
        return None

    user_id = user_id_from_email(normalized)
    if _user_file(user_id).exists():
        return None

    user_data = _default_user_data(normalized)
    user_data["password_hash"] = generate_password_hash(password)
    migrated = _merge_legacy_into_user_data(user_data)

    if not save_user(user_id, user_data):
        return None

    if migrated:
        _clean_legacy_from_global_cache(user_id)

    index = _load_index()
    index[normalized] = user_id
    if not _save_index(index):
        try:
            _user_file(user_id).unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Failed to roll back user file after index save failure: %s", exc)
        return None

    return user_id


def authenticate(email: str, password: str) -> str | None:
    normalized = normalize_email(email)
    if not normalized:
        return None
    user_id = get_user_by_email(normalized)
    if not user_id:
        return None
    user_data = load_user(user_id)
    if not user_data:
        return None
    pwd_hash = user_data.get("password_hash", "")
    if not pwd_hash or not check_password_hash(pwd_hash, password):
        return None
    return user_id


def _detect_image_ext(file_bytes: bytes) -> str | None:
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def save_avatar(user_id: str, file_bytes: bytes, content_type: str | None) -> str | None:
    if len(file_bytes) > MAX_AVATAR_BYTES:
        return None

    ext = _detect_image_ext(file_bytes)
    if not ext:
        return None

    allowed_types = {
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    if content_type and content_type.split(";")[0].strip() not in allowed_types.values():
        return None

    user_data = load_user(user_id)
    if not user_data:
        return None

    upload_dir = UPLOADS_DIR / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    for old in upload_dir.glob("avatar.*"):
        try:
            old.unlink()
        except OSError:
            pass

    dest = upload_dir / f"avatar.{ext}"
    try:
        dest.write_bytes(file_bytes)
    except OSError as exc:
        logger.error("Failed to write avatar for %s: %s", user_id, exc)
        return None

    user_data.setdefault("profile", {})
    user_data["profile"]["avatar_ext"] = ext
    if not save_user(user_id, user_data):
        return None
    return ext


def avatar_path(user_id: str) -> Path | None:
    user_data = load_user(user_id)
    if not user_data:
        return None
    ext = (user_data.get("profile") or {}).get("avatar_ext")
    if not ext:
        return None
    path = UPLOADS_DIR / user_id / f"avatar.{ext}"
    if path.is_file():
        return path
    return None


def has_avatar(user_id: str) -> bool:
    return avatar_path(user_id) is not None
