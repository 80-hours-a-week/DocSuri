# u7-summarization-frontend-nfr-design-plan.md — NFR Design 계획

**단계**: CONSTRUCTION → NFR Design (유닛별 루프) · **유닛**: U7 Summarization **Frontend** 슬라이스 · **일자**: 2026-06-19
**근거**: NFR Requirements `construction/u7-summarization-frontend/nfr-requirements/`(5문 전부 A·NFR-FP/FR/FSEC/FM·ADR-1~5) · FD 산출물(컴포넌트·BR-SF·VM) · 프론트 자산(ApiClient·transport seam·classify·StateView).
**목적**: NFR 전략을 **설계 패턴 + 논리 컴포넌트**로 구체화 — 스트리밍 소비 메커니즘·SSR 셸/CSR 아일랜드·가상화·복원력(union 매핑·재시도)·보안 패턴·테스트 패턴.
**고도**: 패턴·논리 컴포넌트·정책. **수치 실측(ms·번들·가상화 윈도우 크기)·구체 라이브러리 선정**은 Code-gen/Build & Test.

> **계승**: Next.js App Router·React·SSR·transport seam(BFF)·generated-types·vitest/playwright. **ADR(NFR Req)**: 점진렌더·SSR셸+CSR액션·가상화·provisional+seam병렬·generated-types.
> **새 질문 게이트 없음**: 전략 결정은 NFR Requirements 5문(전부 A)에서 잠금. 본 단계는 그 결정의 **구현 패턴 도출**이라 추가 결정 불요. (구현 중 분기 발생 시 Code-gen에서 플래그.)

---

## 1. 유닛 컨텍스트 (NFR Design 렌즈)

- 프론트 U7 = `/paper/[id]` 상세 표면 + 카드 인라인 요약. 온디맨드(NFR-P1 비대상, NFR-P2 체감).
- **핵심 설계 동인**: 점진 스트리밍 렌더(NFR-FP1) · SSR셸+CSR액션(NFR-FP2) · 대용량 가상화(NFR-FP3) · union 전수 매핑·무한로딩 금지(NFR-FR1/2) · XSS/날조0/토큰(NFR-FSEC) · VM↔DTO 정합(NFR-FM).
- **단일 권위 경계**: 인증/레이트리밋/비용 = U6 게이트웨이(BFF 경유). 근거화는 백엔드 — 프론트는 통과분 표시만(무가공).

## 2. NFR Design 실행 계획 (체크박스)

> 산출물은 `construction/u7-summarization-frontend/nfr-design/` 에 생성.

- [x] **nfr-design-patterns.md** ✅ — 스트리밍 소비·체감성능·SSR/CSR·가상화·복원력(union reducer·재시도)·전송 seam·보안·테스트 패턴 + 추적성.
- [x] **logical-components.md** ✅ — 라우트 세그먼트·클라이언트 아일랜드·훅(useSummarize/useFullText)·ApiClient/classifier/transport·StateView. FD 컴포넌트 ↔ 논리 컴포넌트 매핑.

## 3. 가정

- DS-1: 구체 수치(스트림 청크 플러시·가상화 윈도우·타임아웃 ms·번들 예산)·구체 라이브러리는 Code-gen/Build&Test.
- DS-2 [U6 위임]: 인증/레이트리밋/비용은 게이트웨이(BFF). 프론트는 소비.
- DS-3 (provisional): `getFullText`/`scope`는 백엔드 신규 — seam 병렬, 확정 시 재정합.

## 4. 진행 메모

- 산출물 → NFR Design 완료(REVIEW) → 승인 → **Code Generation**(백엔드 §6 + 프론트 실제 코드) → Build & Test.
