"""Pytest fixtures for Estudio Abroad integration tests."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest


def pytest_configure(config) -> None:
    """Set env vars before app is imported during test collection."""
    os.environ.setdefault("FLASK_DEBUG", "1")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
    os.environ.setdefault(
        "ENCRYPTION_KEY", "Zzpj9pN4UxvhKzx0oW7TDk8YQn5X5vR9LqBvG0TJ_Qs="
    )
    os.environ.setdefault("SCHEDULER_ENABLED", "false")


def _csrf_from_session(client) -> str:
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    if not token:
        raise RuntimeError("CSRF token missing from session")
    return token


@pytest.fixture
def app(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_dir = data_dir / "users"
    uploads_dir = data_dir / "uploads"
    cache_file = data_dir / "cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "flashcard_deck": [
                    {"es": "hola", "en": "hello"},
                    {"es": "adiós", "en": "goodbye"},
                    {"es": "gracias", "en": "thank you"},
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("fetcher.DATA_DIR", data_dir)
    monkeypatch.setattr("fetcher.CACHE_FILE", cache_file)
    monkeypatch.setattr("user_store.DATA_DIR", data_dir)
    monkeypatch.setattr("user_store.USERS_DIR", users_dir)
    monkeypatch.setattr("user_store.UPLOADS_DIR", uploads_dir)
    monkeypatch.setattr("user_store.INDEX_FILE", users_dir / "index.json")
    monkeypatch.setattr("user_store.GLOBAL_CACHE_FILE", cache_file)
    monkeypatch.setattr("app.DATA_DIR", data_dir)
    monkeypatch.setattr("app.CACHE_FILE", cache_file)

    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest")
    monkeypatch.setenv("ENCRYPTION_KEY", "Zzpj9pN4UxvhKzx0oW7TDk8YQn5X5vR9LqBvG0TJ_Qs=")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    def fake_translation(
        text: str, src: str, tgt: str, use_cache: bool = True
    ) -> tuple[str, bool]:
        return f"ES:{text}", False

    monkeypatch.setattr("fetcher.fetch_translation", fake_translation)
    monkeypatch.setattr("fetcher.fetch_translation_fast", fake_translation)

    from app import create_app

    application = create_app()
    application.config["TESTING"] = True
    application.config["RATELIMIT_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_token(client):
    client.get("/login")
    return _csrf_from_session(client)


@pytest.fixture
def login(client):
    def _login(email: str, password: str) -> None:
        client.get("/login")
        with client.session_transaction() as sess:
            token = sess["csrf_token"]
        client.post(
            "/login",
            data={"csrf_token": token, "email": email, "password": password},
            follow_redirects=True,
        )

    return _login


@pytest.fixture
def registered_user(client, csrf_token) -> dict[str, str]:
    email = "student@example.com"
    password = "password123"
    response = client.post(
        "/register",
        data={
            "csrf_token": csrf_token,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    return {"email": email, "password": password}
