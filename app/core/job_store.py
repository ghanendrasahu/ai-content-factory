from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from types import TracebackType
from typing import Iterator, Mapping

from app.models.job import Job

_TRANSACTION_LOCK = threading.Lock()  # serializes cross-connection writes


class JobStore(Mapping[str, Job]):
    """Durable job store: in-memory `dict` semantics backed by SQLite.

    Entries survive process restarts (compose mounts the data dir), so jobs
    are no longer lost when the API restarts mid-run.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id     TEXT PRIMARY KEY,
        payload    TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """

    def __init__(self, database_path: str | None = None) -> None:
        try:
            from app.core.paths import JOBS_DB

            default_path = JOBS_DB
        except ImportError:  # circular safety when importing paths first
            from app.config import settings

            default_path = settings.JOB_STORE_DB

        self._path = str(database_path or default_path)
        self._local = threading.local()
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._migrate()
        self._recover()

    # ----- connections -----------------------------------------------------
    def _connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def _migrate(self) -> None:
        with self._connection() as conn:
            conn.executescript(self._SCHEMA)

    def _recover(self) -> None:
        """Boot recovery: rebuild the in-memory map from persisted rows."""
        with self._lock:
            for row in self._connection().execute("SELECT job_id, payload FROM jobs"):
                self._jobs[row[0]] = Job(**json.loads(row[1]))

    # ----- Mapping protocol ------------------------------------------------
    def __getitem__(self, job_id: str) -> Job:
        with self._lock:
            return self._jobs[job_id]

    def __setitem__(self, job_id: str, job: Job) -> None:
        payload = json.dumps(job.__dict__, sort_keys=True)
        with _TRANSACTION_LOCK, self._connection() as conn:
            conn.execute(
                "INSERT INTO jobs (job_id, payload) VALUES (?, ?) "
                "ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload, "
                "updated_at=CURRENT_TIMESTAMP",
                (job_id, payload),
            )
        with self._lock:
            self._jobs[job_id] = job

    def __delitem__(self, job_id: str) -> None:
        with _TRANSACTION_LOCK, self._connection() as conn:
            conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        with self._lock:
            self._jobs.pop(job_id, None)

    def clear(self) -> None:
        """Purge every job (used by test teardowns)."""
        with _TRANSACTION_LOCK, self._connection() as conn:
            conn.execute("DELETE FROM jobs")
        with self._lock:
            self._jobs.clear()

    def __contains__(self, job_id: object) -> bool:
        with self._lock:
            return job_id in self._jobs

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._jobs.keys()))

    def values(self) -> Iterator[Job]:
        with self._lock:
            return iter(list(self._jobs.values()))

    def get(self, job_id: str, default=None):  # noqa: ANN001 (Mapping compat)
        with self._lock:
            return self._jobs.get(job_id, default)

    def get_meta(self) -> dict[str, int]:
        """Sanity metadata for observability endpoints (row vs memory parity)."""
        with _TRANSACTION_LOCK:
            rows = self._connection().execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return {"sql_rows": rows, "memory": len(self._jobs)}

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def __enter__(self) -> "JobStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
