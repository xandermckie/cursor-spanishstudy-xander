"""Voice translation page and API tests."""

from __future__ import annotations

import fetcher


def _csrf_from_session(client) -> str:
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        raise RuntimeError("CSRF token missing from session")
    return token


def test_voice_page_renders(client) -> None:
    response = client.get("/voice")
    assert response.status_code == 200
    assert b"voice-mic-btn" in response.data
    assert "Traducción por voz".encode() in response.data


def test_voice_translate_en_to_es(client) -> None:
    client.get("/voice")
    token = _csrf_from_session(client)
    response = client.post(
        "/voice/translate",
        json={"text": "Where is the metro?", "source_lang": "en"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["spoken"] == "Where is the metro?"
    assert data["translated"].startswith("ES:")
    assert data["source_lang"] == "en"
    assert data["target_lang"] == "es"


def test_voice_translate_es_to_en(client) -> None:
    client.get("/voice")
    token = _csrf_from_session(client)
    response = client.post(
        "/voice/translate",
        json={"text": "¿Dónde está el metro?", "source_lang": "es"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["source_lang"] == "es"
    assert data["target_lang"] == "en"
    assert data["translated"].startswith("ES:")


def test_voice_translate_rejects_oversized_text(client) -> None:
    client.get("/voice")
    token = _csrf_from_session(client)
    response = client.post(
        "/voice/translate",
        json={"text": "x" * 501, "source_lang": "en"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "demasiado larga" in response.get_json()["error"]


def test_voice_save_requires_login(client) -> None:
    client.get("/voice")
    token = _csrf_from_session(client)
    response = client.post(
        "/voice/save",
        json={
            "spoken": "Hello",
            "translated": "Hola",
            "source_lang": "en",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401


def test_voice_save_persists_bidirectional(client, registered_user, login) -> None:
    login(registered_user["email"], registered_user["password"])
    client.get("/voice")
    token = _csrf_from_session(client)

    response = client.post(
        "/voice/save",
        json={
            "spoken": "¿Dónde está la playa?",
            "translated": "Where is the beach?",
            "source_lang": "es",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["phrase_id"]

    with client.session_transaction() as sess:
        user_id = sess.get("user_id")
    assert user_id

    cache = fetcher._load_user_cache(user_id)
    phrases = cache["phrasebook"]
    assert len(phrases) == 1
    assert phrases[0]["es"] == "¿Dónde está la playa?"
    assert phrases[0]["input"] == "Where is the beach?"
