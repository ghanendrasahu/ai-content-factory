from dataclasses import dataclass, field
from typing import Optional


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
