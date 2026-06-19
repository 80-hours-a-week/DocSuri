# U7 Summarization Frontend — NFR Requirements

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U7 Summarization Frontend · **일자**: 2026-06-19
**근거**: 계획서 5문 확정(전부 A) · FD 산출물(컴포넌트·BR-SF-1~16·VM) · 백엔드 `POST /api/summarize`(스트리밍·status union) · `frontend/CLAUDE.md` · `@/types/generated`.
**고도**: 정책 형태(목표·전략). px/ms 수치·번들 예산·구체 서킷값은 NFR Design / Build & Test.
**[전역 계승]**: Next.js App Router·React·SSR·transport seam(BFF)·generated-types·vitest/playwright·모바일 우선·XSS/안전링크/토큰 비노출.

---

## 1. 성능 (NFR-FP)

- **NFR-FP1 (체감 성능, NFR-P2)**: `cached:true` 응답은 **즉시 렌더**(스피너 생략, BR-SF-5). 첫 생성은 **점진 렌더**(Q1=A) — 백엔드 스트리밍(근거화 통과분)을 받는 대로 표시해 체감 TTFB를 낮춘다. 목표는 "캐시 HIT 즉시 / 첫 토큰 가시화까지 짧은 지연" — 구체 ms는 Build & Test.
- **NFR-FP2 (렌더 전략, Q2=A)**: `/paper/[id]` = **SSR 셸(헤더·메타) + CSR 액션**. 라우트 진입은 SSR로 빠르게, 요약/번역/전문뷰어는 사용자 액션 시 CSR 호출(온디맨드).
- **NFR-FP3 (대용량 텍스트, Q3=A)**: 전문 번역(한국어 ~수만 토큰)·전문뷰어(정규화 전문)는 **점진/가상화 렌더** — 청크/가상 스크롤로 대용량 안정 렌더 + 앵커 위치 하이라이트. 메인 스레드 블로킹·리플로우 회피(수치는 NFR Design).
- **NFR-FP4 (디듀프)**: 진행 중 동일 요청 재탭은 새 호출 0(BR-SF-4) — 불필요 LLM 비용·렌더 방지.

## 2. 신뢰성 / 복원력 (NFR-FR)

- **NFR-FR1 (전수 매핑)**: 응답 union(ok-summary·ok-translation·abstain·cost_degraded·source_unavailable) + loading·invalid·error를 빠짐없이 screenState로 매핑(BR-SF-14). **무한 로딩 금지**.
- **NFR-FR2 (폴백·재시도)**: `error`/`cost_degraded` 재시도 경로 제공(BR-SF-15). `abstain`/`source_unavailable`은 정상 동작 — 자동 재시도 없이 고유 메시지 안내(기권 ≠ 소스부재 ≠ 비용저하).
- **NFR-FR3 (전문뷰어 게이트)**: `getFullText` `license_unavailable` → 뷰어 미개방·arXiv 링크아웃 안내(BR-SF-11). `source_unavailable` → 안내. 정규화 텍스트 안내(BR-SF-12).
- **NFR-FR4 (fail-closed 경계)**: 알 수 없는 응답·파싱 실패는 `invalid`/`error`로 안전 처리(스택/내부식별자 비노출).

## 3. 보안 (NFR-FSEC) — 대부분 전역 계승, U7 표면 적용

- **NFR-FSEC1 (XSS)**: 외부 텍스트 전부(요약 6필드·앵커 span·번역 koreanText·전문 텍스트·keptTerms) React 기본 이스케이프, `dangerouslySetInnerHTML` 금지(BR-SF-9).
- **NFR-FSEC2 (날조 0 표시 무가공)**: 백엔드 근거화 통과분만 표시, 앵커·수치 클라이언트 합성/보정 금지(BR-SF-10).
- **NFR-FSEC3 (토큰/내부값 비노출)**: 토큰·비용·캐시키·모델ID 비표시(BR-SF-16, 백엔드 SEC-9 정렬).
- **NFR-FSEC4 (안전 링크)**: 외부 링크 http/https + noopener(BR-SF-13).

## 4. 접근성 (NFR-FA)

- **NFR-FA1**: 액션 3버튼·persona 토글·AnchorChip 터치 타깃·스크린리더 라벨. 앵커 클릭→뷰어 하이라이트 시 포커스 이동·복귀.
- **NFR-FA2**: 각 비-해피 상태(로딩·기권·비용저하·소스부재·라이선스부재)를 시각+텍스트로 동반.

## 5. 관측성 (NFR-FO)

- **NFR-FO1**: 클라이언트 측 오류/상태 전이(요청 실패·기권·저하·라이선스부재) 텔레메트리 형태 — 도구/스키마는 NFR Design. 토큰/비용 등 민감값은 보내지 않는다.

## 6. 유지보수성 (NFR-FM)

- **NFR-FM1 (정합)**: VM(`SummaryVM`·`AnchorVM`·`TranslationVM`·`FullTextVM`) ↔ 백엔드 DTO **1:1**, `@/types/generated` 자동 생성(Q5=A) — 드리프트 0.
- **NFR-FM2 (provisional 경계)**: `getFullText`/`FullTextVM`·`scope`는 백엔드 신규 계약 → transport seam 병렬(Q4=A), 백엔드 §6 확정 시 재정합.

## 7. 테스트 (형태만; 도구·수치는 NFR Design/Build&Test)

- 응답 union → screenState 매핑 전수성(누락 0).
- 외부 텍스트 XSS 라운드트립 무해성.
- persona 전환 멱등(같은 persona 재요청 → 같은 표면·캐시 표기 일관).
- 식별자 매핑 결정성(카드 → SummarizeRequest 동일 입력 → 동일 요청).
- 스트리밍 점진 렌더 중단/완료 처리(부분 표시 후 완료 일관).

## 8. 추적성

NFR-FP→NFR-P2·FR-12~14 · NFR-FR→FR-11·QT-5 · NFR-FSEC→SEC(XSS·토큰)·QT-5(날조0) · NFR-FM→VM/DTO 정합 · US-S1~S5 전반.
