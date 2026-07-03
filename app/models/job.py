from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Job:
    job_id: str

    status: str = "created"

    video_url: Optional[str] = None
    video_path: Optional[str] = None

    transcript: Optional[list] = None
    clips: Optional[list] = None


    step: str | None = None
    progress: int = 0
    error: str | None = None

    result: Optional[list] = field(default_factory=list)