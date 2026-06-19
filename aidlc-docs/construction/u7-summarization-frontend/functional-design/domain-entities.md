# U7 Summarization Frontend — Domain Entities (Functional Design, 경량)

**단계**: CONSTRUCTION → Functional Design · **유닛**: U7 Summarization Frontend · **일자**: 2026-06-19
**원칙**: 클라이언트 **뷰모델(VM)** 만 정의. 백엔드 DTO(`backend/modules/summarization/.../models.py`)와 **1:1 정합(드리프트 0)**. 타입생성·런타임 검증은 NFR.

---

## 1. 요청 VM

```
SummarizeRequest {
  task:      "summary" | "translate"
  paperId:   string            // = ResultCardVM.arxivId (Q8=A)
  version:   number            // = 1 (Q8=A)
  scope?:    "abstract" | "full"   // translate 전용; 기본 "abstract" (요약은 full 고정·무시)
  persona?:  "expert" | "beginner" // summary 전용; 번역은 미적용(단일)
  targetLang?: "ko"            // 기본 ko
  abstract?: string            // 백엔드 보유 초록 사용 — 카드 스니펫 전송 금지(BR-SF-2)
}

FullTextRequest {              // Q5=C 신규
  paperId: string
  version: number
}
```

## 2. 응답 union → Outcome (status 판별)

백엔드 응답은 `status` 판별자 보유 → 구조 추정 불요.

```
SummarizeOutcome =
  | { kind: "summary";          summary: SummaryVM;     meta: ResultMeta; cached: boolean }
  | { kind: "translation";      translation: TranslationVM; meta: ResultMeta; cached: boolean }
  | { kind: "abstain";          reason: unknown }
  | { kind: "degraded";         message: string }          // cost_degraded
  | { kind: "sourceUnavailable"; reason: unknown }
  | { kind: "invalid";          field?: string; message: string }   // HTTP 4xx 검증
  | { kind: "error";            message: string }                    // 네트워크/5xx

FullTextOutcome =              // Q5=C
  | { kind: "page";              fullText: FullTextVM }
  | { kind: "licenseUnavailable" }                          // OA 미허용 → arXiv 안내
  | { kind: "sourceUnavailable" }
  | { kind: "error";             message: string }
```

> `classifySummarizeResponse(body)` = 기존 `classifySearchResponse` 패턴 미러. 단 **`body.status`로 분기**(검색은 무판별 구조분류).

## 3. 콘텐츠 VM (백엔드 §3 스키마 1:1)

```
SummaryVM {                    // ok + summary
  tldr:           string
  contributions:  string[]
  method:         string
  results:        string
  limitations:    string
  reproducibility: { code: string; data: string }
  anchors:        AnchorVM[]
}

AnchorVM {
  field:   string                          // 가리키는 §3 필드명
  target:  "section" | "table" | "figure"
  span:    string                          // 원문 구절(이스케이프 렌더)
  label:   string                          // 예: "§Results", "표 2"
}

TranslationVM {                // ok + translation (초록·전문 공용)
  koreanText: string
  keptTerms:  string[]                     // 미번역 보존 용어 배지
  scope:      "abstract" | "full"          // 표시 컨텍스트(요청 echo)
}

FullTextVM {                   // Q5=C 전문뷰어
  text:        string                      // 정규화 전문(참고문헌·저자 제거 — 안내 표기)
  // 앵커 하이라이트는 AnchorVM.target/span을 text 내에서 매칭
}
```

## 4. 화면 상태 enum

```
screenState =
  | "idle" | "loading" | "page"
  | "abstain" | "degraded" | "sourceUnavailable"   // U7 추가분
  | "licenseUnavailable"                            // 전문뷰어(Q5=C) 추가
  | "invalid" | "error"
```

> U5 `StateViewKind`(loading|empty|abstain|invalid|error)에 **`degraded`·`sourceUnavailable`·`licenseUnavailable`** 추가(코드는 Code-gen에서).

## 5. 정합 메모

- `SummaryVM`/`AnchorVM`/`TranslationVM` 필드명·타입은 백엔드 `models.py`(SummaryDraft·Anchor·TranslationDraft, SEC-9 `to_dict` 화이트리스트)와 **정확히 일치**시킨다.
- `meta`/`cached`는 백엔드 응답 그대로. 토큰·비용·캐시키·모델ID는 VM에 싣지 않는다(BR-SF-16).
- ⚠️ `FullTextVM` + `getFullText`는 **백엔드 신규 계약**(Q5=C) — 프론트 VM은 제안형이며, 백엔드 전문 반환 API 확정 시 1:1 재정합 필요(계획서 §6).
