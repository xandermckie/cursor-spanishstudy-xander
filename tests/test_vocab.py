"""Vocab flashcard integration tests."""

from __future__ import annotations

import fetcher
from fetcher_seeds import FLASHCARD_DECK_SEED


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
