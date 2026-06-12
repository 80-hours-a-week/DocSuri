"""시나리오 1 테스트: 차별성 분석 → NoveltyReport 생성.

Given: 연구자가 연구 주제 초안(200~500자) 입력
When:  "차별성 분석" 요청
Then:  유사 논문 5편 + 공통점/차이점 + overall novelty 평가

실행: cd backend && DOCSURI_ADAPTER_MODE=aws pyenv exec python3 scripts/scenario1_test.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docsuri.u0.adapters.aws import BedrockEmbedding, BedrockLlm
from docsuri.u0.config import load_settings
from docsuri.u0.ports import PaperHit, Persona

# ── DTO ──────────────────────────────────────────────────────────────────────

@dataclass
class SimilarPaperNote:
    paper: PaperHit
    common: str   # 공통점 1줄
    diff: str     # 차이점 1줄


@dataclass
class GapProposal:
    title: str
    body: str
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class NoveltyReport:
    user_topic: str
    similar_papers: list[SimilarPaperNote]
    overall_novelty: str
    gap_proposals: list[GapProposal]
    persona_mode: Persona


# ── 토큰 최적화 ──────────────────────────────────────────────────────────────

# 프롬프트에 넣는 텍스트를 max_chars로 압축 (청크 단위 압축)
_TOPIC_MAX_CHARS = 300   # 연구 주제 최대 300자
_NOTE_MAX_CHARS  = 60    # 공통/차이 요약 최대 60자


def _compress(text: str, max_chars: int) -> str:
    """텍스트를 max_chars 이내로 잘라 토큰 낭비를 방지한다."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


# ── 프롬프트 ────────────────────────────────────────────────────────────────

def _build_diff_prompt(user_topic: str, paper: PaperHit) -> str:
    topic_c = _compress(user_topic, _TOPIC_MAX_CHARS)
    return f"""다음 연구 주제와 논문을 비교하여 JSON으로만 응답하라. 다른 텍스트는 출력하지 말 것.

연구 주제:
{topic_c}

논문:
- 제목: {paper.title}
- 연도: {paper.year}
- arXiv ID: {paper.id}
- 유사도: {paper.similarity}

출력 형식 (반드시 이 JSON만 반환):
{{"common": "공통점 한 문장", "diff": "차이점 한 문장"}}

조건:
- 학술 전문 어휘는 원형 보존, 한국어 표현 병기
- 각 문장은 30자 이내
"""


def _build_gap_prompt(user_topic: str, notes: list[SimilarPaperNote]) -> str:
    topic_c = _compress(user_topic, _TOPIC_MAX_CHARS)
    notes_text = "\n".join(
        f"- [{n.paper.id}] {n.paper.title}\n"
        f"  공통: {_compress(n.common, _NOTE_MAX_CHARS)}\n"
        f"  차이: {_compress(n.diff, _NOTE_MAX_CHARS)}"
        for n in notes
    )
    ids = [n.paper.id for n in notes]
    return f"""다음 연구 주제와 유사 논문 분석을 바탕으로 아직 탐구되지 않은 연구 공백(research gap) 후보 3개를
JSON 배열로만 응답하라. 다른 텍스트는 출력하지 말 것.

연구 주제:
{topic_c}

유사 논문 분석:
{notes_text}

출력 형식 (반드시 이 JSON만 반환):
[
  {{
    "title": "연구 공백 짧은 제목 (20자 이내)",
    "body": "한 문단 설명 (100~150자)",
    "evidence_ids": ["근거 논문 arXiv ID 1개 이상, 다음 목록에서만 선택: {ids}"]
  }},
  ...
]

조건:
- 학술 전문 어휘는 원형 보존, 한국어 표현 병기
- evidence_ids는 반드시 위 목록({ids})에서만 선택
"""


def _build_novelty_prompt(user_topic: str, notes: list[SimilarPaperNote]) -> str:
    topic_c = _compress(user_topic, _TOPIC_MAX_CHARS)
    notes_text = "\n".join(
        f"- [{n.paper.id}] {n.paper.title}\n"
        f"  공통: {_compress(n.common, _NOTE_MAX_CHARS)}\n"
        f"  차이: {_compress(n.diff, _NOTE_MAX_CHARS)}"
        for n in notes
    )
    return f"""다음 연구 주제와 유사 논문 분석을 바탕으로 연구의 전반적인 novelty를 한 문단(150~250자)으로 평가하라.
학술 전문 어휘는 원형을 보존하고 한국어 표현을 병기한다.

연구 주제:
{topic_c}

유사 논문 분석:
{notes_text}

평가:"""


# ── 파이프라인 ───────────────────────────────────────────────────────────────

