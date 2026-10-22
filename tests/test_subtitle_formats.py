"""Subtitle formats: SRT, WebVTT and styled ASS."""

from pathlib import Path

from app.services.subtitles import SubtitleService

TRANSCRIPT = [
    {"start": 0.0, "end": 1.25, "text": "First line"},
    {"start": 1.25, "end": 2.5, "text": "Second line"},
    {"start": 2.5, "end": 3.0, "text": "   "},
]


def test_srt_format(tmp_path):
    path = tmp_path / "out.srt"

    result = SubtitleService.generate_srt(TRANSCRIPT, path)

    content = Path(result).read_text(encoding="utf-8")
    assert content.startswith("1\n")
    assert "00:00:00,000 --> 00:00:01,250" in content
    # empty cues are skipped
    assert "Second line" in content
    assert content.count("-->") == 2


def test_vtt_format(tmp_path):
    path = tmp_path / "out.vtt"

    result = SubtitleService.generate_vtt(TRANSCRIPT, path)

    content = Path(result).read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.250" in content
    assert "First line" in content


def test_ass_format_has_styles_and_dialogue(tmp_path):
    path = tmp_path / "out.ass"

    result = SubtitleService.generate_ass(TRANSCRIPT, path)

    content = Path(result).read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "Style: Default" in content
    assert "[Events]" in content
    assert "Dialogue: 0,0:00:00.00,0:00:01.25,Default" in content
    assert "First line" in content


def test_generate_dispatches_on_format(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.subtitles.settings.SUBTITLE_FORMAT", "vtt", raising=False
    )

    vtt = SubtitleService.generate(TRANSCRIPT, tmp_path / "dispatch.vtt")
    srt = SubtitleService.generate(TRANSCRIPT, tmp_path / "dispatch.srt", fmt="srt")
    ass = SubtitleService.generate(TRANSCRIPT, tmp_path / "dispatch.ass", fmt="ass")

    assert Path(vtt).read_text(encoding="utf-8").startswith("WEBVTT")
    assert Path(srt).read_text(encoding="utf-8").startswith("1\n")
    assert "[Events]" in Path(ass).read_text(encoding="utf-8")


def test_ass_timestamp_uses_centiseconds():
    assert SubtitleService._format_time_ass(0.0) == "0:00:00.00"
    assert SubtitleService._format_time_ass(65.5) == "0:01:05.50"
    assert SubtitleService._format_time_ass(3661.25) == "1:01:01.25"
