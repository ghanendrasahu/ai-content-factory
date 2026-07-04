from dataclasses import dataclass, field
from typing import Optional

VALID_JOB_STATES = {
    "queued",
    "downloading",
    "transcribing",
    "detecting",
    "rendering",
    "optimizing",
    "completed",
    "failed",
}


@dataclass
class Job:
    job_id: str

    status: str = "queued"

    video_url: Optional[str] = None
    video_path: Optional[str] = None

    transcript: Optional[list] = None
    clips: Optional[list] = None

    step: str | None = "queued"
    progress: int = 0
    error: str | None = None

    result: Optional[list] = field(default_factory=list)
    clip_outputs: list[str] = field(default_factory=list)
    final_video: Optional[str] = None
    content_pack: Optional[dict] = None

    def set_state(self, state: str, progress: int) -> None:
        if state not in VALID_JOB_STATES:
            raise ValueError(f"Invalid job state: {state}")

        self.status = state
        self.step = state
        self.progress = max(0, min(progress, 100))
