from app.ai.clip_detector import ClipDetector


def test_clip_detector_filters_invalid_clips(monkeypatch):
    monkeypatch.setattr(
        "app.ai.clip_detector.LLM.generate",
        lambda prompt: """
        [
          {"title": "good", "start": 0, "end": 10, "score": 9},
          {"title": "bad", "start": 10, "end": 1, "score": 10}
        ]
        """,
    )

    clips = ClipDetector.detect([{"start": 0, "end": 20, "text": "hello"}])

    assert len(clips) == 1
    assert clips[0]["title"] == "good"
