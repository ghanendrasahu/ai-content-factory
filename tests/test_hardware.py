from app.services.hardware import HardwareDetector


def test_hardware_detector_falls_back_without_nvidia(monkeypatch):
    monkeypatch.setattr("app.services.hardware.shutil.which", lambda name: None)

    profile = HardwareDetector.detect()

    assert profile.has_nvidia_gpu is False
    assert profile.video_encoder == "libx264"
