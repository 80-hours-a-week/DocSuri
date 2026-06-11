from __future__ import annotations

import pytest

from docsuri.u2 import (
    DocumentIngestor,
    DocumentSource,
    FigureContext,
    FigureExplainer,
    ReadabilityValidator,
    SectionToggleController,
    SelectionTranslator,
    SummaryEngine,
)
from docsuri.u0.adapters.mock import InMemoryTtlCache, ListTelemetry
from docsuri.u0.ports import Completion, KoTranslation
from docsuri.u2.document_ingestor import _parse_arxiv_response


SAMPLE_TEXT = """
Transformer attention models answer whether retrieval-augmented generation can
reduce hallucination in large language model summarization. The method compares
MLM pre-training with a baseline and uses y = f(x) to score semantic similarity.
Results improve benchmark accuracy, but the limitation is that the corpus is
small and the evaluation uses only abstracts.
"""


@pytest.fixture()
def sample_paper():
    return DocumentIngestor().ingest(
        DocumentSource(
            kind="raw_text",
            paper_id="paper:u2-sample",
            title="Transformer Attention for RAG Summaries",
            value=SAMPLE_TEXT,
        )
    )


def test_u2_document_ingestor_raw_text_shape(sample_paper):
    assert sample_paper.paper_id == "paper:u2-sample"
    assert sample_paper.title == "Transformer Attention for RAG Summaries"
    assert sample_paper.sections[0].title == "본문"
    assert "Transformer attention" in sample_paper.plain_text()


def test_u2_document_ingestor_rejects_empty_and_non_arxiv_url():
    ingestor = DocumentIngestor()

    with pytest.raises(ValueError, match="비어"):
        ingestor.ingest(DocumentSource(kind="raw_text", value="   "))
    with pytest.raises(ValueError, match="arXiv"):
        ingestor.ingest(DocumentSource(kind="url", value="https://example.test/paper"))
    with pytest.raises(ValueError, match="XML"):
        _parse_arxiv_response("<not-xml", fallback_id="0000.00000")


def test_u2_summary_engine_pro_and_undergrad_modes_differ(u0, sample_paper):
    engine = SummaryEngine(u0.llm, u0.cache, u0.glossary, u0.telemetry)

    pro = engine.summarize(sample_paper, "pro")
    undergrad = engine.summarize(sample_paper, "undergrad")

    assert pro.mode == "pro"
    assert undergrad.mode == "undergrad"
    assert pro.sections != undergrad.sections
    assert all(
        getattr(pro.sections, key)
        for key in ("question", "method", "result", "limit")
    )
    assert all(
        getattr(undergrad.sections, key)
        for key in ("question", "method", "result", "limit")
    )
    assert {hit.term.lower() for hit in pro.vocab_explanations} >= {
        "transformer",
        "attention",
    }
    assert pro.cost.tokens_in > 0 and pro.cost.tokens_out > 0
    assert undergrad.cost.tokens_in > 0 and undergrad.cost.tokens_out > 0


def test_u2_summary_cache_uses_7_day_key(u0, sample_paper):
    engine = SummaryEngine(u0.llm, u0.cache, u0.glossary, u0.telemetry)
    first = engine.summarize(sample_paper, "pro")
    second = engine.summarize(sample_paper, "pro")

    assert second == first
    assert u0.telemetry.events[-1]["op"] == "summarize"
    assert u0.telemetry.events[-1]["cache_hit"] is True


def test_u2_summary_cache_expires_after_7_days(u0, sample_paper, fake_clock):
    cache = InMemoryTtlCache(clock=fake_clock)
    telemetry = ListTelemetry()
    engine = SummaryEngine(u0.llm, cache, u0.glossary, telemetry)

    first = engine.summarize(sample_paper, "pro")
    second = engine.summarize(sample_paper, "pro")
    fake_clock.advance(7 * 24 * 3600 + 1)
    third = engine.summarize(sample_paper, "pro")

    assert second == first
    assert third == first
    assert [event["cache_hit"] for event in telemetry.events] == [False, True, False]


def test_u2_undergrad_readability_report(sample_paper, u0):
    engine = SummaryEngine(u0.llm, u0.cache, u0.glossary, u0.telemetry)
    result = engine.summarize(sample_paper, "undergrad")
    report = ReadabilityValidator().validate(result.sections.combined_text(), "undergrad")

    assert report.metrics.sentence_count >= 1
    assert report.metrics.average_eojeol_per_sentence <= 22
    assert report.passed


