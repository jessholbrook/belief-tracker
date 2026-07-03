import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.beliefs as beliefs_module
from app import db
from app.config import settings
from app.main import app


@pytest.fixture
def client(test_db):
    with TestClient(app) as c:
        yield c


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_conversation_crud(client):
    created = client.post("/api/conversations", json={"title": "t"}).json()
    assert created["title"] == "t"

    listed = client.get("/api/conversations").json()
    assert [c["id"] for c in listed] == [created["id"]]

    fetched = client.get(f"/api/conversations/{created['id']}").json()
    assert fetched["messages"] == []

    assert client.get("/api/conversations/nope").status_code == 404

    client.delete(f"/api/conversations/{created['id']}")
    assert client.get("/api/conversations").json() == []


def test_extract_rejects_unknown_parent(client):
    res = client.post(
        "/api/beliefs/extract", json={"text": "x", "parent_belief": "bel_nope"}
    )
    assert res.status_code == 404


def test_extract_with_valid_parent(client, monkeypatch):
    async def fake_extract(text, parent_id=None):
        return [
            db.insert_belief(statement="s", confidence="high", parent_id=parent_id)
        ]

    monkeypatch.setattr(beliefs_module, "extract_beliefs", fake_extract)
    parent = db.insert_belief(statement="root", confidence="medium")

    res = client.post(
        "/api/beliefs/extract", json={"text": "x", "parent_belief": parent["id"]}
    )
    assert res.status_code == 200
    assert res.json()[0]["parent_id"] == parent["id"]

    tree = client.get("/api/beliefs").json()
    assert len(tree) == 1
    assert len(tree[0]["children"]) == 1


def test_auth_disabled_by_default(client):
    assert client.get("/api/conversations").status_code == 200


def test_auth_required_when_token_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_token", "sekret")

    assert client.get("/api/conversations").status_code == 401
    assert (
        client.get(
            "/api/conversations", headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/conversations", headers={"Authorization": "Bearer sekret"}
        ).status_code
        == 200
    )
    # Health stays open for load balancers / uptime checks.
    assert client.get("/api/health").status_code == 200


def test_ws_rejects_bad_origin(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/ws/chat/x", headers={"origin": "https://evil.example"}
        ):
            pass


def test_ws_allows_configured_origin(client):
    with client.websocket_connect(
        "/ws/chat/nope", headers={"origin": "http://localhost:5173"}
    ) as ws:
        # Unknown conversation → error event (proves the handshake succeeded).
        assert ws.receive_json()["type"] == "error"


def test_ws_requires_token_when_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_auth_token", "sekret")

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/chat/nope"):
            pass

    with client.websocket_connect("/ws/chat/nope?token=sekret") as ws:
        assert ws.receive_json()["type"] == "error"
