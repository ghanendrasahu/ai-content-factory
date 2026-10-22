"""Runner: engine selection and graceful fallback."""

import pytest

from app.agents import runner
from app.config import settings
from app.models.job import Job


def test_graph_available_reflects_the_dependency():
    # langgraph is a declared dependency, so it must be importable.
    assert runner.graph_available() is True


def test_runner_uses_the_linear_pipeline_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "PIPELINE_ENGINE", "linear")
    called = {"linear": False}

    def fake_pipeline_run(job):
        called["linear"] = True
        job.set_state("completed", 100)
        return job

    monkeypatch.setattr(runner.Pipeline, "run", staticmethod(fake_pipeline_run))

    job = runner.run_job(Job(job_id="j-linear"))

    assert called["linear"] is True
    assert job.status == "completed"


def test_runner_falls_back_to_linear_when_langgraph_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "PIPELINE_ENGINE", "graph")
    monkeypatch.setattr(runner, "graph_available", lambda: False)
    called = {"linear": False}

    def fake_pipeline_run(job):
        called["linear"] = True
        job.set_state("completed", 100)
        return job

    monkeypatch.setattr(runner.Pipeline, "run", staticmethod(fake_pipeline_run))

    runner.run_job(Job(job_id="j-fallback"))

    assert called["linear"] is True


def test_runner_prefers_the_graph_when_available(monkeypatch):
    monkeypatch.setattr(settings, "PIPELINE_ENGINE", "graph")
    monkeypatch.setattr(runner, "graph_available", lambda: True)
    called = {"graph": False, "linear": False}

    def fake_graph_run(job):
        called["graph"] = True
        job.set_state("completed", 100)
        return job

    monkeypatch.setattr(runner, "run_with_graph", fake_graph_run)
    monkeypatch.setattr(
        runner.Pipeline,
        "run",
        staticmethod(lambda job: called.update(linear=True) or job),
    )

    runner.run_job(Job(job_id="j-graph"))

    assert called["graph"] is True
    assert called["linear"] is False


def test_run_with_graph_marks_the_job_failed(monkeypatch):
    def exploding_build():
        raise RuntimeError("no graph for you")

    monkeypatch.setattr("app.agents.graph.build_graph", exploding_build)

    job = Job(job_id="j-fail")

    with pytest.raises(RuntimeError):
        runner.run_with_graph(job)

    assert job.status == "failed"
    assert job.error
    assert job.failure_report
