"""시나리오 3 테스트: 학부생 가벼운 점검.

Given: 학부 수준의 사용자가 졸업프로젝트 아이디어를 한국어 3~5문장으로 입력
When:  "가벼운 점검" 요청
Then:  "비슷한 학부 수준 시도가 있는지" 한 문단 평가 + 차별점 1줄

제약:
- persona: undergrad (한국어 능력시험 4급 수준 어휘, 평균 문장 길이 ≤ 22어절)
- 기본 출력 언어: 한국어

실행: cd backend && pyenv exec python3 scripts/scenario3_test.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docsuri.u0.adapters.aws import BedrockEmbedding, BedrockLlm
from docsuri.u0.config import load_settings
from docsuri.u0.ports import PaperHit

_EOJEOL_LIMIT = 22   # 시나리오 3 제약: 평균 문장 길이 ≤ 22어절


# ── 어절 검증 ────────────────────────────────────────────────────────────────

def _check_sentence_length(text: str) -> dict[str, object]:
    """문장별 어절 수를 분석하여 제약 준수 여부를 반환한다."""
    sentences = [s.strip() for s in re.split(r"[.?!\n]", text) if s.strip()]
    lengths = [len(s.split()) for s in sentences]
    if not lengths:
        return {"ok": True, "avg": 0, "max": 0, "violations": []}
    avg = round(sum(lengths) / len(lengths), 1)
    violations = [
        {"sentence": sentences[i][:40], "eojeol": length}
        for i, length in enumerate(lengths) if length > _EOJEOL_LIMIT
    ]
    return {"ok": avg <= _EOJEOL_LIMIT, "avg": avg, "max": max(lengths), "violations": violations}


# ── DTO ──────────────────────────────────────────────────────────────────────

@dataclass
class UndergradCheckResult:
    user_idea: str
    similar_papers: list[PaperHit]
    check_paragraph: str   # "비슷한 시도가 있는지" 한 문단
    diff_suggestion: str   # 차별점 1줄


# ── 프롬프트 ────────────────────────────────────────────────────────────────

def _build_undergrad_prompt(user_idea: str, papers: list[PaperHit]) -> str:
    # 토큰 최적화: 아이디어 300자, 제목 50자로 압축
    idea = user_idea.strip()
    idea_c = idea[:297] + "…" if len(idea) > 300 else idea
    papers_text = "\n".join(
        f"- [{p.id}] {p.title[:50]} ({p.year}년, 유사도 {p.similarity})"
        for p in papers
    )
    return f"""아래는 대학교 졸업 프로젝트 아이디어와 비슷한 논문들이야.
학부 1~2학년도 이해할 수 있는 쉬운 한국어로 답해줘.
문장은 짧게 써줘 (한 문장에 22어절 이하).
어려운 영어 단어는 쓰지 말고, 꼭 써야 하면 한국어로 설명을 붙여줘.

졸업 프로젝트 아이디어:
{idea_c}

비슷한 논문 목록:
{papers_text}

다음 두 가지를 답해줘:

[비슷한 시도 평가]
위 논문들 중에 이 아이디어와 비슷한 시도가 있는지 한 문단으로 설명해줘.
있으면 어떤 점이 비슷한지, 없으면 왜 새로운 시도인지 알려줘.

[차별점 제안]
이 아이디어가 기존 연구와 달리 가져갈 수 있는 차별점을 딱 한 문장으로 말해줘."""


# ── 파이프라인 ───────────────────────────────────────────────────────────────

def run_scenario3(user_idea: str) -> UndergradCheckResult:
    settings = load_settings()
    embedding = BedrockEmbedding(settings)
    llm = BedrockLlm(settings)

    # Step 1: 유사 논문 검색 (학부 모드는 3편으로 충분)
    print("▶ Step 1: 임베딩 + 유사 논문 검색 (k=3)...")
    vec = embedding.embed(user_idea, lang="ko")
    hits = embedding.search(vec, k=3)
    print(f"  {len(hits)}편 검색 완료")
    for h in hits:
        print(f"  [{h.id}] {h.title[:50]} | similarity={h.similarity}")

    # Step 2: Claude로 평가 생성 (undergrad persona)
    print("▶ Step 2: 가벼운 점검 생성 (undergrad)...")
    prompt = _build_undergrad_prompt(user_idea, hits)
    completion = llm.complete(prompt, persona="undergrad", budget_tokens=500)
    print(f"  완료 (tokens: {completion.tokens_in}→{completion.tokens_out})")

    # 응답에서 [비슷한 시도 평가] / [차별점 제안] 섹션 파싱
    text = completion.text.strip()
    check_paragraph = ""
    diff_suggestion = ""

    if "[비슷한 시도 평가]" in text and "[차별점 제안]" in text:
        parts = text.split("[차별점 제안]")
        check_part = parts[0].replace("[비슷한 시도 평가]", "").strip()
        diff_part = parts[1].strip()
        check_paragraph = check_part
        diff_suggestion = diff_part
    else:
        # 섹션 구분이 없으면 전체를 check_paragraph로
        check_paragraph = text

    return UndergradCheckResult(
        user_idea=user_idea,
        similar_papers=hits,
        check_paragraph=check_paragraph,
        diff_suggestion=diff_suggestion,
    )


# ── 출력 ─────────────────────────────────────────────────────────────────────

def print_result(result: UndergradCheckResult) -> None:
    print("\n" + "=" * 60)
    print("가벼운 점검 결과 (학부생 모드)")
    print("=" * 60)

    print(f"\n[입력 아이디어]\n{result.user_idea}\n")

    print("[검색된 유사 논문]")
    for i, p in enumerate(result.similar_papers, 1):
        print(f"  {i}. [{p.id}] {p.title[:55]}")
        print(f"     year={p.year} | similarity={p.similarity}")
        print(f"     출처: https://arxiv.org/abs/{p.id}")

    print(f"\n[비슷한 시도가 있는지 평가]\n{result.check_paragraph}")

    if result.diff_suggestion:
        print(f"\n[차별점 제안]\n{result.diff_suggestion}")

    # 22어절 제약 검증
    full_text = result.check_paragraph + " " + result.diff_suggestion
    stat = _check_sentence_length(full_text)
    ok_mark = "OK" if stat["ok"] else "WARN"
    print(f"\n[제약 검증] 평균 문장 길이 ≤ 22어절")
    print(f"  {ok_mark} 평균={stat['avg']}어절 | 최대={stat['max']}어절")
    if stat["violations"]:
        print("  초과 문장:")
        for v in stat["violations"]:
            print(f"    - ({v['eojeol']}어절) {v['sentence']}…")

    print("=" * 60)


if __name__ == "__main__":
    USER_IDEA = """
나는 스마트폰 카메라로 찍은 음식 사진을 보고 자동으로 칼로리를 알려주는 앱을 만들고 싶어.
사용자가 사진을 찍으면 AI가 음식의 종류를 알아보고, 양을 추정해서 칼로리를 계산해줘.
한국 음식도 잘 인식할 수 있도록 한국 음식 데이터를 따로 학습시킬 계획이야.
이 앱을 통해 다이어트 중인 사람들이 더 쉽게 식단을 관리할 수 있으면 좋겠어.
""".strip()

    result = run_scenario3(USER_IDEA)
    print_result(result)
