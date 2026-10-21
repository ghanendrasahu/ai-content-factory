from app.core.job_store import JobStore

# Durable store with dict semantics: get()/[…update;]/values()/len/contains
# behave exactly like the legacy in-memory dict, but rows persist to SQLite
# (WAL) under data/jobs.db and are reloaded on boot.
jobs = JobStore()
