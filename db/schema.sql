-- ============================================================
-- 0. Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;          -- pgvector


-- ============================================================
-- 1. papers
-- ============================================================
CREATE TABLE papers (
    -- 식별자
    id                BIGSERIAL       PRIMARY KEY,
    arxiv_id          TEXT            UNIQUE,                    -- arXiv ID  (예: 1706.03762)
    s2_paper_id       TEXT            UNIQUE,                    -- Semantic Scholar paper ID
    openalex_id       TEXT            UNIQUE,                    -- OpenAlex ID (예: W2741809807)
    doi               TEXT            UNIQUE,                    -- DOI

    -- 기본 메타데이터
    title             TEXT            NOT NULL,
    authors           JSONB           NOT NULL DEFAULT '[]',     -- [{"name": "Yann LeCun", "affiliations": [...]}]
    year              SMALLINT,

    -- 본문
    abstract          TEXT,
    pdf_object_key    TEXT,                                      -- 로컬 or S3 오브젝트 키

    -- 지표
    citation_count    INTEGER         NOT NULL DEFAULT 0,
    influential_count INTEGER         NOT NULL DEFAULT 0,        -- Semantic Scholar influentialCitationCount

    -- 벡터 (Bedrock Titan Embed Text V2, 1024차원)
    embedding         vector(1024),

    -- 상태
    status            TEXT            NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'active', 'failed')),
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 인용수 내림차순 정렬용
CREATE INDEX idx_papers_citation_count  ON papers (citation_count DESC);
-- 최신순 정렬용
CREATE INDEX idx_papers_year            ON papers (year DESC);
-- 벡터 유사도 검색 (HNSW + cosine distance, nomic-embed-text 768차원)
CREATE INDEX idx_papers_embedding       ON papers USING hnsw (embedding vector_cosine_ops);


-- ============================================================
-- 2. user_library
-- ============================================================
CREATE TABLE user_library (
    user_id    TEXT        NOT NULL,                            -- session/쿠키 기반 임시 ID
    paper_id   BIGINT      NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tags       TEXT[]      NOT NULL DEFAULT '{}',

    PRIMARY KEY (user_id, paper_id)
);

CREATE INDEX idx_user_library_user_id ON user_library (user_id);
