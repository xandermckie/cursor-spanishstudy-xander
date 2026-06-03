"""Unit tests for user_store."""

from __future__ import annotations

import json

import user_store


def test_should_hash_password_when_registering(app, tmp_path) -> None:
    user_id = user_store.register_user("hash@example.com", "password123")
    assert user_id
    path = user_store.USERS_DIR / f"{user_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["password_hash"]
    assert data["password_hash"] != "password123"
    assert data["password_hash"].startswith("scrypt:") or data["password_hash"].startswith("pbkdf2:")


def test_should_reject_avatar_when_invalid_bytes(app) -> None:
    user_id = user_store.register_user("avatar@example.com", "password123")
    assert user_id
    result = user_store.save_avatar(user_id, b"not-an-image", "image/png")
    assert result is None
