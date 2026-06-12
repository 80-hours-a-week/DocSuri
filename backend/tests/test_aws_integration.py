"""U0 AWS 통합 테스트 — 실제 AWS(리전=설정값 — ADR-D3 재검토 후 서울 ap-northeast-2)에 대고 aws.py 어댑터를 검증한다.

ADR §14 "환경 구축 시 검증 항목"의 실측 게이트. mock 모드(자격 증명 불필요)가
증명하는 것은 *포트 계약*뿐이고, 아래 항목은 mock이 구조적으로 증명할 수 없다 —
실제 AWS 호출로만 닫힌다.

  Tier A (자격 증명만) ……… 스파이크 ① — 인프라 프로비저닝 없이 실행
      embed 차원·complete 한국어 출력 = Bedrock 모델 ID·global CRIS·boto3 응답 파싱.
      즉 "aws.py가 애초에 맞게 짜였나"를 보는 최고가치 체크 (현재 미검증 코드).
  Tier B (DOCSURI_IT_SEEDED=1) … 단계 ② — 테이블·S3 Vectors 인덱스·시드가 선 적재돼야 함
      search 메타데이터 필터 문법·DynamoDB 캐시 TTL·용어집·비용 누적.

실행:
    # Tier A — 자격 증명만으로 모델 가용성·어댑터 정합 검증 (ADR-D2/D3/D4)
    DOCSURI_ADAPTER_MODE=aws AWS_PROFILE=<프로필> uv run pytest tests/test_aws_integration.py -v -s

    # Tier B 포함 — IaC로 테이블·인덱스·시드를 올린 뒤
    DOCSURI_ADAPTER_MODE=aws DOCSURI_IT_SEEDED=1 AWS_PROFILE=<프로필> \
        uv run pytest tests/test_aws_integration.py -v -s

`-s`를 붙이면 LLM 응답·지연 수치가 출력돼 톤·성능을 사람이 직접 판독할 수 있다.

게이트: DOCSURI_ADAPTER_MODE=aws 가 아니거나 자격 증명이 없으면 모듈 전체가 skip된다 —
mock CI(기본)는 전혀 영향받지 않는다. 단, 이 파일은 aws 모드 전제라 mock 단위 테스트와
한 번에 돌리면 conftest의 `u0` 픽스처(mock 단언)가 깨지므로, 파일을 지정해 단독 실행한다.
"""

from __future__ import annotations

import os
import time
import warnings

import pytest

from docsuri.u0.adapters import build_u0
from docsuri.u0.config import load_settings
from docsuri.u0.cost_guard import CostGuard, InMemoryCostStore
from docsuri.u0.llm_gateway import LlmGateway
from docsuri.u0.ports import SearchFilters

# ─────────────────────────────────────────────────────────────────────────────
# 게이트 — 자격 증명/모드가 없으면 모듈 전체 skip
# ─────────────────────────────────────────────────────────────────────────────


def _aws_enabled() -> tuple[bool, str]:
    if os.environ.get("DOCSURI_ADAPTER_MODE", "mock").lower() != "aws":
        return False, "DOCSURI_ADAPTER_MODE=aws 아님 — mock 기본 모드에서는 통합 테스트 skip"
    try:
        import boto3

        if boto3.Session().get_credentials() is None:
            return False, "AWS 자격 증명을 찾을 수 없음 (AWS_PROFILE/환경변수 확인)"
    except Exception as exc:  # noqa: BLE001 — 환경 점검용, 어떤 실패든 skip 사유로 환원
        return False, f"boto3 자격 증명 확인 실패: {exc}"
    return True, ""


_enabled, _skip_reason = _aws_enabled()
pytestmark = pytest.mark.skipif(not _enabled, reason=_skip_reason)

_SEEDED = os.environ.get("DOCSURI_IT_SEEDED", "").lower() in ("1", "true", "yes")
requires_seeded = pytest.mark.skipif(
    not _SEEDED,
    reason="DOCSURI_IT_SEEDED=1 아님 — DynamoDB 테이블·S3 Vectors 인덱스·시드 미프로비저닝(단계 ②)",
)


