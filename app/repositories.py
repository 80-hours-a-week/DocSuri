from __future__ import annotations

import io
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import asyncpg
from pypdf import PdfReader

from app.config import Settings
from app.models import PaperChunk, PaperDocument, PaperSummary


ANCHOR_RE = re.compile(r"\[(§\d+(?:\.\d+)?|p\.\d+\s*¶\d+)\]")


def _quote_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return f'"{identifier}"'


def _first_present(candidates: Iterable[str], columns: set[str]) -> str | None:
    return next((column for column in candidates if column in columns), None)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


@dataclass
class TableColumns:
    columns: set[str]


class PaperRepository(ABC):
    @abstractmethod
    async def list_papers(self) -> list[PaperSummary]:
        raise NotImplementedError

    @abstractmethod
    async def get_paper(self, paper_id: str) -> PaperDocument:
        raise NotImplementedError


class FallbackPaperRepository(PaperRepository):
    def __init__(self, primary: PaperRepository, fallback: PaperRepository):
        self.primary = primary
        self.fallback = fallback

    async def list_papers(self) -> list[PaperSummary]:
        primary_papers = await self.primary.list_papers()
        return primary_papers or await self.fallback.list_papers()

    async def get_paper(self, paper_id: str) -> PaperDocument:
        try:
            return await self.primary.get_paper(paper_id)
        except KeyError:
            return await self.fallback.get_paper(paper_id)


class PostgresPaperRepository(PaperRepository):
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
            anchor = row["anchor"] or f"§{idx}.1"
            chunks.append(
                PaperChunk(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    text=row["text"],
                    anchor=anchor,
                    section=row["section"],
                    page=row["page"],
                    paragraph=row["paragraph"],
                )
            )
        return chunks


class LocalPaperRepository(PaperRepository):
    supported_suffixes = {".json", ".md", ".txt", ".pdf"}

    def __init__(self, paper_dir: Path):
        self.paper_dir = paper_dir

    def has_papers(self) -> bool:
        return any(self._paper_files())

    async def list_papers(self) -> list[PaperSummary]:
        summaries: list[PaperSummary] = []
        for path in self._paper_files():
            try:
                paper = self._load_paper(path)
            except Exception:
                continue
            summaries.append(PaperSummary(id=paper.id, title=paper.title, abstract=paper.abstract))
        return summaries

    async def get_paper(self, paper_id: str) -> PaperDocument:
        for path in self._paper_files():
            paper = self._load_paper(path)
            if paper.id == paper_id:
                return paper
        raise KeyError(f"Paper not found: {paper_id}")

    def _paper_files(self) -> list[Path]:
        if not self.paper_dir.exists():
            return []
        return sorted(
            path
            for path in self.paper_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in self.supported_suffixes and not path.name.startswith(".")
        )

    def _load_paper(self, path: Path) -> PaperDocument:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._load_json_paper(path)
        if suffix == ".pdf":
            text = _extract_pdf_text(path.read_bytes())
            return self._build_plain_paper(path, text)
        text = path.read_text(encoding="utf-8-sig")
        return self._build_plain_paper(path, text)

    def _load_json_paper(self, path: Path) -> PaperDocument:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(f"JSON paper must be an object: {path}")

        paper_id = str(payload.get("id") or path.stem)
        text = str(payload.get("text") or payload.get("full_text") or payload.get("structured_markdown") or "")
        chunks = [
            self._chunk_from_json(item, paper_id, idx)
            for idx, item in enumerate(payload.get("chunks") or [], start=1)
            if isinstance(item, dict)
        ]
        if not text and chunks:
            text = "\n\n".join(f"[{chunk.anchor}] {chunk.text}" for chunk in chunks)
        if not chunks:
            chunks = _chunks_from_text(paper_id, text)

        return PaperDocument(
            id=paper_id,
            title=str(payload.get("title") or payload.get("paper_title") or path.stem),
            abstract=payload.get("abstract"),
            text=text,
            chunks=chunks,
        )

    def _chunk_from_json(self, item: dict, paper_id: str, idx: int) -> PaperChunk:
        anchor = str(item.get("anchor") or item.get("section_anchor") or item.get("locator") or f"§{idx}.1")
        return PaperChunk(
            id=str(item["id"]) if item.get("id") is not None else None,
            paper_id=paper_id,
            text=str(item.get("text") or item.get("chunk_text") or item.get("content") or item.get("body") or ""),
            anchor=anchor,
            section=str(item["section"]) if item.get("section") is not None else None,
            page=int(item["page"]) if item.get("page") is not None else None,
            paragraph=int(item["paragraph"]) if item.get("paragraph") is not None else None,
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )

    def _build_plain_paper(self, path: Path, text: str) -> PaperDocument:
        title = _title_from_text(text) or path.stem
        return PaperDocument(
            id=path.stem,
            title=title,
            abstract=_abstract_from_text(text),
            text=text,
            chunks=_chunks_from_text(path.stem, text),
        )


