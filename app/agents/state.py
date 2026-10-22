"""Shared state and stage plan for the agent graph."""

from __future__ import annotations

from typing import Any, TypedDict


class JobState(TypedDict, total=False):
    """State threaded through the agent graph.

    The ``job`` object stays the single source of truth for API consumers; the
    graph additionally carries the intermediate artefacts between nodes so a
    branch can be skipped without recomputing anything.
    """

    job: Any
    video_path: str
    transcript: list
    clips: list
    content_pack: dict
    clip_outputs: list
    final_video: str
    subtitle_path: str | None
    thumbnail_path: str | None
    published_video: dict | None
    plan: dict
    remaining: list
    error: str | None


def build_plan(job: Any, settings: Any) -> dict[str, Any]:
    """Decide which stages this job needs.

    The plan is computed before transcription, so optional stages are decided
    from configuration and the request - not from artefacts that do not exist
    yet. The transcript requirement is enforced by the stage itself.
    """
    return {
        "download": not getattr(job, "video_path", None),
        "subtitles": bool(getattr(settings, "ENABLE_SUBTITLES", False)),
        "thumbnails": bool(getattr(settings, "ENABLE_THUMBNAILS", False)),
        "publish": bool(getattr(settings, "YOUTUBE_PUBLISH_ENABLED", False))
        and bool(getattr(job, "publish_requested", False)),
    }


def optional_stages(plan: dict[str, Any]) -> list[str]:
    """Ordered list of optional stages to execute after the core pipeline."""
    stages: list[str] = []
    if plan.get("subtitles"):
        stages.append("subtitle")
    if plan.get("thumbnails"):
        stages.append("thumbnail")
    if plan.get("publish"):
        stages.append("publish")
    return stages