# ─────────────────────────────────────────────────────────────────────────────
# 결정 지점 (팀 판단) — mock이 못 거르는 두 "소프트" 검증의 합격 기준
#
#   이 두 값은 *경험적 품질*의 합격선이라 코드가 정답을 줄 수 없다. ADR-D4(Haiku
#   KKL 4급 톤·UX-01·02)와 NFR-PERF/ADR-D9(지연)의 실측 기준을 팀이 정한다.
#   기본값은 "비었거나 깨지지 않았다" 수준의 보수적 가드 — 회귀 탐지가 목적이고,
#   톤·격조의 *질*은 `-s` 출력으로 사람이 판독한다.
# ─────────────────────────────────────────────────────────────────────────────

# ADR-D4: 한국어 응답 길이 창. 너무 좁으면 플레이키, 너무 넓으면 회귀를 못 잡는다.
# (U0 §6 시연은 budget≈2000에서 261자. 여기선 budget·프롬프트가 달라 느슨히 둔다.)
KO_LEN_MIN, KO_LEN_MAX = 80, 2000

# NFR-PERF: 로컬에서 잰 Bedrock *왕복* 지연의 soft 상한(ms). 초과해도 실패가 아니라
# 경고만 낸다 — Lambda 콜드스타트(ADR-D9)는 배포 환경에서 따로 실측할 별개 변수다.
LATENCY_SOFT_BUDGET_MS = 8_000


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def assert_acceptable_completion(text: str, persona: str) -> None:
    """Haiku 4.5 한국어 응답이 페르소나 톤 기준을 만족하는지 검증한다 (ADR-D4 / UX-01·02).

    기계적으로 단언 가능한 것(한국어 우세·길이)과 사람이 판독해야 하는 것(KKL 4급 격조,
    pro의 전문어 보존 vs undergrad의 평이성)의 경계 — 그 선을 어디에 긋느냐가 이 함수의
    설계 결정이다.

    TODO(팀, 학습 기여): 합격 기준을 정한다. 예시 방향:
      · pro    → 영문 전문어 병기를 허용/기대 (예: "어텐션(attention)" 패턴 존재)
      · undergrad → 한자어·수식 비율 상한, 문장 길이 상한 등 평이성 지표
    엄격할수록 회귀를 잘 잡지만 모델 비결정성으로 플레이키해진다 — 트레이드오프.
    아래는 보수적 기본값(언어·길이만). persona별 분기를 추가할 자리.
    """
    assert _has_hangul(text), f"한국어 응답이 아님 (persona={persona}): {text[:80]!r}"
    assert KO_LEN_MIN <= len(text) <= KO_LEN_MAX, (
        f"길이 창[{KO_LEN_MIN},{KO_LEN_MAX}] 이탈 — {len(text)}자 (persona={persona}): {text[:80]!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 픽스처
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def settings():
    s = load_settings()
    assert s.adapter_mode == "aws"  # 게이트가 보장하지만 명시적으로 재확인
    return s


@pytest.fixture(scope="module")
def aws_u0(settings):
    """실제 AWS 포트 묶음 — build_u0가 adapter_mode=aws면 aws.py 어댑터를 조립한다.

    boto3 client/resource 생성은 지연(lazy)이라, 실제 호출이 일어나는 테스트만
    네트워크를 탄다 — Tier A에서 테이블이 없어도 fixture 구성은 실패하지 않는다.
    """
    return build_u0(settings)


@pytest.fixture(scope="module")
def bedrock_llm(settings):
    """Tier A용 LLM 게이트웨이 — 실제 BedrockLlm + 인메모리 CostGuard.

    프로덕션 조립(build_u0)은 CostGuard를 DynamoDB(`docsuri-cost`)에 묶지만, 그 테이블은
    Tier B 인프라다. CostGuard는 호출 *전* 월 누적을 읽으므로(ADR-D4 인라인 하드스톱),
    테이블이 없으면 Bedrock에 닿기도 전에 ResourceNotFoundException으로 실패한다.
    여기서는 *모델*(Haiku 4.5)만 검증하면 되므로 비용 저장소를 InMemoryCostStore로 바꿔
    DynamoDB 의존을 끊는다 — 게이트웨이 래핑(예산 검사·텔레메트리)은 그대로 유지한다.
    cost_store 자체의 실DB 검증은 Tier B `test_cost_store_roundtrip`이 따로 닫는다.
    """
    from docsuri.u0.adapters import mock
    from docsuri.u0.adapters.aws import BedrockLlm

    guard = CostGuard(
        store=InMemoryCostStore(),
        monthly_cap_usd=settings.cost_monthly_cap_usd,
        price_in_per_mtok=settings.llm_price_in_per_mtok,
        price_out_per_mtok=settings.llm_price_out_per_mtok,
    )
    return LlmGateway(BedrockLlm(settings), guard, mock.ListTelemetry(echo=False))


# ─────────────────────────────────────────────────────────────────────────────
# Tier A — 자격 증명만으로 실행 (스파이크 ①: 모델 가용성 + aws.py 어댑터 정합)
# ─────────────────────────────────────────────────────────────────────────────


def test_embed_returns_1024d_vector(aws_u0):
    """ADR-D3(재검토): Titan Text Embeddings V2 = 1024차원. aws.py embed 응답 파싱(inputText→embedding)."""
    vec = aws_u0.embedding.embed("transformer attention mechanism", lang="en")
    assert isinstance(vec, list) and len(vec) == 1024, f"기대 1024차원, 실제 {len(vec)}"
    assert all(isinstance(x, float) for x in vec[:8])


def test_embed_korean_query(aws_u0):
    """DISC-04: 한국어 직접 질의도 임베딩 가능 — Titan V2 다국어(ADR-D3 재검토)."""
    vec = aws_u0.embedding.embed("트랜스포머 어텐션 메커니즘", lang="ko")
    assert len(vec) == 1024


def test_complete_korean_pro(bedrock_llm):
    """ADR-D4: Haiku 4.5 global CRIS — Converse 호출·usage 파싱·한국어 출력.

    인메모리 비용 게이트웨이 사용 — DynamoDB 없이 *모델*만 검증 (bedrock_llm 픽스처 참조).
    """
    c = bedrock_llm.complete(
        "어텐션 메커니즘이 무엇인지 한 문단으로 설명해줘.",
        persona="pro",
        budget_tokens=600,
    )
    assert c.tokens_in > 0 and c.tokens_out > 0, "usage 파싱 실패"
    assert "claude-haiku" in c.model_id, f"모델 ID 예상 밖: {c.model_id}"
    assert_acceptable_completion(c.text, "pro")
    print(f"\n[pro / KKL 톤 판독용]\n{c.text}\n")  # -s 로 사람이 ADR-D4 톤 확인


def test_complete_personas_differ(bedrock_llm):
    """UX-01·02: 페르소나별 톤 분기가 실제 모델에서도 갈리는지 (U0 §6 보장의 실측판)."""
    prompt = "BERT가 무엇인지 설명해줘."
    pro = bedrock_llm.complete(prompt, persona="pro", budget_tokens=600)
    under = bedrock_llm.complete(prompt, persona="undergrad", budget_tokens=600)
    assert_acceptable_completion(pro.text, "pro")
    assert_acceptable_completion(under.text, "undergrad")
    assert pro.text != under.text, "두 페르소나 응답이 동일 — 톤 분기 미작동"
    print(f"\n[pro]\n{pro.text}\n\n[undergrad]\n{under.text}\n")


def test_bedrock_roundtrip_latency(aws_u0, bedrock_llm):
    """NFR-PERF 바닥값 실측 — Bedrock 왕복 지연.

    soft 검증: 초과해도 실패가 아니라 경고. Lambda 콜드스타트(ADR-D9)는 *배포 환경*에서
    따로 재야 하는 별개 변수이므로 여기서 단언하지 않는다 — 여긴 그 합산의 바닥값만 잰다.
    embed는 게이트웨이를 거치지 않아 aws_u0, llm은 인메모리 게이트웨이(bedrock_llm)로 잰다.
    """
    t0 = time.perf_counter()
    aws_u0.embedding.embed("latency probe", lang="en")
    embed_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    bedrock_llm.complete("한 문장으로 답해줘: 딥러닝이란?", persona="pro", budget_tokens=200)
    llm_ms = (time.perf_counter() - t1) * 1000

    total = embed_ms + llm_ms
    print(
        f"\n[latency] embed={embed_ms:.0f}ms  llm={llm_ms:.0f}ms  "
        f"합={total:.0f}ms (soft budget {LATENCY_SOFT_BUDGET_MS}ms)"
    )
    if total > LATENCY_SOFT_BUDGET_MS:
        warnings.warn(
            f"Bedrock 왕복 {total:.0f}ms > soft budget {LATENCY_SOFT_BUDGET_MS}ms — "
            f"배포 콜드스타트 합산 시 NFR-PERF(P50<3s) 점검 필요",
            stacklevel=2,
        )


def test_citation_one_hop_live(aws_u0):
    """R4: Semantic Scholar 1-hop 실호출. 실패 시 빈 결과 폴백도 *정상 동작*으로 합격.

    DynamoDB 의존을 분리하려 in-memory 캐시를 주입 — 외부 API 거동만 본다 (Tier A).
    """
    from docsuri.u0.adapters import mock
    from docsuri.u0.adapters.aws import SemanticScholarCitation

    citation = SemanticScholarCitation(cache=mock.InMemoryTtlCache())
    result = citation.one_hop("1706.03762")  # Attention Is All You Need
    assert hasattr(result, "outgoing") and hasattr(result, "incoming")
    print(f"\n[citation] outgoing={len(result.outgoing)} incoming={len(result.incoming)}")
    # 비어있지 않음을 강제하지 않는다 — R4 폴백(빈 결과)도 설계상 정상.


# ─────────────────────────────────────────────────────────────────────────────
# Tier B — 프로비저닝 후 (단계 ②: DOCSURI_IT_SEEDED=1)
# ─────────────────────────────────────────────────────────────────────────────


@requires_seeded
def test_search_year_and_field_filter(aws_u0):
    """ADR-D2: S3 Vectors 메타데이터 필터 문법($gte/$lte/$and/$in) 실표현력 — US-DISC-02.

    test_ports_unit.py:test_search_filters_year_and_tags 의 실인덱스판.
    aws.py:_to_s3v_filter 가 추정으로 짠 필터 DSL이 실제로 통하는지 검증한다.
    """
    vec = aws_u0.embedding.embed("neural network", lang="en")
    all_hits = aws_u0.embedding.search(vec, k=20)
    assert all_hits, "시드 코퍼스 검색 결과 비어있음 — S3 Vectors 인덱스 적재 확인"

    year_cut = max(h.year for h in all_hits) - 1
    filtered = aws_u0.embedding.search(vec, k=20, filters=SearchFilters(year_min=year_cut))
    assert filtered, "연도 필터 결과가 비면 안 됨"
    assert all(h.year >= year_cut for h in filtered)  # $gte 검증

    tag = all_hits[0].field_tags[0]
    tagged = aws_u0.embedding.search(vec, k=20, filters=SearchFilters(field_tags=[tag]))
    assert tagged and all(tag in h.field_tags for h in tagged)  # $in 검증


@requires_seeded
def test_dynamo_cache_ttl_roundtrip(aws_u0):
    """ADR §12: DynamoDB 캐시 바이트 왕복 + 읽기 시 만료 재검사(TTL 지연 삭제 보완).

    ttl 음수로 set → 이미 만료된 항목 기록 → get이 None을 반환하는 read-time recheck 경로
    (aws.py:148 `expires_at <= time.time()`)를 직접 친다.
    """
    key = "_it:cache-probe"
    aws_u0.cache.set(key, b"docsuri-it", ttl_s=60)
    assert aws_u0.cache.get(key) == b"docsuri-it"

    aws_u0.cache.set(key, b"stale", ttl_s=-1)
    assert aws_u0.cache.get(key) is None  # 읽기 시 만료 재검사


@requires_seeded
def test_glossary_lookup(aws_u0):
    """ADR §12: DynamoDB 용어집 시드(50행) 적중/미스 — NFR-LANG-03 (소문자 키 정규화)."""
    hit = aws_u0.glossary.lookup("transformer")
    assert hit is not None and hit.ko, "용어집 시드 미적재 또는 키 정규화 불일치"
    assert aws_u0.glossary.lookup("nonexistent-term-xyz") is None


@requires_seeded
def test_cost_store_roundtrip(settings):
    """ADR-D9 결과4: DynamoDB 비용 누적의 Decimal 처리 + ADD 원자성.

    실제 월 키("%Y-%m")를 오염시키면 CostGuard 누적이 틀어지므로 센티넬 키를 쓴다 —
    이 행은 프로덕션 CostGuard가 읽지 않는다. (어댑터에 delete가 없어 행은 잔존하나 무해.)
    """
    from docsuri.u0.adapters.aws import DynamoCostStore

    store = DynamoCostStore(settings)
    sentinel = "_it_sentinel"
    before = store.total(sentinel)
    after = store.add(sentinel, 0.01)
    assert after == pytest.approx(before + 0.01, abs=1e-6)
    assert store.total(sentinel) == pytest.approx(after, abs=1e-6)
