from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    job_id: str
    status: str = "created"
    created_at: datetime = field(default_factory=datetime.now)
    video_url: str | None = None
    video_path: str | None = None
    transcript_path: str | None = None