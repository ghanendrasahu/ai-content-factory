from dataclasses import dataclass
from time import perf_counter


@dataclass
class ProgressSnapshot:
    stage: str
    progress: int
    elapsed_seconds: float
    estimated_remaining_seconds: float | None


class ProgressTracker:
    def __init__(self):
        self.started_at = perf_counter()

    def snapshot(self, stage: str, progress: int) -> ProgressSnapshot:
        elapsed = perf_counter() - self.started_at
        remaining = None
        if progress > 0:
            remaining = max((elapsed / progress) * (100 - progress), 0)
        return ProgressSnapshot(stage, progress, round(elapsed, 2), remaining)
