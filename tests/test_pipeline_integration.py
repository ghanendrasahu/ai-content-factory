from pathlib import Path

from app.models.job import Job
from app.services.pipeline import Pipeline


def test_pipeline_e2e_with_sample_video(monkeypatch, sample_video, tmp_path):
    monkeypatch.setattr("app.services.clip_renderer.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("app.services.pipeline.OUTPUT_DIR", tmp_path)

    monkeypatch.setattr(
        "app.services.pipeline.DownloadService.download",
        lambda url: ("sample", str(sample_video)),
    )
    monkeypatch.setattr(
        "app.services.pipeline.Transcriber.transcribe",
        lambda path: {
            "language": "en",
            "transcript": [{"start": 0, "end": 1, "text": "sample"}],
        },
    )
    monkeypatch.setattr(
        "app.services.pipeline.ClipDetector.detect",
        lambda transcript: [{"title": "clip", "start": 0, "end": 0.8, "score": 9}],
    )
    monkeypatch.setattr(
        "app.services.pipeline.ContentPackager.generate",
        lambda transcript, clips: {"title": "sample", "hashtags": []},
    )

    job = Job(job_id="integration", video_url="https://youtu.be/test")
    result = Pipeline.run(job)

    assert result.status == "completed"
    assert Path(result.final_video).is_file()
    assert result.clip_outputs
