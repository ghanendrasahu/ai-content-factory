"""Job control: retry, cancel, delete and the settings endpoint."""

from fastapi.testclient import TestClient

from app.core.storage import jobs
from app.main import app


def _job(**kwargs):
    from app.models.job import Job

    job = Job(job_id=kwargs.pop("job_id", "job-control-1"), **kwargs)
    jobs[job.job_id] = job
    return job


def test_cancel_marks_the_job_cancelled():
    jobs.clear()
    client = TestClient(app)
    job = _job(status="rendering", progress=42)

    response = client.post(f"/jobs/{job.job_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert jobs[job.job_id].status == "cancelled"


def test_cancel_of_a_finished_job_conflicts():
    jobs.clear()
    client = TestClient(app)
    job = _job(job_id="job-control-2", status="completed")

    assert client.post(f"/jobs/{job.job_id}/cancel").status_code == 409


def test_cancel_unknown_job_returns_404():
    client = TestClient(app)
    assert client.post("/jobs/does-not-exist/cancel").status_code == 404


def test_retry_resets_a_failed_job(monkeypatch):
    jobs.clear()
    client = TestClient(app)
    job = _job(job_id="job-control-3", status="failed", error="boom")
    job.video_url = "https://example.com/video.mp4"

    started = []
    monkeypatch.setattr(
        "app.api.jobs.run_pipeline_background", lambda job_id: started.append(job_id)
    )

    response = client.post(f"/jobs/{job.job_id}/retry")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert jobs[job.job_id].error is None
    assert started == [job.job_id]


def test_retry_of_a_running_job_conflicts():
    jobs.clear()
    client = TestClient(app)
    job = _job(job_id="job-control-4", status="rendering")

    assert client.post(f"/jobs/{job.job_id}/retry").status_code == 409


def test_delete_removes_the_job():
    jobs.clear()
    client = TestClient(app)
    job = _job(job_id="job-control-5")

    response = client.delete(f"/jobs/{job.job_id}")

    assert response.status_code == 200
    assert job.job_id not in jobs


def test_settings_endpoint_exposes_flags_without_secrets():
    client = TestClient(app)

    response = client.get("/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["pipeline"]["engine"] in {"graph", "linear"}
    assert "features" in body and "thumbnails" in body["features"]
    assert "youtube_configured" in body["integrations"]
    # no secret material is ever exposed
    assert "api_key" not in str(body).lower().replace("api_key_required", "")


def test_settings_route_does_not_collide_with_job_lookup():
    client = TestClient(app)

    # /settings must be routed to the settings router, not treated as a job id
    assert client.get("/settings").status_code == 200
