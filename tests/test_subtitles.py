from pathlib import Path

from app.services.subtitles import SubtitleService


def test_generate_srt(tmp_path):
    output = tmp_path / "sample.srt"

    result = SubtitleService.generate_srt(
        [{"start": 0, "end": 1.5, "text": "Hello world"}],
        output,
    )

    content = Path(result).read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,500" in content
    assert "Hello world" in content
