"""Security hardening integration tests."""

from __future__ import annotations

import pytest

from app import create_app


def test_should_set_session_cookie_flags_in_production_config(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key-for-tests-only")
    monkeypatch.setenv("ENCRYPTION_KEY", "Zzpj9pN4UxvhKzx0oW7TDk8YQn5X5vR9LqBvG0TJ_Qs=")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    application = create_app()
    assert application.config["SESSION_COOKIE_HTTPONLY"] is True
    assert application.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert application.config["SESSION_COOKIE_SECURE"] is True


def test_should_reject_travel_post_when_csrf_missing(client) -> None:
    response = client.post(
        "/travel",
        data={"mood": "chill"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/travel" in (response.location or "")


def test_should_accept_travel_post_when_csrf_valid(client, csrf_token) -> None:
    response = client.post(
        "/travel",
        data={"csrf_token": csrf_token, "mood": "chill"},
        follow_redirects=False,
    )
    assert response.status_code == 200


def test_should_include_security_headers_on_html_response(client) -> None:
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers


def test_should_reject_phrasebook_export_when_not_logged_in(client) -> None:
    response = client.get("/phrasebook/export", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in (response.location or "")


def test_should_reject_translate_save_when_not_logged_in(client, csrf_token) -> None:
    response = client.post(
        "/translate/save",
        json={
            "spoken": "hello",
            "translated": "hola",
            "source_lang": "en",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 401


def test_should_reject_vocab_record_when_not_logged_in(client, csrf_token) -> None:
    response = client.post(
        "/vocab/record",
        data={
            "csrf_token": csrf_token,
            "card_index": "0",
            "correct": "1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in (response.location or "")


def test_should_raise_when_secret_key_missing_in_production(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("ENCRYPTION_KEY", "Zzpj9pN4UxvhKzx0oW7TDk8YQn5X5vR9LqBvG0TJ_Qs=")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_should_return_429_when_login_rate_limit_exceeded(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_dir = data_dir / "users"
    cache_file = data_dir / "cache.json"
    cache_file.write_text('{"flashcard_deck": []}', encoding="utf-8")

    monkeypatch.setattr("fetcher.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.CACHE_FILE", cache_file)
    monkeypatch.setattr("user_store.DATA_DIR", data_dir)
    monkeypatch.setattr("user_store.USERS_DIR", users_dir)
    monkeypatch.setattr("user_store.UPLOADS_DIR", data_dir / "uploads")
    monkeypatch.setattr("user_store.INDEX_FILE", users_dir / "index.json")
    monkeypatch.setattr("user_store.GLOBAL_CACHE_FILE", cache_file)
    monkeypatch.setattr("app.DATA_DIR", data_dir)
    monkeypatch.setattr("app.CACHE_FILE", cache_file)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setenv("SECRET_KEY", "rate-limit-test-secret")
    monkeypatch.setenv("ENCRYPTION_KEY", "Zzpj9pN4UxvhKzx0oW7TDk8YQn5X5vR9LqBvG0TJ_Qs=")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    application = create_app()
    application.config["TESTING"] = True
    application.config["RATELIMIT_ENABLED"] = True
    client = application.test_client()

    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]

    for _ in range(10):
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": "nobody@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 200

    blocked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "nobody@example.com",
            "password": "wrongpassword",
        },
    )
    assert blocked.status_code == 429
