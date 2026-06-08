## 스프린트 백로그 — 03. 논문 번역 (Translation)

> span 단위 학술체 한국어 번역. 도메인 용어는 `한국어(English)` 병기, anchor 1:1 매핑 보존.
> **glossary Owner 기능** (#02 요약과 공유) — AGENTS.md §6.2 glossing rule 단독 책임.
> 모듈 경계: `domain/translation/` + `crosscutting/{glossary,verifier,audit}/` + `infra/llm/`.
> 출처: `feature-specs/03-translation.md`.

---

### Sprint 1 — Translation MVP + Glossary Owner Schema

**Sprint 1 DoD:** 영문 span 선택 → 한국어 번역 결과 표시. **crosscutting/glossary 사전 스키마가 #02 요약에 export 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | **[Owner]** crosscutting/glossary: 세션 사전(Redis hash, TTL 24h) 스키마 + lookup 포트 — AGENTS.md §6.2 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Owner — #02 Sprint 2부터 의존 | Redis hash 스키마 + lookup 포트 export + 24h TTL 자동 만료 |
| 2 | domain/translation: Span Resolver — span(section_id, char_start, char_end) → 원문 + ±200자 컨텍스트 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 텍스트 추출 단순 | span → 원문+컨텍스트 반환 + p99 < 50ms + 잘못된 좌표 ValueError |
| 3 | domain/translation: Prompt Builder — §6 / 전문 / glossary cached + fresh user span | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 캐시 블록 4단, #02 패턴 재사용 | 4단 캐시 블록 + cache hit 검증 + structured prompt |
| 4 | **[depends-on #02]** infra/llm: 번역용 cache key + ephemeral block 추가 (어댑터 자체는 #02 Owner) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 wrapping + naming | 번역용 cache key naming + key 충돌 0건 |

**Sprint 1 합계: 10 포인트**

---

### Sprint 2 — Glossing Rule + Verifier + Side-by-Side UI

**Sprint 2 DoD:** 첫등장 `한국어(English)` 글로싱 강제 + verifier 10% sampling + anchor 1:1 매핑 보존 검증 + side-by-side 영-한 대조 UI 동작.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/translation: LaTeX 수식·인용 번호(`[12]`) 마스킹/복원 정규식 모듈 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정규식 단순, edge case 다수 | 10 LaTeX 패턴 + 5 citation 패턴 마스킹/복원 round-trip 무손실 |
| 2 | **[Owner]** crosscutting/glossary: 새 용어 매핑 누적 + 첫 등장 글로싱 강제 — AGENTS.md §6.2 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 누적 + 첫 등장 추적 | 첫 등장 `한국어(English)` 100% + 이후 한국어만 + 사용자 수정 시 재처리 |
| 3 | domain/translation: anchor 1:1 매핑 보존 검증 + 3문장 청크 제한 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | anchor 검증 + 청크 분할 | 1:1 매핑 정확도 95%+ + 3문장 청크 강제 |
| 4 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 (10% sampling 옵트인, §4.3) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 호출 + sampling | #02 포트 호출 + 10% sampling 동작 검증 |
| 5 | frontend: side-by-side 영-한 대조 보기 + hover 양방향 토글 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | hover 양방향 + 1:1 시각화 | 영→한 hover + 한→영 hover 양방향 + 1:1 시각화 |

**Sprint 2 합계: 18 포인트**

---

### Sprint 3 — 종결형 + Hardening

**Sprint 3 DoD:** `-한다` 체 통일 검증 + 장문 어순 재배치 회귀 통과 + glossary 오결정 전파 시나리오 처리 + 캐시 히트율 80%+ 검증.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/translation: 종결형 통일 후처리기 (`-합니다`체 → `-한다`체) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 종결형 + 한국어 어미 edge | 종결형 통일률 95%+ + 5 어미 edge case 처리 |
| 2 | crosscutting/audit: 번역 호출·캐시 히트·verify sampling(10%) 로깅 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Prometheus + Grafana | 3 메트릭 Grafana 대시보드 |
| 3 | tests: 장문 어순 재배치 회귀 + glossary 오결정 전파 시나리오 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 회귀 시드 + 복구 옵션 | 2 시드 시나리오 CI + 오결정 즉시 갱신 검증 |
| 4 | **[Ops]** crosscutting/ops: SLO(번역 < 10s) + LLM 비용 + glossary 일관성 위반 alert + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 운영 가시성 + 일관성 모니터 | Grafana 3 패널 + Alertmanager 2 룰 + `/runbooks/glossary-violation.md` |

**Sprint 3 합계: 13 포인트**

**전체 합계: 41 포인트**
