create extension if not exists vector;

create table if not exists papers (
    id text primary key,
    title text not null,
    abstract text,
    structured_markdown text,
    pdf_bytes bytea,
    created_at timestamptz not null default now()
);

create table if not exists paper_chunks (
    id bigserial primary key,
    paper_id text not null references papers(id) on delete cascade,
    chunk_index int not null,
    anchor text not null,
    section text,
    page int,
    paragraph int,
    chunk_text text not null,
    embedding vector(1536),
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists paper_chunks_paper_idx on paper_chunks (paper_id, chunk_index);
create index if not exists paper_chunks_embedding_idx on paper_chunks using ivfflat (embedding vector_cosine_ops);
