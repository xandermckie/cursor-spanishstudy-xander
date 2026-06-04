"""Voice page and translation API tests."""

from __future__ import annotations

import json


def _voice_csrf(client) -> str:
    client.get("/voz")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        raise RuntimeError("CSRF token missing from session")
    return token


def test_should_render_voice_page(client) -> None:
    response = client.get("/voz")
    assert response.status_code == 200
    assert b"Voz y traducci" in response.data
    assert b"voice.js" in response.data


def test_should_translate_via_api(client) -> None:
    token = _voice_csrf(client)
    response = client.post(
        "/api/translate",
        json={"text": "Hello world", "source": "en", "target": "es"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["translated"] == "ES:Hello world"
    assert "from_cache" in data


def test_should_reject_empty_translate_text(client) -> None:
    token = _voice_csrf(client)
    response = client.post(
        "/api/translate",
        json={"text": "   ", "source": "en", "target": "es"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_should_reject_oversized_translate_text(client) -> None:
    token = _voice_csrf(client)
    response = client.post(
        "/api/translate",
        json={"text": "x" * 501, "source": "en", "target": "es"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400


def test_should_reject_invalid_lang_pair(client) -> None:
    token = _voice_csrf(client)
    response = client.post(
        "/api/translate",
        json={"text": "hola", "source": "en", "target": "en"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400


def test_should_reject_translate_without_csrf(client) -> None:
    response = client.post(
        "/api/translate",
        json={"text": "Hello", "source": "en", "target": "es"},
    )
    assert response.status_code == 403


def test_should_reject_phrasebook_save_when_anonymous(client) -> None:
    token = _voice_csrf(client)
    response = client.post(
        "/api/phrasebook/save",
        json={"text": "Where is the metro?"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401


def test_should_save_phrase_when_logged_in(
    client, registered_user, login
) -> None:
    login(registered_user["email"], registered_user["password"])
    token = _voice_csrf(client)
    response = client.post(
        "/api/phrasebook/save",
        json={"text": "Where is the metro?"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data.get("ok") is True

    page = client.get("/phrasebook")
    assert b"Where is the metro?" in page.data
