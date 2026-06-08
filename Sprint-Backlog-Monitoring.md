## 스프린트 백로그 — 04. 자동 모니터링 & 알림 (Auto Monitoring & Notification)

> 등록된 쿼리를 주기 실행 → 의미 있는 변화(신규/인용급증/SOTA/벤치마크)만 필터 → 다채널 알림.
> **W7 Temporal 도입 진입 기능** (AGENTS.md §5.3) — 이후 #06/#07/#09는 무조건 Temporal.
> 모듈 경계: `domain/monitoring/` + `workflows/monitoring_cron/` + `crosscutting/{ratelimit,audit}/` + `infra/{notification,llm,storage,temporal}/`.
> 출처: `feature-specs/04-auto-monitoring-and-notification.md`.

---

### Sprint 1 — Temporal Cluster Owner + Skeleton Notification

**Sprint 1 DoD:** Temporal 클러스터 dev/staging 가동 + 한 사용자가 cron 등록 → 잡 실행 → skeleton 이메일 발송. **infra/temporal이 #06/#07/#09에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[Owner]** infra/temporal: Temporal 클러스터 셋업 + Python SDK + worker 배포 (W7 도입 시점, AGENTS.md §5.3) — #06/#07/#09 공통 의존 | 8 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 큰 인프라 — HA + RBAC + 환경 + worker | dev/staging 클러스터 + worker healthcheck + Sample 워크플로우 실행 |
| 2 | domain/monitoring: Subscription Registry (user_id, query, schedule, channel) Postgres 스키마 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 스키마 + Alembic | 스키마 + Alembic 마이그레이션 + CRUD API |
| 3 | workflows/monitoring_cron: cron-like Schedule + jitter(0~30분) 분산 + 사용자별 격리 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Temporal Schedule + jitter | Temporal Schedule + jitter 분산 검증 + 사용자별 namespace |
| 4 | domain/monitoring: Query Executor — 01 검색 파이프라인 재사용 호출 어댑터 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #01 wrapping | #01 호출 + 결과 정규화 |
| 5 | frontend: 구독 등록 UI (키워드/주기/채널/수준) + 구독 관리 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 페이지 + 폼 + 관리 | 구독 등록 → 잡 가시화 + 수정/삭제 + 빈/에러 처리 |

**Sprint 1 합계: 21 포인트**

---

### Sprint 2 — Change Detection + Classification + Multi-channel

**Sprint 2 DoD:** 4종 변화 분류(new_paper/citation_spike/sota/new_benchmark) + Importance Classifier + Email/Push/Slack/Discord 동시 발송 동작.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/monitoring: State Differ — last_snapshot vs current → new_paper/citation_spike/sota/new_benchmark | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | diff 4종 + 임계 + 분야별 베이스라인 | 4 종 변화 분류 + 분야별 임계값 설정 + 단위 테스트 통과 |
| 2 | domain/monitoring: Papers with Code API 연동 (SOTA 갱신 탐지) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | PwC API + SOTA 추출 | PwC API 호출 + SOTA 갱신 정확도 90%+ |
| 3 | domain/monitoring: Importance Classifier (Claude Haiku) — 사용자 컨텍스트 × 변화 → 점수 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | LLM + 점수 + 컨텍스트 | 변화 이벤트당 1회 호출 + 점수 [0,1] + 컨텍스트 합성 |
| 4 | domain/monitoring: Digest Composer — N건 cap + 우선순위 정렬 + 한 줄 설명 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | cap + 정렬 + LLM 설명 | cap 강제 + 중요도 정렬 + 한 줄 설명 |
| 5 | infra/notification: Email(SES) + Web push(FCM) + Slack/Discord webhook 디스패처 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 채널 + 통합 + fallback | 4 채널 발송 + 실패 fallback + 디스패치 메트릭 |
| 6 | domain/monitoring: State Updater — 새 snapshot 저장 (Postgres + Redis 실행 락) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 스냅샷 + 락 wrapping | 스냅샷 원자성 + 중복 실행 락 검증 |

**Sprint 2 합계: 21 포인트**

---

### Sprint 3 — Fatigue Control + Compliance + Ops Hardening

**Sprint 3 DoD:** 알림 피로 down-rank 동작 + GDPR 익명화 정책 적용 + SES 워밍업 가이드 작성 + 1만 잡 동시 실행 부하 통과 + SOTA false-positive 회귀 통과.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/monitoring: 알림 피로 자동 제어 — 클릭률 학습 + down-rank + 빈도 조정 권장 메시지 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 클릭률 + down-rank + 조정 UX | 클릭률 측정 + 14일 무클릭 카테고리 down-rank + 조정 메시지 |
| 2 | crosscutting/ratelimit: arXiv OAI-PMH 대안 경로 + S2 citation 주 단위 freshness 핸들링 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | OAI-PMH + 신선도 캐시 | OAI-PMH 통합 테스트 + 주 단위 freshness 캐시 |
| 3 | crosscutting/audit: GDPR/개인정보 정책 — 익명화 + 삭제 권리 + 구독 패턴 익명 통계 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 익명화 + 삭제 + 통계 | 익명화 룰 + 삭제 권리 API + 익명 집계 검증 |
| 4 | tests: SES 워밍업 시나리오 + 1만 잡 동시 실행 부하 + SOTA false-positive 회귀 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 부하 인프라 + 워밍업 + 3 시나리오 | 1만 잡 부하 통과 + SES 워밍업 가이드 + SOTA 회귀 통과 |
| 5 | **[Ops]** crosscutting/ops: SLO(잡 99% 성공, 발송 < 5min) + Temporal worker health + 채널별 발송 성공률 + SES 평판/FCM 토큰 alert + runbook | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 다채널 + Temporal + 평판 다축 | Grafana 5 패널 + Alertmanager 4 룰 + `/runbooks/ses-reputation-drop.md` + `/runbooks/temporal-worker-down.md` |

**Sprint 3 합계: 21 포인트**

**전체 합계: 63 포인트**
