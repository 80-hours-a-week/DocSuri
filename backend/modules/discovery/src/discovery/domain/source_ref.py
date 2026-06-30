"""Source-neutral (name, url) projection for a corpus record (Phase 2 / Q2).

Shared by the search card (``ResultAssembler``) and the detail header (``PaperMetadataService``)
so both surfaces agree on a paper's discovery source and its resolvable real link (FR-5)."""

from __future__ import annotations

from docsuri_shared.vector_spec import IndexRecord


def source_ref(record: IndexRecord) -> tuple[str, str]:
    """``(sourceName, resolvable url)``. The arXiv path keeps ``arxivUrl``; a non-arXiv record
    (Semantic Scholar / OpenAlex) uses its ``sourceProvenance.sourceUrl`` (or a DOI link),
    falling back to ``arxivUrl`` if neither is set. Legacy/arXiv-only records (no provenance)
    default to "arXiv" + arxivUrl. Only these two derived fields are exposed — the full
    ``sourceProvenance`` stays internal (SEC-9 / Q3)."""
    prov = record.sourceProvenance
    if prov is None or not prov.sourceName:
        return "arXiv", record.arxivUrl
    if prov.sourceName.lower() == "arxiv":
        return prov.sourceName, record.arxivUrl
    url = prov.sourceUrl or (f"https://doi.org/{prov.doi}" if prov.doi else record.arxivUrl)
    return prov.sourceName, url


def record_has_link(record: IndexRecord) -> bool:
    """A record is structurally grounded only if its source-neutral projection yields a
    resolvable http(s) link (FR-5). Scheme check is case-insensitive."""
    _, url = source_ref(record)
    return url.lower().startswith(("http://", "https://"))
