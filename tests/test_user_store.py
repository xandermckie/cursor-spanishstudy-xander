"""Unit tests for user_store."""

from __future__ import annotations

import json
from unittest.mock import patch

import user_store


def test_should_hash_password_when_registering(app, tmp_path) -> None:
    user_id = user_store.register_user("hash@example.com", "password123")
    assert user_id
    data = user_store.load_user(user_id)
    assert data
    assert data["password_hash"]
    assert data["password_hash"] != "password123"
    assert data["password_hash"].startswith("scrypt:") or data["password_hash"].startswith("pbkdf2:")


def test_should_reject_avatar_when_invalid_bytes(app) -> None:
    user_id = user_store.register_user("avatar@example.com", "password123")
    assert user_id
    result = user_store.save_avatar(user_id, b"not-an-image", "image/png")
    assert result is None


def test_legacy_migration_preserves_global_cache_when_save_fails(
    app, tmp_path, monkeypatch
) -> None:
    legacy_phrasebook = [{"es": "hola", "en": "hello"}]
    legacy_stats = {"xp_total": 50, "level": 2}
    user_store.GLOBAL_CACHE_FILE.write_text(
        json.dumps(
            {
                "phrasebook": legacy_phrasebook,
                "user_stats": legacy_stats,
                "flashcard_deck": [],
            }
        ),
        encoding="utf-8",
    )

    with patch.object(user_store, "save_user", return_value=False):
        user_id = user_store.register_user("legacy@example.com", "password123")

    assert user_id is None
    global_cache = json.loads(user_store.GLOBAL_CACHE_FILE.read_text(encoding="utf-8"))
    assert global_cache.get("phrasebook") == legacy_phrasebook
    assert global_cache.get("user_stats") == legacy_stats


def test_legacy_migration_moves_data_after_successful_register(app) -> None:
    legacy_phrasebook = [{"es": "gracias", "en": "thanks"}]
    legacy_stats = {"xp_total": 120, "level": 3}
    user_store.GLOBAL_CACHE_FILE.write_text(
        json.dumps(
            {
                "phrasebook": legacy_phrasebook,
                "user_stats": legacy_stats,
                "flashcard_deck": [],
            }
        ),
        encoding="utf-8",
    )

    user_id = user_store.register_user("migrated@example.com", "password123")
    assert user_id

    user_data = user_store.load_user(user_id)
    assert user_data
    assert user_data["phrasebook"] == legacy_phrasebook
    assert user_data["user_stats"]["xp_total"] == 120

    global_cache = json.loads(user_store.GLOBAL_CACHE_FILE.read_text(encoding="utf-8"))
    assert "phrasebook" not in global_cache
    assert "user_stats" not in global_cache