def test_u2_undergrad_retry_preserves_aids(u0, sample_paper):
    class RetryLlm:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, prompt: str, persona: str, budget_tokens: int) -> Completion:
            self.calls += 1
            if self.calls == 1:
                long_sentence = " ".join(["어려운설명"] * 30)
                return Completion(
                    text=(
                        f"연구 질문: {long_sentence}. 방법: {long_sentence}. "
                        f"결과: {long_sentence}. 한계: {long_sentence}."
                    ),
                    tokens_in=10,
                    tokens_out=120,
                    model_id="retry-test",
                )
            return Completion(
                text="연구 질문: 쉽게 묻습니다. 방법: 짧게 풉니다. 결과: 좋아졌습니다. 한계: 더 봐야 합니다.",
                tokens_in=8,
                tokens_out=20,
                model_id="retry-test",
            )

    engine = SummaryEngine(
        RetryLlm(),  # type: ignore[arg-type]
        InMemoryTtlCache(),
        u0.glossary,
        ListTelemetry(),
    )

    result = engine.summarize(sample_paper, "undergrad")

    assert "MLM(마스크 언어 모델)" in result.sections.question
    assert "수식 해석" in result.sections.method
    assert result.cost.tokens_in == 18
    assert result.cost.tokens_out == 140
    assert engine.last_readability_report is not None
    assert engine.last_readability_report.passed


def test_u2_undergrad_failed_retry_is_not_cached(u0, sample_paper):
    class AlwaysHardLlm:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, prompt: str, persona: str, budget_tokens: int) -> Completion:
            self.calls += 1
            long_sentence = " ".join(["어려운설명"] * 30)
            return Completion(
                text=(
                    f"연구 질문: {long_sentence}. 방법: {long_sentence}. "
                    f"결과: {long_sentence}. 한계: {long_sentence}."
                ),
                tokens_in=10,
                tokens_out=120,
                model_id="always-hard-test",
            )

    llm = AlwaysHardLlm()
    engine = SummaryEngine(
        llm,  # type: ignore[arg-type]
        InMemoryTtlCache(),
        u0.glossary,
        ListTelemetry(),
    )

    engine.summarize(sample_paper, "undergrad")
    first_report = engine.last_readability_report
    engine.summarize(sample_paper, "undergrad")

    assert first_report is not None
    assert not first_report.passed
    assert llm.calls == 4


def test_u2_glossary_scan_uses_limited_compressed_text(u0):
    class CountingGlossary:
        def __init__(self) -> None:
            self.calls = 0

        def lookup(self, term: str) -> KoTranslation | None:
            self.calls += 1
            return u0.glossary.lookup(term)

    text = " ".join(f"term{i}" for i in range(2000))
    text += " transformer attention retrieval-augmented generation"
    paper = DocumentIngestor().ingest(
        DocumentSource(kind="raw_text", paper_id="paper:glossary-limit", value=text)
    )
    glossary = CountingGlossary()

    engine = SummaryEngine(u0.llm, InMemoryTtlCache(), glossary, ListTelemetry())
    result = engine.summarize(paper, "pro")

    assert glossary.calls <= 256
    assert result.vocab_explanations
    assert {hit.term.lower() for hit in result.vocab_explanations} >= {
        "transformer",
        "attention",
    }
    assert all(hit.term in result.sections.combined_text() or hit.term in paper.plain_text() for hit in result.vocab_explanations)


def test_u2_selection_translator_desktop_and_mobile(u0):
    translator = SelectionTranslator(u0.llm, u0.glossary, u0.telemetry)
    source = "Transformer attention improves semantic similarity for retrieval-augmented generation."

    desktop_selection = translator.select(source, 0, len(source), "desktop")
    mobile_selection = translator.select(source, 0, len(source), "mobile", long_press_ms=500)
    desktop = translator.translate(desktop_selection)
    mobile = translator.translate(mobile_selection)

    assert desktop.source_excerpt == source
    assert mobile.source_excerpt == source
    assert "한국어" in desktop.target_text or "학부 모드" in desktop.target_text
    assert {hit.term.lower() for hit in desktop.glossary_hits} >= {
        "transformer",
        "attention",
    }
    assert u0.telemetry.events[-1]["op"] == "translate"


def test_u2_selection_translator_rejects_short_mobile_press(u0):
    translator = SelectionTranslator(u0.llm, u0.glossary, u0.telemetry)

    with pytest.raises(ValueError, match="500ms"):
        translator.select("A paragraph", 0, 5, "mobile", long_press_ms=300)


def test_u2_figure_explainer_checks_touch_target(u0):
    explainer = FigureExplainer(u0.llm, u0.telemetry)
    text = explainer.explain(
        FigureContext(
            caption="Table 1 compares baseline and transformer results.",
            context="The table summarizes benchmark accuracy.",
        )
    )

    assert text
    assert u0.telemetry.events[-1]["op"] == "figure_explain"
    with pytest.raises(ValueError, match="44 CSS px"):
        explainer.explain(FigureContext(caption="bad target", touch_target_width_css_px=20))


def test_u2_section_toggle_persists_within_session(u0, sample_paper):
    engine = SummaryEngine(u0.llm, u0.cache, u0.glossary, u0.telemetry)
    summary = engine.summarize(sample_paper, "pro")
    controller = SectionToggleController(u0.session)

    state = controller.toggle("method")
    defaults = controller.defaults_for(summary)

    assert state.collapsed["method"] is True
    assert defaults.collapsed["method"] is True
