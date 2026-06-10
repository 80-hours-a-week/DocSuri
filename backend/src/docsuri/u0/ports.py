"""U0 Foundation 포트 계약.

단일 진실: aidlc-docs/design-artifacts/component-model.md §2 (동결).
시그니처 변경은 handoff.md §6 / U0 §8 변경 정책을 따른다 — 이 파일에서
임의로 필드를 추가·제거하지 말 것.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

Vector = list[float]
Lang = Literal["ko", "en"]
Persona = Literal["pro", "undergrad"]


class PaperHit(BaseModel):
    """EmbeddingPort.search 결과 1건 — component-model §2.1 스키마."""

    id: str
    title: str
    authors: list[str]
    year: int
    citations: int
    similarity: float = 0.0
    field_tags: list[str] = Field(default_factory=list)
    abstract_len: int = 0


class SearchFilters(BaseModel):
    """US-DISC-02 연도·분야 필터."""

    year_min: int | None = None
    year_max: int | None = None
    field_tags: list[str] = Field(default_factory=list)


class Completion(BaseModel):
    """LlmPort.complete 결과."""

    text: str
    tokens_in: int
    tokens_out: int
    model_id: str


class Session(BaseModel):
    """SessionPort.session 결과 — NFR-SEC-01 비로그인 익명 세션."""

    anon_id: str
    persona_mode: Persona
    filters_url: str = ""


class TelemetryEvent(BaseModel):
    """Telemetry.record 입력 — NFR-OBS-01·02 키."""

    op: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    cache_hit: bool = False
    persona: Persona | None = None


class KoTranslation(BaseModel):
    """Glossary.lookup 결과 — NFR-LANG-03 정규 번역."""

    term: str
    ko: str
    note: str = ""


class OneHopResult(BaseModel):
    """CitationApi.oneHop 결과 — U4가 사용."""

    outgoing: list[PaperHit]
    incoming: list[PaperHit]


class EmbeddingPort(Protocol):
    def embed(self, text: str, lang: Lang) -> Vector: ...

    def search(
        self, vec: Vector, k: int, filters: SearchFilters | None = None
    ) -> list[PaperHit]: ...


class LlmPort(Protocol):
    def complete(self, prompt: str, persona: Persona, budget_tokens: int) -> Completion: ...


class CachePort(Protocol):
    def get(self, key: str) -> bytes | None: ...

    def set(self, key: str, value: bytes, ttl_s: int) -> None: ...


class SessionPort(Protocol):
    def session(self) -> Session: ...

    def serialize_filters(self, filters: SearchFilters) -> str: ...

    def restore_filters(self, url_query: str) -> SearchFilters: ...


class Telemetry(Protocol):
    def record(self, event: TelemetryEvent) -> None: ...


class Glossary(Protocol):
    def lookup(self, term: str) -> KoTranslation | None: ...


class CitationApi(Protocol):
    def one_hop(self, paper_id: str) -> OneHopResult: ...
