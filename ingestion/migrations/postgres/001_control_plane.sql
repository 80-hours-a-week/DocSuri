CREATE TABLE IF NOT EXISTS dedup_state (
    paper_id TEXT PRIMARY KEY,
    current_version INTEGER NOT NULL CHECK (current_version >= 1),
    fingerprint TEXT,
    state TEXT NOT NULL CHECK (state IN ('INDEXED', 'TOMBSTONED')),
    ingested_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS watermark (
    name TEXT PRIMARY KEY,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_job (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    arxiv_ref TEXT,
    event_id TEXT,
    correlation_id TEXT,
    status TEXT NOT NULL,
    detail TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS rebuild_lock (
    lock_key TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dedup_state_updated_at ON dedup_state(updated_at);
CREATE INDEX IF NOT EXISTS idx_ingestion_job_status ON ingestion_job(status);
