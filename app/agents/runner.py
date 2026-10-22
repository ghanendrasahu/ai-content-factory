"""Execute jobs with the agent graph, falling back to the linear pipeline.

``PIPELINE_ENGINE`` selects the engine:

- ``graph``  (default) - LangGraph state machine
- ``linear`` - the original sequential pipeline

The graph is used automatically when ``langgraph`` is installed; otherwise the
runner logs a warning and uses the linear pipeline, so the service never
breaks because of an optional dependency.
"""

from __future__ import annotations

from app.config import settings
from app.core.paths import cleanup_job_temp_files, ensure_directories
from app.logger import logger
from app.models.job import Job
from app.services.pipeline import Pipeline
from app.services.self_healing import RecoveryStrategies


def graph_available() -> bool:
    """True when the LangGraph dependency is importable."""
    try:
        import langgraph.graph  # noqa: F401
    except ImportError:
        return False
    return True


def run_with_graph(job: Job) -> Job:
    """Run the job through the compiled LangGraph."""
    from app.agents.graph import build_graph

    ensure_directories()
    logger.info("Running job %s through the agent graph", job.job_id)

    try:
        compiled = build_graph()
        compiled.invoke({"job": job}, config={"recursion_limit": 50})
    except Exception as exc:
        job.set_state("failed", job.progress)
        job.error = str(exc)
        job.failure_report = RecoveryStrategies.diagnose(exc).__dict__
        cleanup_job_temp_files(job.job_id)
        logger.exception("Agent graph failed for job: %s", job.job_id)
        raise

    cleanup_job_temp_files(job.job_id)
    return job


def run_job(job: Job) -> Job:
    """Run a job with the configured engine (graph first, linear as fallback)."""
    engine = str(getattr(settings, "PIPELINE_ENGINE", "graph")).lower()

    if engine == "linear":
        return Pipeline.run(job)

    if not graph_available():
        logger.warning(
            "langgraph is not installed - falling back to the linear pipeline. "
            "Install it with `pip install langgraph`."
        )
        return Pipeline.run(job)

    try:
        return run_with_graph(job)
    except ImportError:
        logger.warning("langgraph could not be loaded - using the linear pipeline")
        return Pipeline.run(job)


__all__ = ["graph_available", "run_job", "run_with_graph"]
