# DocSuri Production Roadmap — 2026-07

> **Date**: 2026-07-03 · **Baseline**: develop `7b7166d` (2026-07-05) · **main at v1.5.0** (2026-07-04 promotion)
> **Updated**: 2026-07-05 — Phase 1 execution, day 2:
> - ✅ **P2-b merged** (PR #370): **#257 단계 상세 이벤트** — worker가 FE `timelineDetail` 계약 키(source/query/count/outputSummary/reason)로 도구·쿼리·발견 출처 수·저하 사유를 emit(검색 단계는 시작+완료 이벤트, LLM 단계는 draft 선완료라 시작 이벤트가 결과 수 동봉) + **#253 유사 연구 표 상세 칼럼**(문제정의·방법·데이터셋·결과·한계·겹치는 점). 리뷰 2라운드 반영: 상세 칸은 **필드별 근거**(`{value, sourceRefIndexes}`)가 유효할 때만 값 보존 — row 출처는 포괄 근거가 아니며 검증 불가 형상은 기권 null(B-001); SSE 경로도 REST와 동일한 payload→detail 매핑(N-001).
> - ✅ **P3 1차 슬라이스 merged** (PR #373): 에이전트 첨부 **처리 전 검증**(pdf/markdown/text 허용목록 · 10MB · 최대 8개 → 422 즉시 거부, #268/#297 AC) + **실배포 첨부 500 결함** 수정(FE 객체 vs 공유계약 `list[str]` 핸들 → 파싱단계 검증 + id 핸들 변환); 후속 커밋이 evidence async 경로의 핸들 보존까지 마감. 2차(presigned upload + doc-model ingestion + #252 E2E, CDK/IAM 동반)는 **#268 설계 코멘트로 유진 검토 대기**.
> - ✅ **#371 merged** (팀): summary worker crash 수정 + 수식/MathML sanitize + glossary 편집 UI 분리(CollapsibleTerms/GlossaryTermEditor) + renderMath 보강.
> - ✅ **#372 merged** (팀 ELSAPHABA): novelty Bedrock을 `invoke_model_with_response_stream`으로 전환 + read_timeout 45s→300s — 장시간 draft 타임아웃 완화. #370과의 충돌(test_novelty·audit) 해소 및 칼럼 테스트 fake의 스트리밍 계약 이식 후 머지.
> - ⏭️ Remaining Phase 1 — see §3: P3 2차(presign+ingestion) · sessions decision (#271/#272) · eval (#273/#259) · #258 Notion · #251 form_evidence.
> _Prev 2026-07-04 pm — NFR-C1 비용 거버넌스 v1.5.0 (PR #364, 유진 `40d545d`); #339 close (PR #365); #293/#295/#296/#298 close; summary worker 5th ECS unit + **v1.5.0 승격** (PR #366/#367, 5유닛 안정); novelty FE 렌더러 (PR #368). am — v1.4.0 승격 (PR #360); CI node24 (PR #361); #338/#349 에이전트 merge; #353/#355/#357 오픈; #351 merge. 07-03 — #337 merge; #349 오픈._
> Snapshot of where the product stands against the team's initial plan, and the path to
> production-level completion of our goals. Tracking references: #251–#373 where cited below.

## 1. Status vs. the initial plan

| Plan item | Status | Notes |
|---|---|---|
| 논문 검색 | ✅ Live | Hybrid search over ~1.5M-chunk corpus; daily auto-harvest (EventBridge 15:00 KST); pre-2026 historical drain in progress |
| 논문 요약/번역 | ✅ Live | Grounded summaries/translation; glossary redesign (PR #334); source-anchor structural resolution + stale-docmodel self-heal (PR #351); tool-use structured output (PR #356, shipped v1.4.0); summary worker now its own ECS unit (PR #366, **v1.5.0**) — 무한 pending 사고 클래스 prod 종결; worker crash + 수식/MathML sanitize + glossary 편집 UI (PR #371, develop) |
| 프로필 페이지 | 🟡 Live w/ mocks | U10 merged; 최근 본 논문/ORCID still mock (#347) |
| 인용 그래프 → 각주 트리 | 🟡 Live w/ bug | DOI node expansion returns 500 (#342) — fix in **PR #357** (provider fail-closed), awaiting merge |
| 트렌드/알림 | ❌ Not started | Never entered requirements — needs inception re-entry |
| 구독제 | ❌ Not started | Never entered requirements — needs inception re-entry |
| 로그 수집 | ✅ Live | U9 collection healthy (944 events/7d, 0 failures); KPI funnel view missing (#346) |
| 개인화 추천 | 🟡 Shadow | Search boost applied in shadow mode (PR #300); go-live judgment pending (#345); US-P5 deferred |
| 에이전트: 문헌탐색/근거형성 | ✅ Live (v1.4.0) | PR #338 shipped v1.4.0; **cost-governed since v1.5.0** (PR #364); 근거 카드 + `§` 인용 앵커 (#339, PR #365); **첨부 검증(422) + 첨부 500 결함 수정 merged** (PR #373, develop). Remaining: attachments 2차(presign+ingestion, #268 설계 대기), sessions surfaces (#271/#272), eval/observability (#273) |
| (charter add) 연구아이디어 novelty 에이전트 | ✅ Live (v1.4.0) | PR #349 shipped v1.4.0; cost-governed since v1.5.0 (PR #364: draft-gate + 5/day quota). FE 아티팩트 렌더러 (PR #368) + **P2-b merged** (PR #370: 단계 상세 이벤트 + 표 상세 칼럼, 필드별 근거 강제) + **Bedrock streaming·timeout 300s** (PR #372). Remaining: #258 Notion export, #251 form_evidence |
| 웹검색 레퍼런스 (고려) | ❌ Not started | Novelty agent has GitHub+datasets search; web/news deferred to next cycle |
| 온보딩 (고려) | ❌ Not started | Candidate fix for personalization cold-start |

Infra baseline: CI/CD hardening merged (#304/#305), main promotion + v* tag CD path live.
Production deploys now go through CI on main push — the manual-buildx era is over.

## 2. Phase 0 — This week: protect prod, land the agent

| # | Action | Tracking |
|---|---|---|
| 1 | ✅ **PR #337 merged** (2026-07-03 13:00 UTC) — revert-on-promote trap closed | PR #337 |
| 2 | ✅ **PR #338 merged** (`f12990d`, 2026-07-04) — #359 landed all 4 blockers + whitespace + multi-turn context; independently re-reviewed → APPROVED. Attachments → tracked follow-up | PR #338, #359 |
| 3 | ✅ **Promoted develop→main → `v1.4.0`** (2026-07-04) — PR #360 merged (`45651d0`); `release.yml` auto-tagged `v1.4.0` (ships #351 anchor, #356 tool-use, #338 evidence agent, #349 novelty agent), `cd.yml` ECS rolling deploy | #340 · `v1.4.0` |
| 4 | ✅ **#339 closed** (PR #365, 2026-07-04) — 근거 카드 + `§` 인용 앵커 렌더링 + screen-level evidence-card test; shipped in v1.5.0 | #339 · PR #365 |

## 3. Phase 1 — Weeks 1–2: agent GA (the 차별화)

The differentiator is ~90% built. Finish it before starting anything new.

**Execution board (2026-07-05)** — verified against code+tests, not docs (board sweep: 4 stories DONE→closed, rest partial):

| Step | Status | Notes |
|---|---|---|
| P0 · Cost gates (NFR-C1) | ✅ **v1.5.0** | PR #364 — CostGuard on both agent Bedrock paths, real spend recorded from invocation metrics, critical-tier `[abstain] cost_degraded`, per-user daily quotas (evidence 30 · novelty 5; Redis-shared, fail-open) |
| P1 · #339 + story hygiene | ✅ **v1.5.0** | PR #365 (근거 카드 + `§` 앵커 + screen test); #293/#295/#296/#298 closed with evidence comments |
| P2-a · Novelty FE renderers | ✅ develop | PR #368 (`233aac1`) — #253–#256 FE half; ships with next promotion |
| P2-b · Novelty backend | ✅ develop | PR #370 — #257 단계 상세 이벤트(timelineDetail 계약) + #253 표 상세 칼럼; 리뷰 2라운드로 **필드별 근거 강제**(B-001) + SSE detail 매핑(N-001). 같은 날 PR #372(Bedrock streaming + timeout 300s)와 통합 |
| P3 · Attachments E2E | 🟡 1차 develop | 1차 ✅ (PR #373): 처리 전 검증(422) + 첨부 500 결함 + async 핸들 보존. 2차 ⬜: presigned upload + doc-model ingestion + #252 manuscript E2E — **#268 설계 코멘트 유진 검토 대기** (CDK/IAM 동반, cd.yml allowlist 선배포 순서) |
| P4 · Residue | ⬜ | sessions surfaces decision (#271/#272 — dead surface or wire it) · eval harness/metrics (#273/#259) · #258 Notion export · #251 form_evidence-first · novelty old-queue drain/retire 확인 (cutover green at v1.4.0) |

## 4. Phase 2 — Weeks 2–4 (parallel): production hardening

Ordered by user impact:

| Item | Tracking |
|---|---|
| Intermittent SSR 500 on paper pages — **PR #353** enables ALB/CloudFront access logs (step ①); root-cause after a repro. Investigation: module-resolution guess weak (no dynamic imports; self-contained standalone) — likelier load-driven OOM. Raw-500 exposure fix belongs at the edge (CloudFront `error_responses`), not React boundaries → **PR #355** (step ②): branded page served from a private S3/OAC origin, independent of the failing ALB. Remaining: **PR-B** root-cause fix, after #353 logs give a repro. | #341 · #353 · #355 |
| 각주 트리 DOI node expansion 500 — **PR #357**: S2 200-with-bad-body was fail-open (parse escaped the `httpx`-only guard → app 500); now fail-closed to Unavailable at both the provider parse and tree assembly (BR-CG12). Regression tests exercise the real provider path the old suite bypassed via FixtureProvider. | #342 · #357 |
| Docmodel backlog self-heal — re-enqueue contaminated docmodels @3 (embedding-cost-free) + drain DLQ 111 | #343 |
| Finish pre-2026 backfill drain → restore ingestion autoscale; decide on separate doc-model queue | #344 |
| Personalization shadow→real flip after metric review; then US-P5 + keywordWeights | #345 |
| KPI funnel dashboard (AI 호출 > 검색 > 완독률) from existing U9 events — build **before** Phase 3 prioritization | #346 |
| U10 mypage mocks: 최근 본 논문/ORCID real data or cut | #347 |
| Email strategy decision: SES production access vs. Resend commitment | #348 |
| Authz contract → `docsuri_shared` refactor | #167 |
| 검색 품질 개선 (charter phase 7) | charter |
| Issue hygiene: close shipped US-A3~A7 stories (#187–191) | — |
| `mathieudutour/github-tag-action` node24 bump — blocked on upstream release (rest of CI on node24 since PR #361) | — |
| Env-dependent `test_api_create_status_and_cancel` (passes only when AWS creds absent) — pin the fake/live seam | — |

## 5. Phase 3 — Month 2: growth scope (requires inception re-entry)

Recommended order; none of these have requirements coverage today:

1. **온보딩** — smallest scope; seeds U9 keyword signals at signup, solving
   personalization cold-start.
2. **트렌드/알림** — email digest of new papers in followed topics. Cheapest version
   reuses the daily harvest + existing email path. Builds the retention loop 구독제
   needs.
3. **웹검색 레퍼런스** — implement as an evidence-agent *tool* (web/news search was
   already deferred to next cycle in the novelty charter), not a standalone feature.
4. **구독제** — deliberately last: agent LLM cost per user is the natural paid
   boundary, but pricing needs Phase 1 live + Phase 2's KPI funnel for real per-user
   Bedrock spend. Payment-provider decision via requirements re-entry.

## 6. Sequencing rationale

Ship the differentiator first (it's nearly done) → harden what users already touch →
build the retention loop → monetize with real cost data. Trends/subscription before the
agent would monetize an undifferentiated product; the KPI funnel (#346) is the cheap
instrument that keeps Phase 3 decisions honest.
