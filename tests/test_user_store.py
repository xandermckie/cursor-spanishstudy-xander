"""Unit tests for user_store."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import user_store

MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


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


def test_should_preserve_avatar_when_write_fails(app) -> None:
    user_id = user_store.register_user("writefail@example.com", "password123")
    assert user_id

    first = user_store.save_avatar(user_id, MINIMAL_PNG, "image/png")
    assert first == "png"
    assert user_store.has_avatar(user_id)

    original_path = user_store.avatar_path(user_id)
    assert original_path is not None
    original_bytes = original_path.read_bytes()

    original_write_bytes = Path.write_bytes

    def failing_write_bytes(self: Path, data: bytes) -> int:
        if self.name.startswith("avatar.") and self.name.endswith(".tmp"):
            raise OSError("simulated write failure")
        return original_write_bytes(self, data)

    with patch.object(Path, "write_bytes", failing_write_bytes):
        result = user_store.save_avatar(user_id, MINIMAL_PNG + b"alt", "image/png")

    assert result is None
    assert user_store.has_avatar(user_id)
    assert original_path.read_bytes() == original_bytes


def test_should_allow_only_one_concurrent_registration_per_email(app) -> None:
    barrier = threading.Barrier(2)
    results: list[tuple[str, str | None]] = []
    passwords = ["password111", "password222"]

    def register(password: str) -> None:
        barrier.wait()
        user_id = user_store.register_user("race@example.com", password)
        results.append((password, user_id))

    threads = [
        threading.Thread(target=register, args=(passwords[0],)),
        threading.Thread(target=register, args=(passwords[1],)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    winners = [(password, user_id) for password, user_id in results if user_id]
    losers = [(password, user_id) for password, user_id in results if user_id is None]
    assert len(winners) == 1
    assert len(losers) == 1

    winning_password, winner_id = winners[0]
    losing_password, _ = losers[0]
    assert user_store.get_user_by_email("race@example.com") == winner_id
    assert user_store._user_file(winner_id).exists()
    assert user_store.authenticate("race@example.com", winning_password) == winner_id
    assert user_store.authenticate("race@example.com", losing_password) is None


def test_should_rollback_new_user_when_index_save_fails(app) -> None:
    first_id = user_store.register_user("first@example.com", "password123")
    assert first_id
    assert user_store.load_user(first_id)

    with patch.object(user_store, "_save_index", return_value=False):
        second_id = user_store.register_user("second@example.com", "password456")

    assert second_id is None
    assert user_store.get_user_by_email("second@example.com") is None
    assert not user_store._user_file(
        user_store.user_id_from_email("second@example.com")
    ).exists()
    assert user_store.load_user(first_id)
    assert user_store.get_user_by_email("first@example.com") == first_id


def test_should_preserve_both_emails_when_registering_different_addresses(app) -> None:
    alice_id = user_store.register_user("alice@example.com", "password123")
    bob_id = user_store.register_user("bob@example.com", "password456")
    assert alice_id
    assert bob_id

    index = user_store._load_index()
    assert index["alice@example.com"] == alice_id
    assert index["bob@example.com"] == bob_id


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
