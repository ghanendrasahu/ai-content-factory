"""Cooperative cancellation for long-running jobs."""

from __future__ import annotations


class JobCancelled(RuntimeError):
    """Raised when a job was cancelled by the user."""


def is_cancelled(job) -> bool:
    """True when the job was cancelled."""
    return getattr(job, "status", "") == "cancelled"


def check_cancelled(job) -> None:
    """Raise ``JobCancelled`` when the job was cancelled.

    Pipeline stages call this between units of work so a cancel request is
    honoured at the next stage boundary instead of killing the process.
    """
    if is_cancelled(job):
        raise JobCancelled(f"Job {getattr(job, 'job_id', '?')} was cancelled")


__all__ = ["JobCancelled", "check_cancelled", "is_cancelled"]
