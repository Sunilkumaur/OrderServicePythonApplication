"""Unit tests - the CI pipeline runs these before building the Docker image."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


def test_health_endpoints():
    assert client.get("/health/live").json() == {"status": "alive"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_info_has_version_and_hostname():
    body = client.get("/info").json()
    assert {"app", "version", "environment", "hostname"} <= body.keys()


def test_create_and_get_order():
    created = client.post("/orders", json={"item": "laptop", "quantity": 2})
    assert created.status_code == 201
    order_id = created.json()["id"]

    fetched = client.get(f"/orders/{order_id}")
    assert fetched.status_code == 200
    assert fetched.json()["item"] == "laptop"


def test_invalid_order_is_rejected():
    response = client.post("/orders", json={"item": "laptop", "quantity": 0})
    assert response.status_code == 422


def test_missing_order_returns_404():
    assert client.get("/orders/does-not-exist").status_code == 404
