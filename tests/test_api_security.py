"""Auth tests: X-API-Key gate on job-spawn routes (off by default)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture()
def keys_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "API_KEYS", ["ci-secret-key"])
    yield
    monkeypatch.setattr(settings, "API_KEYS", [])


def test_auth_off_by_default():
    """Local single-tenant workflow: empty API_KEYS leaves POSTs open."""
    client = TestClient(app)
    response = client.post("/jobs")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_spawn_401_without_key(keys_enabled):
    client = TestClient(app)
    assert client.post("/jobs").status_code == 401
    assert "API key" in client.post("/jobs").json()["detail"]


def test_spawn_401_with_wrong_key(keys_enabled):
    client = TestClient(app)
    response = client.post("/jobs", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_spawn_200_with_valid_key(keys_enabled):
    client = TestClient(app)
    response = client.post("/jobs", headers={"X-API-Key": "ci-secret-key"})
    assert response.status_code == 200
    assert response.json()["job_id"]


def test_reads_stay_open_with_keys(keys_enabled):
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/metrics").status_code == 200
    assert client.get("/api/nothing") .status_code in {404, 405}


def test_download_route_gated(keys_enabled):
    client = TestClient(app)
    response = client.post(
        "/jobs/whatever/download",
        json={"url": "https://youtu.be/x"},
    )
    assert response.status_code == 401


def test_time_safe_compare_unit():
    """Unit: compare gate requires exact match, header value None -> 401."""
    from app.api.deps import require_api_key
    from fastapi import HTTPException

    settings.API_KEYS = ["k1"]
    try:
        assert require_api_key("k1") is None
        with pytest.raises(HTTPException) as exc:
            require_api_key("k2")
        assert exc.value.status_code == 401
        with pytest.raises(HTTPException):
            require_api_key(None)
    finally:
        settings.API_KEYS = []
