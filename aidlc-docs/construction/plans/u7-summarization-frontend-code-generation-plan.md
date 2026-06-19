# u7-summarization-frontend-code-generation-plan.md — Code Generation 계획

**단계**: CONSTRUCTION → Code Generation · **유닛**: U7 Summarization **Frontend** 슬라이스 · **일자**: 2026-06-19
**근거**: FD·NFR Req·NFR Design 산출물(전부 확정) · 프론트 자산(`lib/api/*`·`components/*`·`app/*`·`types/generated/*`).
**고도**: 실제 코드. 컨벤션은 기존 U5 프론트 정합(ApiClient seam·classify union·StateView·CSS Module). **real-first — 프로덕션 mock 대역 없음**(백엔드 U7 정합).

> **⚠️ 설계 플래그 (구현 중 발견)**: 기존 `Transport.send → {status, body}`는 **비스트리밍**. NFR P1(점진 스트리밍)은 seam 확장 필요 → **v1은 terminal-classified**(완성 응답 status 분류, `classifySearchResponse` 패턴), **점진 스트리밍은 seam 확장 fast-follow**.
> **[real-first]**: 프로덕션 mock 대역 없음 — 실 BFF transport로 동작. 단위 테스트만 test-only stub Transport 허용. 신규 계약(scope=full·getFullText)은 백엔드 §6 통합 의존.
> **provisional**: `getFullText`/`scope`/요약 응답 DTO는 백엔드 신규 계약 → `types/generated/summarize.ts`는 curated provisional, 백엔드 `shared/dtos/summarization.schema.json` 확정 시 `pnpm gen:types`로 재정합.

---

## 1. 빌드 순서 (프론트, Q4=A 병렬)

**파운데이션:**
- [x] `types/generated/summarize.ts` — VM/DTO(provisional) + index barrel export
- [x] `lib/api/classifySummarize.ts` — `classifySummarizeResponse`(status 판별) + `classifyFullTextResponse`
- [x] `lib/api/apiClient.ts` — `summarize()`·`getFullText()` 추가
- [x] `lib/api/index.ts` — Outcome 타입 export
- [x] `components/StateView.tsx` — kind 확장(degraded·sourceUnavailable·licenseUnavailable)
- (real-first: 프로덕션 mock 대역 없음 — 실 BFF transport 사용. mock 픽스처 미생성)

**훅·컴포넌트:**
- [x] `lib/useSummarize.ts` — terminal 상태머신(요청·디듀프·재시도·screenState)
- [x] `lib/useFullText.ts` — 전문 반환(provisional)
- [x] `components/SummaryView.tsx`(+AnchorChip)·`TranslationView.tsx`·`FullTextViewer.tsx`
- [x] `components/SummaryActions.tsx`·`PersonaToggle.tsx`·`PaperDetailIsland.tsx`
- [x] `components/SummaryAction.tsx`(카드 인라인 + SummaryInline)
- [x] `app/paper/[id]/page.tsx` — SSR 셸 + 아일랜드
- [x] ResultCard action 와이어링(검색/라이브러리)

**테스트:**
- [x] classifier 전수성·XSS·persona 멱등·식별자 결정성(vitest, **test-only stub Transport** — 프로덕션 mock 아님)

## 2. 백엔드(§6)는 별도 패스 — 본 계획은 프론트만(seam 병렬).
