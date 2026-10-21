"""Durable job store tests: persistence, restart recovery, dict semantics."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.core.job_store import JobStore
from app.models.job import Job


@pytest.fixture()
def store(tmp_path: Path) -> JobStore:
    instance = JobStore(str(tmp_path / "jobs.db"))
    try:
        yield instance
    finally:
        instance.close()


def _fresh_store(tmp_path: Path) -> JobStore:
    """Simulate a restart: a new store instance against the same DB file."""
    return JobStore(str(tmp_path / "jobs.db"))


def test_put_then_restart_recovery(tmp_path: Path, store: JobStore):
    job = Job(job_id="abc", status="transcribing", progress=40)
    job.video_url = "https://youtu.be/x"
    store["abc"] = job

    with sqlite3.connect(tmp_path / "jobs.db") as conn:
        rows = conn.execute("SELECT COUNT(*) FROM jobs").fetchall()
        assert rows[0][0] == 1

    recovered = _fresh_store(tmp_path)
    try:
        assert "abc" in recovered
        same = recovered["abc"]
        assert same.status == "transcribing"
        assert same.progress == 40
        assert same.video_url == "https://youtu.be/x"
    finally:
        recovered.close()


def test_upsert_persists_over_status_changes(tmp_path: Path, store: JobStore):
    job = Job(job_id="up1")
    store["up1"] = job

    job.set_state("downloading", 20)
    store["up1"] = job  # mutation-only writes require an explicit persist

    recovered = _fresh_store(tmp_path)
    try:
        assert recovered["up1"].status == "downloading"
        assert recovered["up1"].progress == 20
    finally:
        recovered.close()


def test_purge_and_delete(tmp_path: Path, store: JobStore):
    store["del_me"] = Job(job_id="del_me")
    assert "del_me" in store

    del store["del_me"]

    assert "del_me" not in store
    recovered = _fresh_store(tmp_path)
    try:
        assert "del_me" not in recovered
    finally:
        recovered.close()


def test_len_values_contains(tmp_path: Path, store: JobStore):
    assert len(store) == 0
    store["a"] = Job(job_id="a", progress=1)
    store["b"] = Job(job_id="b", progress=2)

    assert len(store) == 2
    assert sorted(store) == ["a", "b"]
    assert {job.job_id for job in store.values()} == {"a", "b"}
    assert store.get("missing") is None
    with pytest.raises(KeyError):
        _ = store["missing"]


def test_sql_parity_meta(tmp_path: Path, store: JobStore):
    store["m1"] = Job(job_id="m1")
    meta = store.get_meta()
    assert meta["sql_rows"] == 1
    assert meta["memory"] == 1


def test_wal_mode_available(tmp_path: Path, store: JobStore):
    with sqlite3.connect(tmp_path / "jobs.db") as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"