def run_scenario1(user_topic: str, persona: Persona = "pro") -> NoveltyReport:
    settings = load_settings()
    embedding = BedrockEmbedding(settings)
    llm = BedrockLlm(settings)

    # Step 1: 유사 논문 5편 검색
    print("▶ Step 1: 임베딩 + 유사 논문 검색...")
    vec = embedding.embed(user_topic, lang="ko")
    hits = embedding.search(vec, k=5)
    print(f"  {len(hits)}편 검색 완료")

    # Step 2: 논문별 공통점/차이점
    print("▶ Step 2: 공통점/차이점 분석...")
    notes: list[SimilarPaperNote] = []
    for hit in hits:
        prompt = _build_diff_prompt(user_topic, hit)
        completion = llm.complete(prompt, persona=persona, budget_tokens=200)
        try:
            raw = completion.text.strip()
            # ```json ... ``` 마크다운 블록 제거
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            # 첫 번째 완성된 JSON 객체만 추출
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end]) if start != -1 else {}
            common = parsed.get("common", "")
            diff = parsed.get("diff", "")
        except (json.JSONDecodeError, ValueError):
            common = completion.text[:60]
            diff = ""
        notes.append(SimilarPaperNote(paper=hit, common=common, diff=diff))
        print(f"  [{hit.id}] 완료 (tokens: {completion.tokens_in}→{completion.tokens_out})")

    # Step 3: Overall novelty 평가
    print("▶ Step 3: Overall novelty 평가...")
    novelty_prompt = _build_novelty_prompt(user_topic, notes)
    novelty_completion = llm.complete(novelty_prompt, persona=persona, budget_tokens=400)
    overall_novelty = novelty_completion.text.strip()
    print(f"  완료 ({len(overall_novelty)}자)")

    return NoveltyReport(
        user_topic=user_topic,
        similar_papers=notes,
        overall_novelty=overall_novelty,
        gap_proposals=[],   # 시나리오 2에서 채움
        persona_mode=persona,
    )


def run_scenario2(report: NoveltyReport) -> NoveltyReport:
    """시나리오 2: 시나리오 1 결과를 받아 연구 공백 후보 3개를 gap_proposals에 채운다."""
    settings = load_settings()
    llm = BedrockLlm(settings)

    print("\n▶ 시나리오 2: 연구 공백 제안...")
    prompt = _build_gap_prompt(report.user_topic, report.similar_papers)
    completion = llm.complete(prompt, persona=report.persona_mode, budget_tokens=800)
    print(f"  완료 (tokens: {completion.tokens_in}→{completion.tokens_out})")

    try:
        raw = completion.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        start = raw.find("[")
        end = raw.rfind("]") + 1
        parsed = json.loads(raw[start:end]) if start != -1 else []
    except (json.JSONDecodeError, ValueError):
        parsed = []

    proposals = [
        GapProposal(
            title=p.get("title", ""),
            body=p.get("body", ""),
            evidence_ids=p.get("evidence_ids", []),
        )
        for p in parsed
    ]
    return NoveltyReport(
        user_topic=report.user_topic,
        similar_papers=report.similar_papers,
        overall_novelty=report.overall_novelty,
        gap_proposals=proposals,
        persona_mode=report.persona_mode,
    )




def print_report(report: NoveltyReport) -> None:
    print("\n" + "=" * 60)
    print("📋 NoveltyReport")
    print("=" * 60)
    print(f"[Persona] {report.persona_mode}")
    print(f"\n[주제]\n{report.user_topic[:100]}...\n")

    print("[유사 논문 5편]")
    for i, n in enumerate(report.similar_papers, 1):
        print(f"\n  {i}. [{n.paper.id}] {n.paper.title[:55]}")
        print(f"     year={n.paper.year} | similarity={n.paper.similarity}")
        print(f"     공통: {n.common}")
        print(f"     차이: {n.diff}")
        print(f"     출처: https://arxiv.org/abs/{n.paper.id}")

    print(f"\n[Overall Novelty 평가]\n{report.overall_novelty}")

    if report.gap_proposals:
        print(f"\n[연구 공백 제안 {len(report.gap_proposals)}개]")
        for i, g in enumerate(report.gap_proposals, 1):
            print(f"\n  {i}. {g.title}")
            print(f"     {g.body}")
            print(f"     근거 논문: {', '.join(g.evidence_ids)}")

    print("=" * 60)


if __name__ == "__main__":
    USER_TOPIC = """
본 연구는 대규모 언어 모델(LLM)을 활용한 자동화된 논문 novelty 평가 시스템을 제안한다.
기존 연구자들은 새로운 연구 아이디어의 차별성을 파악하기 위해 수동으로 관련 논문을 검색하고
비교해야 하는 번거로움이 있었다. 본 시스템은 연구 주제 초안을 입력받아 벡터 유사도 검색을
통해 관련 논문을 자동으로 찾고, LLM이 각 논문과의 공통점·차이점을 분석하여 연구 공백을
제안하는 end-to-end 파이프라인을 구축한다.
""".strip()

    report = run_scenario1(USER_TOPIC, persona="pro")
    report = run_scenario2(report)
    print_report(report)
