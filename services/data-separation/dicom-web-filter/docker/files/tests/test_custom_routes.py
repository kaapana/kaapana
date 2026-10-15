"""Tests for the dicom-web-filter custom routes that proxy straight to dcm4chee."""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import DICOMWEB_BASE_URL
from app.CUSTOM_RS import routes


def test_patient_routes_are_admin_only(monkeypatch):
    calls = []

    async def fake_request(self, method, url, **kwargs):
        calls.append((method, url))
        return httpx.Response(200, json=[])

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)

    app = FastAPI()

    # Stands in for AuthMiddleware, which sets the same scope key from the token.
    @app.middleware("http")
    async def set_admin(request, call_next):
        request.scope["admin"] = request.headers.get("x-test-admin") == "true"
        return await call_next(request)

    app.include_router(routes.router)
    client = TestClient(app)

    assert client.get("/patients").status_code == 403
    assert calls == []

    response = client.delete(
        "/patients/AB%2F12^^^ISSUER", headers={"x-test-admin": "true"}
    )
    assert response.status_code == 200
    assert calls == [("DELETE", f"{DICOMWEB_BASE_URL}/patients/AB%2F12%5E%5E%5EISSUER")]
