"""Authenticated saved-route API coverage."""

from __future__ import annotations

from app.auth.dependencies import get_current_active_user
from app.main import app
from app.models.entities import User


def _authenticated_client(client, user: User):
    app.dependency_overrides[get_current_active_user] = lambda: user
    return client


def test_saved_route_api_crud_and_validation(client, db_session) -> None:
    user = User(email="dashboard.routes@trafficsms.local")
    db_session.add(user)
    db_session.commit()
    authenticated = _authenticated_client(client, user)

    created = authenticated.post("/users/me/routes", json={
        "name": "Client office", "origin_text": "Corona", "destination_text": "Irvine",
    })
    assert created.status_code == 201
    route = created.json()
    assert route["normalized_name"] == "CLIENT OFFICE"

    listed = authenticated.get("/users/me/routes")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["routes"]] == [route["id"]]

    updated = authenticated.patch(f"/users/me/routes/{route['id']}", json={"destination_text": "LAX"})
    assert updated.status_code == 200
    assert updated.json()["destination_text"] == "LAX"

    duplicate = authenticated.post("/users/me/routes", json={
        "name": "CLIENT OFFICE", "origin_text": "Home", "destination_text": "LAX",
    })
    assert duplicate.status_code == 409
    assert authenticated.post("/users/me/routes", json={"name": "", "origin_text": "", "destination_text": ""}).status_code == 422

    deleted = authenticated.delete(f"/users/me/routes/{route['id']}")
    assert deleted.status_code == 204


def test_saved_route_api_enforces_authentication_and_ownership(client, db_session) -> None:
    owner = User(email="route.owner@trafficsms.local")
    other = User(email="route.other@trafficsms.local")
    db_session.add_all([owner, other])
    db_session.commit()

    assert client.get("/users/me/routes").status_code == 403
    authenticated_owner = _authenticated_client(client, owner)
    route = authenticated_owner.post("/users/me/routes", json={
        "name": "Church", "origin_text": "Home", "destination_text": "Church",
    }).json()
    app.dependency_overrides[get_current_active_user] = lambda: other
    assert client.get(f"/users/me/routes/{route['id']}").status_code == 404
    assert client.patch(f"/users/me/routes/{route['id']}", json={"name": "Other"}).status_code == 404
    assert client.delete(f"/users/me/routes/{route['id']}").status_code == 404
