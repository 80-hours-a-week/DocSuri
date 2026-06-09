from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from typing import Iterable

import asyncpg
from pypdf import PdfReader

from app.config import Settings
from app.models import PaperChunk, PaperDocument, PaperSummary


def _quote_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return f'"{identifier}"'


def _first_present(candidates: Iterable[str], columns: set[str]) -> str | None:
    return next((column for column in candidates if column in columns), None)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in values) + "]"


def _metadata_dict(value: object) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


@dataclass
class TableColumns:
    columns: set[str]


class PostgresPaperRepository:
    def __init__(self, pool: asyncpg.Pool, settings: Settings):
        self.pool = pool
        self.settings = settings
        self._column_cache: dict[str, TableColumns] = {}

    async def list_papers(self) -> list[PaperSummary]:
        paper_columns = await self._columns(self.settings.paper_table)
        id_col = self.settings.paper_id_column
        title_col = _first_present(self.settings.title_columns, paper_columns.columns)
        abstract_col = "abstract" if "abstract" in paper_columns.columns else None

        select_title = f"{_quote_ident(title_col)}::text" if title_col else "'Untitled paper'"
        select_abstract = f"{_quote_ident(abstract_col)}::text" if abstract_col else "NULL"
        sql = (
            f"select {_quote_ident(id_col)}::text as id, {select_title} as title, "
            f"{select_abstract} as abstract from {_quote_ident(self.settings.paper_table)} "
            "order by 1 limit 100"
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql)
        return [PaperSummary(id=row["id"], title=row["title"], abstract=row["abstract"]) for row in rows]

    async def get_paper(self, paper_id: str) -> PaperDocument:
        paper = await self._fetch_paper_row(paper_id)
        chunks = await self._fetch_chunks(paper_id)
        if not paper.text and chunks:
            paper.text = "\n\n".join(f"[{chunk.anchor}] {chunk.text}" for chunk in chunks)
        paper.chunks = chunks
        return paper

    async def retrieve_relevant_chunks(
        self,
        paper_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[PaperChunk]:
        if not query_embedding:
            raise ValueError("query_embedding is required for PGVector retrieval.")
        columns = await self._columns(self.settings.paper_chunk_table)
        embedding_col = self.settings.paper_chunk_embedding_column
        if embedding_col not in columns.columns:
            raise ValueError(f"Embedding column not found: {embedding_col}")
        return await self._fetch_chunks_by_vector(paper_id, query_embedding, max(1, top_k))

    async def _columns(self, table_name: str) -> TableColumns:
        if table_name in self._column_cache:
            return self._column_cache[table_name]

        sql = """
            select column_name
            from information_schema.columns
            where table_schema = current_schema() and table_name = $1
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, table_name)
        table_columns = TableColumns(columns={row["column_name"] for row in rows})
        self._column_cache[table_name] = table_columns
        return table_columns

    async def _fetch_paper_row(self, paper_id: str) -> PaperDocument:
        columns = await self._columns(self.settings.paper_table)
        id_col = self.settings.paper_id_column
        title_col = _first_present(self.settings.title_columns, columns.columns)
        abstract_col = "abstract" if "abstract" in columns.columns else None
        text_col = _first_present(self.settings.text_columns, columns.columns)
        pdf_col = _first_present(self.settings.pdf_columns, columns.columns)

        selects = [f"{_quote_ident(id_col)}::text as id"]
        selects.append(f"{_quote_ident(title_col)}::text as title" if title_col else "'Untitled paper' as title")
        selects.append(f"{_quote_ident(abstract_col)}::text as abstract" if abstract_col else "NULL as abstract")
        selects.append(f"{_quote_ident(text_col)}::text as text" if text_col else "NULL as text")
        selects.append(f"{_quote_ident(pdf_col)} as pdf_bytes" if pdf_col else "NULL as pdf_bytes")

        sql = (
            f"select {', '.join(selects)} from {_quote_ident(self.settings.paper_table)} "
            f"where {_quote_ident(id_col)}::text = $1 limit 1"
        )
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, paper_id)
        if not row:
            raise KeyError(f"Paper not found: {paper_id}")

        text = row["text"] or ""
        if not text and row["pdf_bytes"]:
            text = _extract_pdf_text(bytes(row["pdf_bytes"]))
        return PaperDocument(
            id=row["id"],
            title=row["title"],
            abstract=row["abstract"],
            text=text,
            chunks=[],
        )

    async def _fetch_chunks(self, paper_id: str) -> list[PaperChunk]:
        columns = await self._columns(self.settings.paper_chunk_table)
        if not columns.columns:
            return []

        paper_id_col = self.settings.paper_chunk_paper_id_column
        text_col = _first_present(self.settings.chunk_text_columns, columns.columns)
        if not text_col:
            return []

        id_col = "id" if "id" in columns.columns else None
        anchor_col = _first_present(self.settings.chunk_anchor_columns, columns.columns)
        order_col = _first_present(self.settings.chunk_order_columns, columns.columns)
        section_col = "section" if "section" in columns.columns else "section_id" if "section_id" in columns.columns else None
        page_col = "page" if "page" in columns.columns else None
        paragraph_col = "paragraph" if "paragraph" in columns.columns else None

        selects = [
            f"{_quote_ident(text_col)}::text as text",
            f"{_quote_ident(paper_id_col)}::text as paper_id",
        ]
        selects.append(f"{_quote_ident(id_col)}::text as id" if id_col else "NULL as id")
        selects.append(f"{_quote_ident(anchor_col)}::text as anchor" if anchor_col else "NULL as anchor")
        selects.append(f"{_quote_ident(section_col)}::text as section" if section_col else "NULL as section")
        selects.append(f"{_quote_ident(page_col)}::int as page" if page_col else "NULL::int as page")
        selects.append(
            f"{_quote_ident(paragraph_col)}::int as paragraph" if paragraph_col else "NULL::int as paragraph"
        )

        order_by = f"order by {_quote_ident(order_col)}" if order_col else ""
        sql = (
            f"select {', '.join(selects)} from {_quote_ident(self.settings.paper_chunk_table)} "
            f"where {_quote_ident(paper_id_col)}::text = $1 {order_by} limit 500"
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, paper_id)

        chunks: list[PaperChunk] = []
        for idx, row in enumerate(rows, start=1):
            chunks.append(
                PaperChunk(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    text=row["text"],
                    anchor=row["anchor"] or f"§{idx}.1",
                    section=row["section"],
                    page=row["page"],
                    paragraph=row["paragraph"],
                )
            )
        return chunks

    async def _fetch_chunks_by_vector(
        self,
        paper_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[PaperChunk]:
        columns = await self._columns(self.settings.paper_chunk_table)
        paper_id_col = self.settings.paper_chunk_paper_id_column
        embedding_col = self.settings.paper_chunk_embedding_column
        text_col = _first_present(self.settings.chunk_text_columns, columns.columns)
        if not text_col:
            raise ValueError("No chunk text column found.")

        id_col = "id" if "id" in columns.columns else None
        anchor_col = _first_present(self.settings.chunk_anchor_columns, columns.columns)
        order_col = _first_present(self.settings.chunk_order_columns, columns.columns)
        section_col = "section" if "section" in columns.columns else "section_id" if "section_id" in columns.columns else None
        page_col = "page" if "page" in columns.columns else None
        paragraph_col = "paragraph" if "paragraph" in columns.columns else None
        metadata_col = "metadata" if "metadata" in columns.columns else None
        vector_literal = _vector_literal(query_embedding)

        selects = [
            f"{_quote_ident(text_col)}::text as text",
            f"{_quote_ident(paper_id_col)}::text as paper_id",
            f"{_quote_ident(embedding_col)} <=> $2::vector as distance",
        ]
        selects.append(f"{_quote_ident(id_col)}::text as id" if id_col else "NULL as id")
        selects.append(f"{_quote_ident(anchor_col)}::text as anchor" if anchor_col else "NULL as anchor")
        selects.append(f"{_quote_ident(section_col)}::text as section" if section_col else "NULL as section")
        selects.append(f"{_quote_ident(page_col)}::int as page" if page_col else "NULL::int as page")
        selects.append(
            f"{_quote_ident(paragraph_col)}::int as paragraph" if paragraph_col else "NULL::int as paragraph"
        )
        selects.append(f"{_quote_ident(metadata_col)} as metadata" if metadata_col else "'{}'::jsonb as metadata")

        tie_breaker = f", {_quote_ident(order_col)}" if order_col else ""
        sql = (
            f"select {', '.join(selects)} from {_quote_ident(self.settings.paper_chunk_table)} "
            f"where {_quote_ident(paper_id_col)}::text = $1 and {_quote_ident(embedding_col)} is not null "
            f"order by {_quote_ident(embedding_col)} <=> $2::vector{tie_breaker} limit $3"
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, paper_id, vector_literal, top_k)

        chunks: list[PaperChunk] = []
        for idx, row in enumerate(rows, start=1):
            metadata = _metadata_dict(row["metadata"])
            metadata["retrieval_distance"] = float(row["distance"])
            metadata["retrieval_rank"] = idx
            metadata["retrieval_source"] = "pgvector"
            chunks.append(
                PaperChunk(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    text=row["text"],
                    anchor=row["anchor"] or f"§{idx}.1",
                    section=row["section"],
                    page=row["page"],
                    paragraph=row["paragraph"],
                    metadata=metadata,
                )
            )
        return chunks
