-- U7 Summarization — schema migration 001 (PostgreSQL, inherited from U3's RDS instance).
-- Personal glossary (P2). Owner-scoped (SEC-8): every read filters by user_id. glossary_ver
-- folds per-user personalization into the immutable summary cache key (Q7/TD-S6).

CREATE TABLE IF NOT EXISTS user_glossary (
    id              BIGSERIAL    PRIMARY KEY,
    user_id         VARCHAR(36)  NOT NULL,
    term_from       TEXT         NOT NULL,
    term_to         TEXT         NOT NULL,
    glossary_ver    INTEGER      NOT NULL DEFAULT 1,
    prompt_enforced BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- One preference per (owner, source term); upsert target.
CREATE UNIQUE INDEX IF NOT EXISTS ux_glossary_owner_term
    ON user_glossary (user_id, term_from);

-- Owner-scoped lookups (get_user_glossary / get_glossary_version).
CREATE INDEX IF NOT EXISTS ix_glossary_owner
    ON user_glossary (user_id);
