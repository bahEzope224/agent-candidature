import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.main import app


def _register_test_routes() -> None:
    if any(route.path == "/__test-http-exception" for route in app.routes):
        return

    @app.get("/__test-http-exception")
    async def _raise_http_exception():
        raise HTTPException(status_code=400, detail="détails simulés")

    @app.get("/__test-unhandled")
    async def _raise_unhandled_exception():
        raise RuntimeError("erreur inattendue")


_register_test_routes()


@pytest.fixture(autouse=True)
def _stub_write_log(monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.main.write_log", _noop)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_http_exception_handler_returns_payload(client: TestClient):
    response = client.get("/__test-http-exception")
    assert response.status_code == 400
    payload = response.json()
    assert "détails simulés" in payload["error"]
    assert payload["location"]["path"] == "/__test-http-exception"
    assert payload["location"]["method"] == "GET"


def test_global_exception_handler_returns_payload(client: TestClient):
    response = client.get("/__test-unhandled")
    assert response.status_code == 500
    payload = response.json()
    assert "erreur inattendue" in payload["error"]
    assert payload["location"]["path"] == "/__test-unhandled"
    assert payload["location"]["method"] == "GET"
