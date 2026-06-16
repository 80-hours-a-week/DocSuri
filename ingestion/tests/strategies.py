from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import strategies as st

from docsuri_ingestion.domain.models import ParsedPaper

paper_id_strategy = st.builds(
    lambda year, number: f"{year:04d}.{number:05d}",
    year=st.integers(min_value=2101, max_value=2501),
    number=st.integers(min_value=0, max_value=99999),
)

safe_text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=20,
    max_size=2000,
).filter(lambda value: bool(value.strip()))


@st.composite
def parsed_paper_strategy(draw):
    paper_id = draw(paper_id_strategy)
    version = draw(st.integers(min_value=1, max_value=20))
    abstract = draw(safe_text_strategy)
    body = draw(safe_text_strategy)
    return ParsedPaper(
        paper_id=paper_id,
        version=version,
        title="Property Based Ingestion Test",
        authors=("Ada Lovelace",),
        abstract=abstract,
        categories=("cs.LG",),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        year=2024,
        arxiv_url=f"https://arxiv.org/abs/{paper_id}v{version}",
        full_text=f"INTRODUCTION\n{body}",
        license_url="https://creativecommons.org/licenses/by/4.0/",
    )
