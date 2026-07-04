import pytest

from app.services.self_healing import ErrorCategory, ErrorClassifier, RetryManager


def test_error_classifier_detects_ffmpeg():
    category = ErrorClassifier.classify(RuntimeError("ffmpeg failed"))

    assert category == ErrorCategory.FFMPEG


def test_retry_manager_recovers():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary")
        return "ok"

    result = RetryManager(attempts=2, initial_delay=0, backoff=1).run(flaky, "test")

    assert result == "ok"


def test_retry_manager_raises_after_exhaustion():
    with pytest.raises(RuntimeError):
        RetryManager(attempts=1, initial_delay=0, backoff=1).run(
            lambda: (_ for _ in ()).throw(RuntimeError("failed")),
            "test",
        )
