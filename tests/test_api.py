from fastapi.testclient import TestClient

from app.core.storage import jobs
from app.main import app


def test_health_and_ready():
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_create_and_get_job():
    jobs.clear()
    client = TestClient(app)

    created = client.post("/jobs").json()
    response = client.get(f"/jobs/{created['job_id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_missing_job_returns_404():
    client = TestClient(app)

    response = client.get("/jobs/missing")

    assert response.status_code == 404
