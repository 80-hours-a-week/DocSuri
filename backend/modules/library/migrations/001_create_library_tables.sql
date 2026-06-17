-- U4 Library — schema migration 001 (PostgreSQL, inherited from U3's RDS instance).
-- Three owner-private tables. All access is owner-scoped (INV-L1); indexes back the
-- (owner_id, sort_key) keyset pagination (BR-L8) and the idempotency lookups (BR-L1/L3/L7).

CREATE TABLE IF NOT EXISTS saved_searches (
    id               VARCHAR(36)  PRIMARY KEY,
    owner_id         VARCHAR(36)  NOT NULL,
    query            TEXT         NOT NULL,
    normalized_query TEXT         NOT NULL,
    label            VARCHAR(200),
    created_at       TIMESTAMPTZ  NOT NULL
);
-- BR-L1: dedup identity is (owner_id, normalized_query).
CREATE UNIQUE INDEX IF NOT EXISTS ux_saved_owner_norm
    ON saved_searches (owner_id, normalized_query);
-- BR-L8: most-recent-first keyset page.
CREATE INDEX IF NOT EXISTS ix_saved_owner_created
    ON saved_searches (owner_id, created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS library_items (
    id        VARCHAR(36) PRIMARY KEY,
    owner_id  VARCHAR(36) NOT NULL,
    arxiv_id  VARCHAR(64) NOT NULL,
    meta      JSONB       NOT NULL,
    added_at  TIMESTAMPTZ NOT NULL
);
-- BR-L3/QT-4: idempotent add identity is (owner_id, arxiv_id).
CREATE UNIQUE INDEX IF NOT EXISTS ux_library_owner_arxiv
    ON library_items (owner_id, arxiv_id);
CREATE INDEX IF NOT EXISTS ix_library_owner_added
    ON library_items (owner_id, added_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS search_history (
    id           VARCHAR(36) PRIMARY KEY,
    owner_id     VARCHAR(36) NOT NULL,
    query        TEXT        NOT NULL,
    executed_at  TIMESTAMPTZ NOT NULL,
    result_count INTEGER     NOT NULL,
    dedupe_key   VARCHAR(64) NOT NULL
);
-- BR-L7/INV-L3: at-least-once → exactly-once per (owner_id, dedupe_key).
CREATE UNIQUE INDEX IF NOT EXISTS ux_history_owner_dedupe
    ON search_history (owner_id, dedupe_key);
CREATE INDEX IF NOT EXISTS ix_history_owner_executed
    ON search_history (owner_id, executed_at DESC, id DESC);
