"""Vocab flashcard integration tests."""

from __future__ import annotations

import json

import pytest

import fetcher
import user_store
from fetcher_seeds import FLASHCARD_DECK_SEED


@pytest.fixture
def vocab_unit_env(tmp_path, monkeypatch):
    """Isolated data dirs for direct fetcher vocab function tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_dir = data_dir / "users"
    cache_file = data_dir / "cache.json"
    cache_file.write_text(
        json.dumps({"flashcard_deck": list(FLASHCARD_DECK_SEED)}),
        encoding="utf-8",
    )

    monkeypatch.setattr("fetcher.cache.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.cache.CACHE_FILE", cache_file)
    monkeypatch.setattr("fetcher.cache.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.cache.CACHE_FILE", cache_file)
    monkeypatch.setattr(fetcher, "DATA_DIR", data_dir)
    monkeypatch.setattr(fetcher, "CACHE_FILE", cache_file)
    monkeypatch.setattr(user_store, "DATA_DIR", data_dir)
    monkeypatch.setattr(user_store, "USERS_DIR", users_dir)
    monkeypatch.setattr(user_store, "UPLOADS_DIR", data_dir / "uploads")
    monkeypatch.setattr(user_store, "INDEX_FILE", users_dir / "index.json")
    monkeypatch.setattr(user_store, "GLOBAL_CACHE_FILE", cache_file)

    user_id = user_store.register_user("vocab-unit@example.com", "password123")
    assert user_id
    fetcher.reset_vocab_session(user_id)
    return user_id


def test_should_reject_record_when_not_logged_in(client, csrf_token) -> None:
    response = client.post(
        "/vocab/record",
        data={
            "csrf_token": csrf_token,
            "es": "hola",
            "en": "hello",
            "current_i": "0",
            "missed": "0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.location


def test_should_reject_record_when_card_mismatch(client, registered_user, login) -> None:
    login(registered_user["email"], registered_user["password"])
    client.get("/vocab")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    response = client.post(
        "/vocab/record",
        data={
            "csrf_token": token,
            "es": "fake",
            "en": "card",
            "current_i": "0",
            "missed": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"No se pudo guardar" in response.data


def test_should_not_complete_deck_when_index_skipped(
    client, registered_user, login
) -> None:
    login(registered_user["email"], registered_user["password"])
    user_id = None
    with client.session_transaction() as sess:
        user_id = sess.get("user_id")
    assert user_id

    last = FLASHCARD_DECK_SEED[-1]
    last_idx = len(FLASHCARD_DECK_SEED) - 1
    skipped = fetcher.record_flashcard_result(
        user_id, last["es"], last["en"], False, last_idx
    )
    assert skipped is False

    session = fetcher.get_vocab_session(user_id)
    assert session.get("complete") is not True
    assert session.get("index") == 0

    client.get("/vocab")
    first = fetcher.get_vocab_session(user_id)["card"]
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post(
        "/vocab/record",
        data={
            "csrf_token": token,
            "es": first["es"],
            "en": first["en"],
            "current_i": "0",
            "missed": "0",
        },
        follow_redirects=True,
    )
    session = fetcher.get_vocab_session(user_id)
    assert session.get("index") == 1
    assert session.get("complete") is not True


def test_should_record_shuffled_card_at_session_index(
    registered_user, login, client
) -> None:
    """Session index 0 maps to deck[shuffled_order[0]], not deck[0]."""
    login(registered_user["email"], registered_user["password"])
    with client.session_transaction() as sess:
        user_id = sess.get("user_id")
    assert user_id

    deck = fetcher._ensure_flashcard_deck(fetcher._load_cache())
    total = len(deck)
    cache = fetcher._load_user_cache(user_id)
    session = fetcher._ensure_vocab_session(cache)
    session["shuffled_order"] = [total - 1] + [
        i for i in range(total) if i != total - 1
    ]
    fetcher._save_user_cache(user_id, cache)

    card = deck[total - 1]
    assert fetcher.record_flashcard_result(
        user_id, card["es"], card["en"], False, 0
    )

    session = fetcher.get_vocab_session(user_id)
    assert session.get("index") == 1


def test_record_flashcard_increments_correct_count_and_xp(vocab_unit_env) -> None:
    user_id = vocab_unit_env
    card = fetcher.get_vocab_session(user_id)["card"]

    assert fetcher.record_flashcard_result(
        user_id, card["es"], card["en"], False, 0
    )

    cache = fetcher._load_user_cache(user_id)
    session = cache["vocab_session"]
    assert session["correct_count"] == 1
    assert session["expected_index"] == 1
    assert cache["user_stats"]["xp_total"] == 10
    assert cache["user_stats"]["total_correct"] == 1


def test_record_flashcard_rejects_wrong_card_content(vocab_unit_env) -> None:
    user_id = vocab_unit_env
    cache_before = fetcher._load_user_cache(user_id)
    xp_before = cache_before["user_stats"]["xp_total"]

    assert fetcher.record_flashcard_result(
        user_id, "fake", "card", False, 0
    ) is False

    cache_after = fetcher._load_user_cache(user_id)
    assert cache_after["vocab_session"]["correct_count"] == 0
    assert cache_after["user_stats"]["xp_total"] == xp_before


def test_record_flashcard_rejects_duplicate_index(vocab_unit_env) -> None:
    user_id = vocab_unit_env
    card = fetcher.get_vocab_session(user_id)["card"]

    assert fetcher.record_flashcard_result(
        user_id, card["es"], card["en"], False, 0
    )
    assert fetcher.record_flashcard_result(
        user_id, card["es"], card["en"], False, 0
    ) is False


def test_reset_vocab_session_clears_progress(vocab_unit_env) -> None:
    user_id = vocab_unit_env
    card = fetcher.get_vocab_session(user_id)["card"]
    fetcher.record_flashcard_result(user_id, card["es"], card["en"], False, 0)

    fetcher.reset_vocab_session(user_id)

    cache = fetcher._load_user_cache(user_id)
    session = cache["vocab_session"]
    assert session["correct_count"] == 0
    assert session["expected_index"] == 0
    assert session["complete"] is False
    assert session["visited_indices"] == []
