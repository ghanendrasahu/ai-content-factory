import shutil
import subprocess
from dataclasses import dataclass

from app.config import settings
from app.logger import logger


@dataclass(frozen=True)
class HardwareProfile:
    has_nvidia_gpu: bool
    video_encoder: str
    whisper_device: str
    whisper_compute_type: str


class HardwareDetector:
    @staticmethod
    def detect() -> HardwareProfile:
        has_gpu = settings.ENABLE_GPU and HardwareDetector._has_nvidia_gpu()
        return HardwareProfile(
            has_nvidia_gpu=has_gpu,
            video_encoder=settings.NVIDIA_ENCODER if has_gpu else settings.CPU_ENCODER,
            whisper_device="cuda" if has_gpu else settings.WHISPER_DEVICE,
            whisper_compute_type=(
                "float16" if has_gpu else settings.WHISPER_COMPUTE_TYPE
            ),
        )

    @staticmethod
    def _has_nvidia_gpu() -> bool:
        if shutil.which("nvidia-smi") is None:
            return False

        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0 and "GPU" in result.stdout
        except Exception as exc:
            logger.warning("hardware.gpu_detection_failed error=%s", exc)
            return False
