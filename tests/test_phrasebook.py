"""Phrasebook persistence integration tests."""

from __future__ import annotations


def test_should_persist_phrase_when_logged_in(client, registered_user, login) -> None:
    login(registered_user["email"], registered_user["password"])
    client.get("/phrasebook")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    add = client.post(
        "/phrasebook",
        data={"csrf_token": token, "input": "Where is the metro?"},
        follow_redirects=True,
    )
    assert add.status_code == 200
    assert b"ES:Where is the metro?" in add.data

    client.get("/phrasebook")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
    login(registered_user["email"], registered_user["password"])
    page = client.get("/phrasebook")
    assert b"Where is the metro?" in page.data


def test_should_return_empty_phrasebook_when_anonymous(client) -> None:
    response = client.get("/phrasebook")
    assert response.status_code == 200
    assert b"Where is the metro?" not in response.data
