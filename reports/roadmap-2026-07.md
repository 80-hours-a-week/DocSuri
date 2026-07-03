# DocSuri Production Roadmap — 2026-07

> **Date**: 2026-07-03 · **Baseline**: develop `573ad494` (main at v1.2.3, 13 commits behind)
> **Updated**: 2026-07-03 pm — PR #337 merged; PR #349 (novelty progress UX + queue ownership) opened.
> Snapshot of where the product stands against the team's initial plan, and the path to
> production-level completion of our goals. Tracking issues: #339–#348.

## 1. Status vs. the initial plan

| Plan item | Status | Notes |
|---|---|---|
| 논문 검색 | ✅ Live | Hybrid search over ~1.5M-chunk corpus; daily auto-harvest (EventBridge 15:00 KST); pre-2026 historical drain in progress |
| 논문 요약/번역 | ✅ Live | Grounded summaries/translation; glossary system redesigned (PR #334); map parallelism + shared-base overlay landed |
| 프로필 페이지 | 🟡 Live w/ mocks | U10 merged; 최근 본 논문/ORCID still mock (#347) |
| 인용 그래프 → 각주 트리 | 🟡 Live w/ bug | DOI node expansion returns 500 (#342) |
| 트렌드/알림 | ❌ Not started | Never entered requirements — needs inception re-entry |
| 구독제 | ❌ Not started | Never entered requirements — needs inception re-entry |
| 로그 수집 | ✅ Live | U9 collection healthy (944 events/7d, 0 failures); KPI funnel view missing (#346) |
| 개인화 추천 | 🟡 Shadow | Search boost applied in shadow mode (PR #300); go-live judgment pending (#345); US-P5 deferred |
| 에이전트: 문헌탐색/근거형성 | 🚧 One PR away | PR #338 — full pipeline E2E-verified on real AWS; `Docsuri-Evidence` stack deployed idle; FE renders raw JSON (#339) |
| (charter add) 연구아이디어 novelty 에이전트 | 🚧 In construction | Code in develop, `Docsuri-Novelty` stack built; US-NV stories (#251–259) open; PR #349 (progress UX + queue ownership) in review |
| 웹검색 레퍼런스 (고려) | ❌ Not started | Novelty agent has GitHub+datasets search; web/news deferred to next cycle |
| 온보딩 (고려) | ❌ Not started | Candidate fix for personalization cold-start |

Infra baseline: CI/CD hardening merged (#304/#305), main promotion + v* tag CD path live.
Production deploys now go through CI on main push — the manual-buildx era is over.

## 2. Phase 0 — This week: protect prod, land the agent

| # | Action | Tracking |
|---|---|---|
| 1 | ✅ **PR #337 merged** (2026-07-03 13:00 UTC) — revert-on-promote trap closed | PR #337 |
| 2 | Review + merge **PR #338** (U11 evidence agent; infra already live-but-idle) | PR #338 |
| 3 | Promote develop→main + tag (ships glossary redesign + #337 + #338 via real CD) | #340 |
| 4 | Fix AgentChatScreen raw-JSON rendering — start **after** #338 and #349 land (both rewrite `AgentChatScreen.tsx`); base the fix on #349's version | #339 |

## 3. Phase 1 — Weeks 1–2: agent GA (the 차별화)

The differentiator is ~90% built. Finish it before starting anything new.

- **Evidence agent stories** (#268–273): attachments, abstention paths, session
  persistence/re-open, session delete, observability + invariants.
- **Agent chat frontend** (#293–299): nav entry, mode select, session drawer,
  exploration timeline, attachment UX, mock/real transport boundary, quality gate.
- **Novelty agent stories** (#251–259): manuscript upload, 유사 연구 표, 차별화
  후보/실험 계획, Notion export, progress display. **PR #349 (in review)** largely
  lands progress display (US-NV7 #257), the DLQ+alarm half of observability
  (US-NV9 #259), and timeline normalization toward US-AG4 #296.
  ⚠️ Its queue swap (stack-owned SQS, RETAIN) needs rollout coordination — worker
  and API must cut to the new queue URL in one rollout, then drain/retire the old
  queue (cf. the PR #323 old-worker skew trap). Details in the PR comment.
- **Cost gates before public exposure**: both agents call Bedrock Sonnet per turn under
  the $1600 cap — verify NFR-C1 agent cost lines + per-user throttles on the live path.

## 4. Phase 2 — Weeks 2–4 (parallel): production hardening

Ordered by user impact:

| Item | Tracking |
|---|---|
| Intermittent SSR 500 on paper pages — enable ALB/CloudFront access logs, then root-cause | #341 |
| 각주 트리 DOI node expansion 500 | #342 |
| Docmodel backlog self-heal — re-enqueue contaminated docmodels @3 (embedding-cost-free) + drain DLQ 111 | #343 |
| Finish pre-2026 backfill drain → restore ingestion autoscale; decide on separate doc-model queue | #344 |
| Personalization shadow→real flip after metric review; then US-P5 + keywordWeights | #345 |
| KPI funnel dashboard (AI 호출 > 검색 > 완동률) from existing U9 events — build **before** Phase 3 prioritization | #346 |
| U10 mypage mocks: 최근 본 논문/ORCID real data or cut | #347 |
| Email strategy decision: SES production access vs. Resend commitment | #348 |
| Authz contract → `docsuri_shared` refactor | #167 |
| 검색 품질 개선 (charter phase 7) | charter |
| Issue hygiene: close shipped US-A3~A7 stories (#187–191) | — |

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