def _title_from_text(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
        return stripped[:120]
    return None


def _abstract_from_text(text: str) -> str | None:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        return None
    first = paragraphs[0]
    if first.startswith("#") and len(paragraphs) > 1:
        first = paragraphs[1]
    return first[:800]


def _chunks_from_text(paper_id: str, text: str) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    for idx, paragraph in enumerate(paragraphs, start=1):
        anchors = ANCHOR_RE.findall(paragraph)
        anchor = anchors[0] if anchors else f"§{idx}.1"
        chunk_text = re.sub(rf"^\s*\[{re.escape(anchor)}\]\s*", "", paragraph).strip()
        if not chunk_text:
            continue
        chunks.append(PaperChunk(paper_id=paper_id, text=chunk_text, anchor=anchor))
    if chunks:
        return chunks

    stripped = text.strip()
    if not stripped:
        return []
    return [PaperChunk(paper_id=paper_id, text=stripped, anchor="§1.1")]


class DemoPaperRepository(PaperRepository):
    def __init__(self) -> None:
        self.paper = PaperDocument(
            id="demo-paper",
            title="DocSuri Demo: Retrieval-Augmented Paper Summarization",
            abstract="A demo paper used when PostgreSQL is not configured.",
            text=(
                "[§1.1] We propose DocSuri, a retrieval-augmented workflow for summarizing and translating "
                "academic papers. The system stores original PDFs in PostgreSQL and embedded chunks in PGVector.\n\n"
                "[§2.1] The method fetches structured paper text and relevant chunks, builds a cached prompt, "
                "and asks a language model to produce anchored Korean summaries.\n\n"
                "[§3.1] Experiments show that anchor validation reduces unsupported claims and improves user trust "
                "during literature review sessions.\n\n"
                "[§4.1] Limitations include dependence on extraction quality, table understanding, and the cost of "
                "verifying every generated sentence."
            ),
            chunks=[
                PaperChunk(
                    id="c1",
                    paper_id="demo-paper",
                    anchor="§1.1",
                    text="We propose DocSuri, a retrieval-augmented workflow for summarizing and translating academic papers.",
                ),
                PaperChunk(
                    id="c2",
                    paper_id="demo-paper",
                    anchor="§2.1",
                    text="The method fetches structured paper text and relevant chunks, builds a cached prompt, and asks a language model to produce anchored Korean summaries.",
                ),
                PaperChunk(
                    id="c3",
                    paper_id="demo-paper",
                    anchor="§3.1",
                    text="Experiments show that anchor validation reduces unsupported claims and improves user trust during literature review sessions.",
                ),
                PaperChunk(
                    id="c4",
                    paper_id="demo-paper",
                    anchor="§4.1",
                    text="Limitations include dependence on extraction quality, table understanding, and the cost of verifying every generated sentence.",
                ),
            ],
        )

    async def list_papers(self) -> list[PaperSummary]:
        return [PaperSummary(id=self.paper.id, title=self.paper.title, abstract=self.paper.abstract)]

    async def get_paper(self, paper_id: str) -> PaperDocument:
        if paper_id != self.paper.id:
            raise KeyError(f"Paper not found: {paper_id}")
        return self.paper.model_copy(deep=True)
