# DO NOT EDIT. Generated from the JSON Schema SSOT in shared/ by tools/generate.py.
# Change the schema and regenerate (§5-B); never hand-edit.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ArxivCategory(RootModel[str]):
    root: str = Field(
        ...,
        description='An arXiv category code within the corpus slice (e.g. cs.LG, cs.AI, cs.CL, cs.CV, stat.ML). Trace: C-6.',
    )


class DocModelBlockRef(BaseModel):
    """
    Structured DocModel block reference covered by this chunk. Trace: FR-18, QT-9.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    paperId: str
    version: int
    sectionId: str
    blockId: str
    blockType: str


class IndexRecord(BaseModel):
    """
    Shared per-chunk index document (one record per chunk; many chunks per paper, Q2=C full-text multi-chunk). Written by U1 (VectorIndexWriter) and read by U2 (HybridRetriever) over the SAME embedding space (vector-spec.md §2, §4). Card fields (FR-4) project to U2 ResultCardVM (dtos.md §1.1). Internal fields (vector, lexicalTerms, chunkId, section, categories — and the full `abstract`; the snippet, not the full abstract, is the exposed card field) are NOT exposed in external DTOs; the externally exposed card projection is the 6 fields in dtos.md §1.1 (SEC-9, per dtos.md §1.1/§4).
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    chunkId: str = Field(
        ...,
        description='Deterministic chunkId(paperId, ordinal). Serves as the index document ID (idempotent upsert key). Trace: BR-5, BR-9, PBT P2/P3.',
    )
    paperId: str = Field(
        ..., description='Version-less arXiv ID (canonical identifier). Trace: BR-3.'
    )
    version: int = Field(
        ..., description='arXiv version vN currently indexed. Trace: BR-3, BR-14.'
    )
    vector: list[float] = Field(
        ...,
        description='Chunk embedding (cosine space, inputType=search_document). 1024-dim per the FROZEN embedding contract (vector-spec.yaml). INTERNAL — not exposed in external DTOs (SEC-9). Trace: vector-spec.md §1.',
        max_length=1024,
        min_length=1024,
    )
    section: str = Field(
        ...,
        description='Source section of the chunk (abstract / body section). INTERNAL — not exposed in external DTOs (SEC-9). Trace: BR-5.',
    )
    lexicalTerms: str = Field(
        ...,
        description='Analyzed text field over title + abstract + chunk text — the single BM25 lexical field for hybrid retrieval (FR-2). U1 Corpus v1 intentionally does not split lexical fields or write per-field boosts; changing this field shape requires full reindex. INTERNAL — not exposed in external DTOs (SEC-9). Trace: BR-6.',
    )
    blockRefs: list[DocModelBlockRef] = Field(
        ...,
        description='Structured DocModel block refs covered by this chunk. Empty only for legacy/plain-text chunks. INTERNAL provenance used by QT-9 BlockRef validation; not searched or exposed externally. Trace: BR-C8, BR-C13, QT-9.',
    )
    title: str = Field(
        ...,
        description='Card field (FR-4). Paper title. Projects to ResultCardVM.title (dtos.md §1.1).',
    )
    authors: list[str] = Field(
        ...,
        description='Card field (FR-4). Authors. Projects to ResultCardVM.authors (dtos.md §1.1).',
    )
    year: int = Field(
        ...,
        description='Card field (FR-4). Publication year. Projects to ResultCardVM.year (dtos.md §1.1).',
    )
    arxivId: str = Field(
        ...,
        description='Card field (FR-4). Display arXiv ID (may include version). Projects to ResultCardVM.arxivId (dtos.md §1.1).',
    )
    abstract: str = Field(
        ...,
        description='Full abstract; source for abstractSnippet derivation. vector-spec.md §2 lists `abstract` in the card-field group as the snippet SOURCE, but per dtos.md §1.1 the full abstract is NOT itself exposed on the card — only the derived `abstractSnippet` is. Trace: FR-4, FR-5.',
    )
    abstractSnippet: str = Field(
        ...,
        description='Card field (FR-4). Card abstract snippet (derived from full abstract). Projects to ResultCardVM.abstractSnippet (dtos.md §1.1).',
    )
    arxivUrl: str = Field(
        ...,
        description='Card field (FR-4/FR-5). Resolvable real link (grounding — no fabrication). Projects to ResultCardVM.arxivUrl (dtos.md §1.1). U6.GroundingEnforcementHook validates at the response edge.',
    )
    categories: list[ArxivCategory] = Field(
        ...,
        description='arXiv categories (corpus slice cs.LG/cs.AI/cs.CL/cs.CV/stat.ML). INTERNAL — not exposed in external DTOs (SEC-9). Trace: C-6.',
    )
