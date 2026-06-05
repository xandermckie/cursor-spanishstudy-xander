"""Voice translation page and API tests."""

from __future__ import annotations

import fetcher


def _csrf_from_session(client) -> str:
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        raise RuntimeError("CSRF token missing from session")
    return token


def test_voice_page_renders_desktop(client) -> None:
    response = client.get("/voice")
    assert response.status_code == 200
    assert b"voice-mic-btn" in response.data
    assert b'data-speech-backend="auto"' in response.data
    assert b"voice.js" in response.data
    assert b"voice-lite.js" not in response.data
    assert b"voice-unsupported" in response.data
    assert b"voice-cancel-translate-btn" in response.data
    assert "Traducción por voz".encode() in response.data


def test_voice_page_renders_mobile_lite(client) -> None:
    response = client.get(
        "/voice",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            )
        },
    )
    assert response.status_code == 200
    assert b'data-speech-backend="keyboard"' in response.data
    assert b"voice-lite.js" in response.data
    assert b"voice.js" not in response.data
    assert b"voice-mic-btn" not in response.data
    assert b"voice-keyboard-card" in response.data
    assert "micrófono del teclado".encode() in response.data


def test_voice_translate_returns_504_when_fast_translation_fails(
    client, monkeypatch
) -> None:
    def fail_fast(*_args, **_kwargs):
        return None, False

    monkeypatch.setattr("fetcher.fetch_translation_fast", fail_fast)
    client.get("/voice")
    token = _csrf_from_session(client)
    response = client.post(
        "/voice/translate",
        json={"text": "Hello", "source_lang": "en"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 504
    assert "tardó demasiado" in response.get_json()["error"]


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
