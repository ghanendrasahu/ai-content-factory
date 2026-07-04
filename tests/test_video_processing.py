import ffmpeg

from app.services.clip_renderer import ClipRenderer
from app.services.video_optimizer import VideoOptimizer


def _video_stream(path):
    metadata = ffmpeg.probe(str(path))
    return next(
        stream for stream in metadata["streams"] if stream["codec_type"] == "video"
    )


def test_video_optimizer_outputs_vertical_h264(sample_video, tmp_path):
    output = tmp_path / "vertical.mp4"

    result = VideoOptimizer.make_vertical(str(sample_video), str(output))
    stream = _video_stream(result)

    assert stream["codec_name"] == "h264"
    assert stream["width"] == 1080
    assert stream["height"] == 1920


def test_clip_renderer_outputs_vertical_h264(monkeypatch, sample_video, tmp_path):
    monkeypatch.setattr("app.services.clip_renderer.OUTPUT_DIR", tmp_path)

    outputs = ClipRenderer.render(
        str(sample_video),
        [{"start": 0, "end": 0.8, "score": 1}],
        "job-test",
    )
    stream = _video_stream(outputs[0])

    assert stream["codec_name"] == "h264"
    assert stream["width"] == 1080
    assert stream["height"] == 1920
