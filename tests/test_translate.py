"""Translate page and API tests."""

from __future__ import annotations


def _csrf_from_session(client) -> str:
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        raise RuntimeError("CSRF token missing from session")
    return token


def test_translate_page_renders(client) -> None:
    response = client.get("/translate")
    assert response.status_code == 200
    assert b"translate-app" in response.data
    assert "Traductor".encode() in response.data


def test_translate_api_en_to_es(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/api",
        json={
            "text": "Where is the metro?",
            "source_lang": "en",
            "target_lang": "es",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["source"] == "Where is the metro?"
    assert data["translated"].startswith("ES:")
    assert data["source_lang"] == "en"
    assert data["target_lang"] == "es"


def test_translate_api_es_to_ca(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/api",
        json={
            "text": "¿Dónde está el metro?",
            "source_lang": "es",
            "target_lang": "ca",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["source_lang"] == "es"
    assert data["target_lang"] == "ca"
    assert data["translated"].startswith("ES:")


def test_translate_api_rejects_same_lang(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/api",
        json={"text": "Hello", "source_lang": "en", "target_lang": "en"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "distintos" in response.get_json()["error"]


def test_translate_api_rejects_invalid_lang(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/api",
        json={"text": "Hello", "source_lang": "en", "target_lang": "fr"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "destino" in response.get_json()["error"]


def test_translate_api_rejects_oversized_text(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/api",
        json={
            "text": "x" * 501,
            "source_lang": "en",
            "target_lang": "es",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert "demasiado larga" in response.get_json()["error"]


def test_translate_save_requires_login(client) -> None:
    client.get("/translate")
    token = _csrf_from_session(client)
    response = client.post(
        "/translate/save",
        json={
            "spoken": "Hello",
            "translated": "Hola",
            "source_lang": "en",
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 401
