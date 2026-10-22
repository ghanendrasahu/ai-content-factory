"""LangGraph orchestration for the content factory.

The graph replaces the linear pipeline with an explicit state machine:

    plan -> acquire -> transcribe -> detect -> package -> render -> optimize
          -> [subtitle] -> [thumbnail] -> [publish] -> finalize

Optional stages are routed around when the plan says so (subtitles disabled,
no thumbnail requested, publishing not enabled), and every node reuses the
existing services - the graph adds orchestration, not duplicate logic.

``langgraph`` is imported lazily: when it is not installed the caller falls
back to the linear pipeline (see ``app.agents.runner``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ai.clip_detector import ClipDetector
from app.ai.content_packager import ContentPackager
from app.ai.transcriber import Transcriber
from app.config import settings
from app.core.cancellation import JobCancelled, check_cancelled
from app.core.paths import OUTPUT_DIR
from app.logger import logger
from app.services.clip_renderer import ClipRenderer
from app.services.download_service import DownloadService
from app.services.progress import ProgressTracker
from app.services.self_healing import RecoveryStrategies, RetryManager
from app.services.subtitles import SubtitleService
from app.services.thumbnail import ThumbnailGenerator
from app.services.video_optimizer import VideoOptimizer
from app.services.youtube_publisher import YouTubePublisher

from app.agents.state import JobState, build_plan, optional_stages


def _retry():
    return RetryManager()


def _progress(job: Any, stage: str, percent: int) -> None:
    """Publish progress onto the job so API consumers see the same states."""
    job.apply_progress(ProgressTracker().snapshot(stage, percent))


def _require_file(path: str | Path, label: str) -> str:
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return str(resolved)


# =========================
# NODES
# =========================
def node_plan(state: JobState) -> dict[str, Any]:
    """Decide the stage plan and the optional stages that remain."""
    job = state["job"]
    _progress(job, "queued", 0)
    plan = build_plan(job, settings)
    remaining = optional_stages(plan)
    logger.info(
        "graph.plan job=%s download=%s subtitles=%s thumbnails=%s publish=%s",
        job.job_id,
        plan["download"],
        plan["subtitles"],
        plan["thumbnails"],
        plan["publish"],
    )
    return {
        "plan": plan,
        "remaining": remaining,
        "error": None,
        # Seed the source path: the download node may be routed around.
        "video_path": getattr(job, "video_path", None),
    }


def node_acquire(state: JobState) -> dict[str, Any]:
    """Download the source video when it is not local yet."""
    job = state["job"]
    if job.video_path:
        return {"video_path": job.video_path}

    if not job.video_url:
        raise ValueError("No video URL provided")

    _progress(job, "downloading", 10)

    _, video_path = _retry().run(
        lambda: DownloadService.download(job.video_url), "download"
    )
    job.video_path = _require_file(video_path, "Downloaded video")
    return {"video_path": job.video_path}


def node_transcribe(state: JobState) -> dict[str, Any]:
    """Transcribe the source video into timed segments."""
    job = state["job"]
    source = state.get("video_path") or job.video_path
    if not source:
        raise ValueError("No source video available for transcription")

    _progress(job, "transcribing", 30)
    result = _retry().run(lambda: Transcriber.transcribe(source), "whisper")
    job.transcript = result["transcript"]
    if not job.transcript:
        raise ValueError("Transcription produced no segments")
    return {"transcript": job.transcript}


def node_detect(state: JobState) -> dict[str, Any]:
    """Detect the highlight clips."""
    job = state["job"]
    _progress(job, "detecting", 45)
    clips = _retry().run(lambda: ClipDetector.detect(state["transcript"]), "detect")
    if not clips:
        raise ValueError("No clips detected")
    job.clips = clips
    return {"clips": clips}


def node_package(state: JobState) -> dict[str, Any]:
    """Generate titles, descriptions and tags with the LLM."""
    job = state["job"]
    _progress(job, "content_generation", 55)
    job.content_pack = _retry().run(
        lambda: ContentPackager.generate(state["transcript"], state["clips"]),
        "content_generation",
    )
    return {"content_pack": job.content_pack}


def node_render(state: JobState) -> dict[str, Any]:
    """Render the selected clips."""
    job = state["job"]
    _progress(job, "rendering", 70)
    clip_outputs = _retry().run(
        lambda: ClipRenderer.render(state["video_path"], state["clips"], job.job_id),
        "render",
    )
    if not clip_outputs:
        raise ValueError("No clips were rendered")
    job.clip_outputs = clip_outputs
    return {"clip_outputs": clip_outputs}


def node_optimize(state: JobState) -> dict[str, Any]:
    """Produce the final vertical (Shorts) video."""
    job = state["job"]
    _progress(job, "optimizing", 90)
    vertical_output = OUTPUT_DIR / f"{job.job_id}_vertical.mp4"
    source_clip = _require_file(state["clip_outputs"][0], "Rendered clip")
    final_video = _retry().run(
        lambda: VideoOptimizer.make_vertical(
            source_clip, str(vertical_output), state["transcript"]
        ),
        "optimize",
    )
    job.final_video = _require_file(final_video, "Vertical video")
    return {"final_video": job.final_video}


def node_subtitle(state: JobState) -> dict[str, Any]:
    """Generate and burn in subtitles."""
    job = state["job"]
    _progress(job, "optimizing", 92)
    subtitle_path = OUTPUT_DIR / f"{job.job_id}.srt"
    job.subtitle_path = SubtitleService.generate(state["transcript"], subtitle_path)
    subtitled_output = OUTPUT_DIR / f"{job.job_id}_vertical_subtitled.mp4"
    job.final_video = _retry().run(
        lambda: SubtitleService.burn(
            state["final_video"], job.subtitle_path, str(subtitled_output)
        ),
        "subtitles",
    )
    return {"subtitle_path": job.subtitle_path, "final_video": job.final_video}


def node_thumbnail(state: JobState) -> dict[str, Any]:
    """Render the thumbnail poster."""
    job = state["job"]
    _progress(job, "optimizing", 94)
    title = (job.content_pack or {}).get("title", "AI Content Factory")
    job.thumbnail_path = ThumbnailGenerator.generate(
        state["final_video"], title, job.job_id
    )
    return {"thumbnail_path": job.thumbnail_path}


def node_publish(state: JobState) -> dict[str, Any]:
    """Publish the finished video to YouTube."""
    job = state["job"]
    _progress(job, "publishing", 97)
    metadata = YouTubePublisher.build_metadata(content_pack=job.content_pack)
    published = _retry().run(
        lambda: YouTubePublisher.publish(state["final_video"], metadata), "publish"
    )
    job.published_video = published.to_dict()
    return {"published_video": job.published_video}


def node_finalize(state: JobState) -> dict[str, Any]:
    """Mark the job complete."""
    job = state["job"]
    job.set_state("completed", 100)
    return {"error": None}


# =========================
# ROUTING
# =========================
def route_start(state: JobState) -> str:
    """Skip the download when the video is already local."""
    return "acquire" if state.get("plan", {}).get("download", True) else "transcribe"


def route_optional(state: JobState) -> str:
    """Route to the next optional stage, or finish."""
    remaining = list(state.get("remaining") or [])
    return remaining[0] if remaining else "finalize"


def _pop_remaining(state: JobState, stage: str) -> dict[str, Any]:
    remaining = [item for item in (state.get("remaining") or []) if item != stage]
    return {"remaining": remaining}


def _guard(node):
    """Mark the job failed and re-raise, so the graph reports failures itself."""

    def wrapped(state: JobState) -> dict[str, Any]:
        job = state.get("job")
        try:
            check_cancelled(job)
            return node(state)
        except JobCancelled:
            if job is not None:
                job.set_state("cancelled", job.progress)
                job.error = "cancelled by user"
            raise
        except Exception as exc:
            if job is not None:
                job.set_state("failed", job.progress)
                job.error = str(exc)
                job.failure_report = RecoveryStrategies.diagnose(exc).__dict__
            raise

    return wrapped


def _make_optional(node, stage: str):
    def wrapped(state: JobState) -> dict[str, Any]:
        update = node(state)
        update.update(_pop_remaining(state, stage))
        return update

    return _guard(wrapped)


# =========================
# GRAPH
# =========================
def build_graph():
    """Compile the LangGraph state machine.

    Raises ``ImportError`` when langgraph is not installed - the runner then
    falls back to the linear pipeline.
    """
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(JobState)

    graph.add_node("plan", _guard(node_plan))
    graph.add_node("acquire", _guard(node_acquire))
    graph.add_node("transcribe", _guard(node_transcribe))
    graph.add_node("detect", _guard(node_detect))
    graph.add_node("package", _guard(node_package))
    graph.add_node("render", _guard(node_render))
    graph.add_node("optimize", _guard(node_optimize))
    graph.add_node("subtitle", _make_optional(node_subtitle, "subtitle"))
    graph.add_node("thumbnail", _make_optional(node_thumbnail, "thumbnail"))
    graph.add_node("publish", _make_optional(node_publish, "publish"))
    graph.add_node("finalize", node_finalize)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges(
        "plan",
        route_start,
        {"acquire": "acquire", "transcribe": "transcribe"},
    )
    graph.add_edge("acquire", "transcribe")
    graph.add_edge("transcribe", "detect")
    graph.add_edge("detect", "package")
    graph.add_edge("package", "render")
    graph.add_edge("render", "optimize")

    # Every optional stage routes to the next remaining one (or to finalize).
    # Sources are the optimizer plus each optional stage itself.
    for source in ("optimize", "subtitle", "thumbnail", "publish"):
        graph.add_conditional_edges(
            source,
            route_optional,
            {
                "subtitle": "subtitle",
                "thumbnail": "thumbnail",
                "publish": "publish",
                "finalize": "finalize",
            },
        )
    graph.add_edge("finalize", END)

    return graph.compile()


__all__ = [
    "build_graph",
    "node_acquire",
    "node_detect",
    "node_finalize",
    "node_optimize",
    "node_package",
    "node_plan",
    "node_publish",
    "node_render",
    "node_subtitle",
    "node_thumbnail",
    "node_transcribe",
    "route_optional",
    "route_start",
]
