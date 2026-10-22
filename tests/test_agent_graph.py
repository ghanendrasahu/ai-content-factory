"""Agent graph: planning, conditional routing and end-to-end execution.

The heavy services (whisper, ffmpeg, LLM) are stubbed - the tests verify the
orchestration, not the media processing.
"""

import pytest

from app.agents import graph as graph_module
from app.agents.state import build_plan, optional_stages
from app.config import settings
from app.models.job import Job
from app.services.youtube_publisher import PublishedVideo, VideoMetadata


@pytest.fixture()
def stubbed_services(tmp_path, monkeypatch):
    """Replace every external service with a deterministic local stub."""
    video = tmp_path / "source.mp4"
    video.write_bytes(b"0" * 32)
    rendered = tmp_path / "clip.mp4"
    rendered.write_bytes(b"0" * 32)
    vertical = tmp_path / "vertical.mp4"
    vertical.write_bytes(b"0" * 32)
    thumb = tmp_path / "thumb.jpg"
    thumb.write_bytes(b"0")
    srt = tmp_path / "subs.srt"
    srt.write_text("1\n", encoding="utf-8")

    transcript = [{"start": 0.0, "end": 1.0, "text": "hello"}]
    clips = [{"start": 0.0, "end": 1.0, "text": "hello"}]

    monkeypatch.setattr(
        graph_module.Transcriber,
        "transcribe",
        staticmethod(lambda path: {"transcript": transcript}),
    )
    monkeypatch.setattr(
        graph_module.ClipDetector, "detect", staticmethod(lambda t: clips)
    )
    monkeypatch.setattr(
        graph_module.ContentPackager,
        "generate",
        staticmethod(lambda t, c: {"title": "T", "description": "D", "tags": ["a"]}),
    )
    monkeypatch.setattr(
        graph_module.ClipRenderer,
        "render",
        staticmethod(lambda path, c, job_id: [str(rendered)]),
    )
    monkeypatch.setattr(
        graph_module.VideoOptimizer,
        "make_vertical",
        staticmethod(lambda src, out, transcript=None: str(vertical)),
    )
    monkeypatch.setattr(
        graph_module.SubtitleService,
        "generate_srt",
        staticmethod(lambda t, path: str(srt)),
    )
    monkeypatch.setattr(
        graph_module.SubtitleService,
        "burn",
        staticmethod(lambda video_path, srt_path, out: str(vertical)),
    )
    monkeypatch.setattr(
        graph_module.ThumbnailGenerator,
        "generate",
        staticmethod(lambda video, title, job_id: str(thumb)),
    )
    monkeypatch.setattr(
        graph_module.YouTubePublisher,
        "build_metadata",
        staticmethod(lambda **kwargs: VideoMetadata(title="T")),
    )
    monkeypatch.setattr(
        graph_module.YouTubePublisher,
        "publish",
        staticmethod(lambda video, metadata, **kwargs: _published()),
    )

    return {"video": video, "vertical": vertical, "thumb": thumb}


def _published():
    return PublishedVideo(
        video_id="vid-1",
        title="T",
        privacy_status="private",
        url="https://youtu.be/vid-1",
        bytes_uploaded=10,
    )


# =========================
# PLANNING
# =========================
def test_plan_reflects_settings_and_request(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SUBTITLES", True)
    monkeypatch.setattr(settings, "ENABLE_THUMBNAILS", True)
    monkeypatch.setattr(settings, "YOUTUBE_PUBLISH_ENABLED", True)

    job = Job(job_id="j1", publish_requested=True)
    plan = build_plan(job, settings)

    assert plan["subtitles"] is True
    assert plan["thumbnails"] is True
    assert plan["publish"] is True
    assert optional_stages(plan) == ["subtitle", "thumbnail", "publish"]


def test_plan_skips_publishing_when_not_requested(monkeypatch):
    monkeypatch.setattr(settings, "YOUTUBE_PUBLISH_ENABLED", True)

    plan = build_plan(Job(job_id="j2"), settings)

    assert plan["publish"] is False


def test_route_start_skips_download_for_local_video():
    state = {"job": Job(job_id="j3"), "plan": {"download": False}}
    assert graph_module.route_start(state) == "transcribe"


def test_route_optional_finishes_when_nothing_remains():
    assert graph_module.route_optional({"remaining": []}) == "finalize"
    assert graph_module.route_optional({"remaining": ["publish"]}) == "publish"


# =========================
# GRAPH EXECUTION
# =========================
def test_graph_compiles():
    compiled = graph_module.build_graph()
    assert compiled is not None


def test_graph_completes_job(stubbed_services, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SUBTITLES", False)
    monkeypatch.setattr(settings, "ENABLE_THUMBNAILS", False)
    monkeypatch.setattr(settings, "YOUTUBE_PUBLISH_ENABLED", False)

    job = Job(job_id="job-graph-1")
    job.video_path = str(stubbed_services["video"])

    graph_module.build_graph().invoke({"job": job}, config={"recursion_limit": 50})

    assert job.status == "completed"
    assert job.progress == 100
    assert job.final_video == str(stubbed_services["vertical"])
    assert job.content_pack["title"] == "T"
    # disabled stages are routed around
    assert job.subtitle_path is None
    assert job.thumbnail_path is None
    assert job.published_video is None


def test_graph_runs_optional_stages_when_enabled(stubbed_services, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SUBTITLES", True)
    monkeypatch.setattr(settings, "ENABLE_THUMBNAILS", True)
    monkeypatch.setattr(settings, "YOUTUBE_PUBLISH_ENABLED", True)

    job = Job(job_id="job-graph-2", publish_requested=True)
    job.video_path = str(stubbed_services["video"])

    graph_module.build_graph().invoke({"job": job}, config={"recursion_limit": 50})

    assert job.status == "completed"
    assert job.subtitle_path is not None
    assert job.thumbnail_path == str(stubbed_services["thumb"])
    assert job.published_video["video_id"] == "vid-1"


def test_graph_marks_job_failed_on_error(stubbed_services, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("transcription exploded")

    monkeypatch.setattr(graph_module.Transcriber, "transcribe", staticmethod(boom))
    monkeypatch.setattr(settings, "ENABLE_SUBTITLES", False)
    monkeypatch.setattr(settings, "ENABLE_THUMBNAILS", False)

    job = Job(job_id="job-graph-3")
    job.video_path = str(stubbed_services["video"])

    with pytest.raises(RuntimeError):
        graph_module.build_graph().invoke({"job": job}, config={"recursion_limit": 50})

    assert job.status == "failed"
    assert "exploded" in (job.error or "")
