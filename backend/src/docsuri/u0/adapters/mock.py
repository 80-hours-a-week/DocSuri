"""결정적 mock 어댑터 — U0 §6 '실모델 OR 결정적 mock' 중 후자.

자격 증명·네트워크 없이 빌드 가능 정의 6항목을 시연한다.
모든 출력은 입력에 대해 결정적(같은 입력 → 같은 출력)이다.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode

from ..ports import (
    Completion,
    KoTranslation,
    Lang,
    OneHopResult,
    PaperHit,
    Persona,
    SearchFilters,
    Session,
    TelemetryEvent,
    Vector,
)

VECTOR_DIM = 32


def _deterministic_vector(text: str, lang: str) -> Vector:
    digest = hashlib.sha256(f"{lang}:{text}".encode()).digest()
    seed = list(digest) + list(hashlib.sha256(digest).digest())
    return [(b - 127.5) / 127.5 for b in seed[:VECTOR_DIM]]


def _cosine(a: Vector, b: Vector) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class DeterministicEmbedding:
    """EmbeddingPort mock — 해시 기반 벡터 + 코퍼스 fixture 검색(필터 지원)."""

    def __init__(self, corpus_path: Path) -> None:
        raw = json.loads(corpus_path.read_text(encoding="utf-8"))
        self._papers: list[dict] = raw["papers"]
        self._vectors: list[Vector] = [
            _deterministic_vector(p["title"], "en") for p in self._papers
        ]

    def embed(self, text: str, lang: Lang) -> Vector:
        return _deterministic_vector(text, lang)

    def search(
        self, vec: Vector, k: int, filters: SearchFilters | None = None
    ) -> list[PaperHit]:
        scored = []
        for paper, pvec in zip(self._papers, self._vectors):
            if filters:
                if filters.year_min is not None and paper["year"] < filters.year_min:
                    continue
                if filters.year_max is not None and paper["year"] > filters.year_max:
                    continue
                if filters.field_tags and not set(filters.field_tags) & set(
                    paper["field_tags"]
                ):
                    continue
            scored.append((_cosine(vec, pvec), paper))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            PaperHit(similarity=round(score, 4), **paper)
            for score, paper in scored[:k]
        ]


_PRO_BODY = (
    "연구 질문: 입력 프롬프트가 요구한 분석 대상을 전문 어휘를 보존한 채 정리합니다. "
    "방법: retrieval-augmented generation(검색 증강 생성)과 transformer 기반 "
    "attention(어텐션) 구조를 한국어 표현과 병기해 검토했습니다. "
    "결과: 의미 유사도 상위 결과의 핵심 기여와 한계를 구분해 제시할 수 있음을 확인했습니다. "
    "한계: 본 출력은 결정적 mock 응답이므로 실제 모델 추론을 대체하지 않습니다."
)

_UNDERGRAD_BODY = (
    "질문을 쉽게 풀어 볼게요. 입력하신 내용이 무엇을 묻는지 차근차근 살펴보는 답변이에요. "
    "방법은 문장의 의미를 숫자 목록(벡터)으로 바꾼 뒤 비슷한 논문을 찾는 방식이에요. "
    "결과적으로 어려운 용어를 풀어 쓰면 처음 공부하는 사람도 핵심을 잡을 수 있다는 점을 "
    "확인했어요. 다만 이 답변은 시연용 가짜 응답이라서 실제 인공지능 모델의 답과는 달라요."
)


class CannedKoreanLlm:
    """LlmPort mock — 페르소나별 톤이 다른 한국어 200~400자 응답 (U0 §6)."""

    def __init__(self, model_id: str = "mock-llm") -> None:
        self._model_id = model_id

    def complete(self, prompt: str, persona: Persona, budget_tokens: int) -> Completion:
        tag = hashlib.sha256(f"{persona}:{prompt}".encode()).hexdigest()[:6]
        body = _PRO_BODY if persona == "pro" else _UNDERGRAD_BODY
        prefix = (
            f"[전문 모드·응답 {tag}] " if persona == "pro" else f"[학부 모드·응답 {tag}] "
        )
        text = (prefix + body)[:400]
        if len(text) < 200:  # 방어적 패딩 — 계약은 200~400자
            text = (text + " 추가 설명: 동일 입력에는 항상 동일 응답이 반환됩니다.")[:400]
        return Completion(
            text=text,
            tokens_in=max(1, len(prompt) // 3),
            tokens_out=max(1, len(text) // 3),
            model_id=self._model_id,
        )


class InMemoryTtlCache:
    """CachePort mock — 시간 주입식이라 'set → 25h 후 miss'(U0 §6)를 시뮬레이션 가능."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._store: dict[str, tuple[bytes, float]] = {}

    def get(self, key: str) -> bytes | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: bytes, ttl_s: int) -> None:
        self._store[key] = (value, self._clock() + ttl_s)


