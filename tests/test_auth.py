"""Authentication route integration tests."""

from __future__ import annotations


def test_should_register_and_login_when_valid_credentials(
    client, csrf_token, login
) -> None:
    email = "newuser@example.com"
    password = "securepass1"
    register = client.post(
        "/register",
        data={
            "csrf_token": csrf_token,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=False,
    )
    assert register.status_code == 302
    assert "/profile" in register.location

    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
    login(email, password)
    profile = client.get("/profile")
    assert profile.status_code == 200
    assert email.encode() in profile.data


def test_should_reject_duplicate_email_when_registering_twice(
    client, registered_user, csrf_token
) -> None:
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
    client.get("/register")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "email": registered_user["email"],
            "password": "otherpass1",
            "confirm_password": "otherpass1",
        },
    )
    assert response.status_code == 200
    assert b"ya est" in response.data.lower() or b"registrado" in response.data.lower()


def test_should_reject_login_when_wrong_password(client, registered_user) -> None:
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": registered_user["email"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 200
    assert b"incorrectos" in response.data.lower()


def test_should_reject_post_when_csrf_missing(client) -> None:
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 302
    assert "/login" in (response.location or "")
