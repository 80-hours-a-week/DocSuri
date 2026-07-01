# U7 Summarization Frontend — Tech Stack Decisions (ADR)

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U7 Summarization Frontend · **일자**: 2026-06-19
**형식**: ADR(결정 · 근거 · 대안 · 전환 비용). 계획서 5문 확정(전부 A) 반영.

---

## [전역 계승] (재결정 아님)

| 항목 | PIN |
|---|---|
| 프레임워크 | Next.js 15.1.6 (App Router) · React 19 |
| 렌더 | SSR 기본 |
| 패키지 | pnpm |
| 테스트 | vitest(단위) + playwright(E2E) |
| API 레이어 | ApiClient 단일 진입 + 실 transport(`routeHandlerTransport` BFF → U6 게이트웨이). **real-first — 프로덕션 mock 대역 없음** |
| 타입 | `@/types/generated`(백엔드 스키마 파생) |
| 스타일 | 모바일 우선 CSS Module |
| 보안 | XSS 이스케이프 · 안전 링크 · 토큰 클라이언트 비노출(`frontend/CLAUDE.md`) |

---

## ADR-1 — 스트리밍 소비 = 점진 렌더 (Q1=A)

- **결정**: 백엔드 스트리밍 응답(근거화 통과분)을 fetch 스트림으로 **받는 대로 점진 렌더**.
- **근거**: 첫 생성 수십 초 → 체감 TTFB↓(NFR-FP1). 백엔드가 *안전 콘텐츠만* 스트리밍(BR-S8)하므로 표시 측 추가 검증 불요(BR-SF-10).
- **대안**: 완성분 await 후 일괄(단순하나 긴 대기).
- **전환 비용**: 낮음 — 점진→일괄 다운그레이드는 표시 로직만.

## ADR-2 — 렌더 전략 = SSR 셸 + CSR 액션 (Q2=A)

- **결정**: `/paper/[id]`는 헤더·메타 SSR, 요약/번역/전문뷰어는 사용자 액션 시 CSR 호출.
- **근거**: 요약/번역은 온디맨드 액션 → CSR이 자연스럽고, 라우트 진입 체감은 SSR 셸로 확보(NFR-FP2). 기존 U5 search/library 패턴 정합.
- **대안**: 전체 CSR(진입 빈 화면 지연).
- **전환 비용**: 낮음.

## ADR-3 — 대용량 텍스트 = 점진/가상화 렌더 (Q3=A)

- **결정**: 전문 번역·전문뷰어는 청크/가상 스크롤 렌더 + 앵커 위치 하이라이트.
- **근거**: 한국어 전문 번역·정규화 전문은 수만 토큰 → 일괄 DOM 렌더 시 성능 부담(NFR-FP3).
- **대안**: 단순 일괄 렌더(소형은 무방, 초대형서 부담).
- **전환 비용**: 중 — 가상화 도입은 컴포넌트 구조 영향(구체 도구는 NFR Design).

## ADR-4 — 전문 반환 API = real-first, provisional 타입 (Q4=A; mock 제거)

- **결정**: `getFullText`/전문 반환 API·`scope`는 백엔드 신규 계약. 프론트는 **실 transport(BFF) 기준 real-first** 구현 — **프로덕션 mock 대역 없음**(백엔드 U7 real-first 정합). 응답 DTO는 provisional 타입으로 두고 백엔드 §6 확정 시 1:1 재정합.
- **근거**: 기존 `/api/summarize`(요약·초록 번역)는 실 백엔드 보유 → 즉시 실 연동. 신규 계약(scope=full·getFullText)은 **백엔드 §6 통합 의존** — mock으로 우회하지 않는다.
- **대안**: 프로덕션 mock 대역(❌ real-first 위배) / 백엔드 확정까지 전면 블로킹.
- **테스트**: 프로덕션 mock 없음. 단위 테스트는 **test-only stub Transport** 허용(백엔드 `tests/stubs` 선례 정합).
- **마일스톤**: 백엔드 전문 반환 API + `scope` 계약 확정 = 신규 기능 실 연동 지점.

## ADR-5 — 타입 정합 = generated-types 파이프라인 계승 (Q5=A)

- **결정**: 신규 DTO(Summary/Translation/FullText)도 `@/types/generated` 자동 생성, VM이 소비.
- **근거**: 백엔드 DTO ↔ 프론트 VM 드리프트 0(NFR-FM1). 기존 파이프라인 재사용.
- **대안**: 수기 타입(드리프트 위험).
- **전환 비용**: 낮음.

---

## 신규 ApiClient 시임 계약 (요약)

```
summarize(req: SummarizeRequest): Promise<SummarizeOutcome>   // POST /api/summarize (스트리밍, status union)
getFullText(req: FullTextRequest): Promise<FullTextOutcome>   // Q5=C 신규 (OA 라이선스 게이트) — provisional
```

- 분류기 `classifySummarizeResponse(body)` = 기존 `classifySearchResponse` 미러, 단 `body.status` 판별.
- transport: routeHandlerTransport(BFF)로 U6 게이트웨이 경유(토큰 서버측). **real-first — 프로덕션 mock 대역 없음**(테스트는 test-only stub 한정).

---

## 백엔드 연계(재확인 — Code-gen에서 수행)

계획서 §6 백엔드 델타(전문 번역 `scope`·전문 반환 API·persona 유지)와 정합. 프론트는 seam으로 병렬, 백엔드 계약 확정이 재정합 마일스톤.