class ListTelemetry:
    """Telemetry mock — 이벤트를 메모리에 모으고 JSONL로 출력(옵션)."""

    def __init__(self, echo: bool = False) -> None:
        self.events: list[dict] = []
        self._echo = echo

    def record(self, event: TelemetryEvent) -> None:
        payload = event.model_dump()
        self.events.append(payload)
        if self._echo:
            print(json.dumps(payload, ensure_ascii=False))


class FixtureGlossary:
    """Glossary mock — data/glossary_seed.json 50개 시드 (A6)."""

    def __init__(self, glossary_path: Path) -> None:
        raw = json.loads(glossary_path.read_text(encoding="utf-8"))
        self._entries = {e["term"].lower(): e for e in raw["entries"]}

    def lookup(self, term: str) -> KoTranslation | None:
        entry = self._entries.get(term.lower())
        return KoTranslation(**entry) if entry else None


class FixtureCitation:
    """CitationApi mock — 코퍼스에서 결정적으로 선택한 1-hop fixture."""

    OUTGOING_N = 3
    INCOMING_N = 5

    def __init__(self, corpus_path: Path) -> None:
        raw = json.loads(corpus_path.read_text(encoding="utf-8"))
        self._papers: list[dict] = raw["papers"]

    def _pick(self, paper_id: str, salt: str, n: int) -> list[PaperHit]:
        digest = hashlib.sha256(f"{salt}:{paper_id}".encode()).digest()
        picks = []
        for i in range(n):
            idx = digest[i] % len(self._papers)
            candidate = self._papers[idx]
            if candidate["id"] != paper_id:
                picks.append(PaperHit(**candidate))
        return picks

    def one_hop(self, paper_id: str) -> OneHopResult:
        return OneHopResult(
            outgoing=self._pick(paper_id, "out", self.OUTGOING_N),
            incoming=self._pick(paper_id, "in", self.INCOMING_N),
        )


class AnonymousSession:
    """SessionPort mock — NFR-SEC-01 비로그인 익명 세션 + 필터 URL 직렬화."""

    def __init__(self, persona_mode: Persona = "pro") -> None:
        self._anon_id = str(uuid.uuid4())
        self._persona: Persona = persona_mode
        self._filters_url = ""

    def session(self) -> Session:
        return Session(
            anon_id=self._anon_id,
            persona_mode=self._persona,
            filters_url=self._filters_url,
        )

    def serialize_filters(self, filters: SearchFilters) -> str:
        params: dict[str, str] = {}
        if filters.year_min is not None:
            params["year_min"] = str(filters.year_min)
        if filters.year_max is not None:
            params["year_max"] = str(filters.year_max)
        if filters.field_tags:
            params["tags"] = ",".join(filters.field_tags)
        self._filters_url = urlencode(params)
        return self._filters_url

    def restore_filters(self, url_query: str) -> SearchFilters:
        parsed = parse_qs(url_query)
        return SearchFilters(
            year_min=int(parsed["year_min"][0]) if "year_min" in parsed else None,
            year_max=int(parsed["year_max"][0]) if "year_max" in parsed else None,
            field_tags=parsed["tags"][0].split(",") if "tags" in parsed else [],
        )
