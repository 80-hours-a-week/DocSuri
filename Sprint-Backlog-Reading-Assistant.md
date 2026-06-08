## 스프린트 백로그 — 10. Research Reading Assistant (논문 읽기·이해 지원)

> ⚠️ AGENTS.md §1.3 Non-goal 충돌 해소 — "Reading 한정" 재정의(옵션 C) 적용.
> 4 서브기능: Literature Map / Citation Candidate / Peer Review Simulation / Concept Sparring + 연구 일지.
> 모듈 경계: `domain/reading/` + `crosscutting/{verifier,anchor,safety,audit}/` + `infra/{llm,vectordb,storage}/`.
> 출처: `feature-specs/10-research-reading-assistant.md`.

---

### Sprint 1 — Safety Guard + Citation Candidate (최빈도 서브기능 1개)

**Sprint 1 DoD:** §1.3 가드(쓰기 금지) 적용 + Citation Candidate 서브기능 단독 동작 (user sentence → top-5 후보 + abstract 미리보기 + 인용 format) + ZDR. 다른 3 서브기능 비활성.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | crosscutting/safety: system prompt에 "쓰기 대신 작성" 금지 가드 + 출력 후 검증 hook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | §1.3 정책 — 모든 출력 가드 | system prompt 가드 + 출력 검증 + 위반 시 거부 |
| 2 | infra/llm: ZDR(Zero Data Retention) 옵션 + 미공개 아이디어 격리 (no LLM memory) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | ZDR + 정책 점검 | ZDR header 적용 + LLM memory off 검증 |
| 3 | domain/reading: Citation Candidate — user sentence → 임베딩 ANN → Sonnet rerank top-5 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | ANN + Sonnet rerank | sentence → top-5 후보 + abstract 포함 |
| 4 | domain/reading: Citation Candidate 인용 format(APA/IEEE/MLA) + abstract 미리보기 강제 | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 형식 변환 + abstract 강제 | 3 형식 변환 단위 테스트 + abstract 100% 첨부 |
| 5 | frontend: 4 서브기능 탭 (Citation만 활성) + "AI 보조" 마커 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 탭 UI + 마커 + 비활성 | 4 탭 + Citation 활성 + 3 비활성 + AI 보조 마커 |

**Sprint 1 합계: 13 포인트**

---

### Sprint 2 — 나머지 3 서브기능 + Anchor/Verifier

**Sprint 2 DoD:** Peer Review Simulation (4 rubric) + Concept Sparring (강도 옵트인) + Literature Map (#06+#05 결합) 동작 + 모든 출력에 anchor + verifier 환각 검증.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/reading: Peer Review Simulation (Claude Opus) — novelty/method/eval/clarity rubric | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 rubric + Opus + 합성 | 4 rubric 정의 + 항목별 LLM 코멘트 + 합성 리포트 |
| 2 | domain/reading: Concept Sparring (Claude Opus) — corpus 반례 검색 + 도전적 질문 (강도 옵트인) | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 반례 + 도전 + 강도 | 반례 검색 + 도전 질문 + 강도 슬라이더 3단계 |
| 3 | domain/reading: Literature Map — 06(gap) + 05(similar) 결합 호출 + 구조화 정리 합성     | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 두 기능 결합 + 합성 | #06+#05 호출 + 구조화 출력 + 정리 표 |
| 4 | **[depends-on #02]** crosscutting/anchor: anchor 포트 호출 (4 서브기능 출력 모두, §4.4) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 포트 × 4 | #02 호출 × 4 서브기능 + 100% anchor |
| 5 | **[depends-on #02]** crosscutting/verifier: verifier 포트 호출 (인용 적합도 + Peer Review/Sparring, §4.3) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #02 + 다중 적용 | #02 호출 + 3 서브기능 적용 + 라벨 노출 |

**Sprint 2 합계: 19 포인트**

---

### Sprint 3 — Notebook + Policy Telemetry + Hardening

**Sprint 3 DoD:** 연구 일지 Postgres + Markdown export + 학술 윤리 ToS + 사용 패턴 텔레메트리(옵션 A 결정 입력) + 작성 보조 슬립퍼리 슬로프 회귀 통과.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | domain/reading: 연구 일지 (notebook) — Postgres + Markdown export + 사용자 소유 강조 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 일지 CRUD + export | CRUD + Markdown export + 사용자 소유 권한 |
| 2 | crosscutting/audit: 학술 윤리 ToS 게시 + 대학 통합 시 별도 정책 + 산출물 마커 로그 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | ToS + 로그 + 정책 | ToS 게시 + 산출물 마커 로그 + 대학 정책 분기 |
| 3 | domain/reading: 사용 패턴 데이터 수집 — 옵션 A(AGENTS.md §1 확장) 의사결정 입력 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 텔레메트리 + 대시보드 | 사용 패턴 4 메트릭 + 대시보드 + 익명화 |
| 4 | tests: "작성 보조" 슬립퍼리 슬로프 회귀 + 인용 후보 적합도 + cold-start Citation Candidate | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 3 시드 + 슬립퍼리 측정 | 3 시드 시나리오 CI + 슬립퍼리 슬로프 측정 |
| 5 | **[Ops]** crosscutting/ops: SLO(서브기능 < 10s) + safety 가드 위반 alert + ZDR 활성 확인 + 학술 윤리 ToS 위반 텔레메트리 + runbook | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 안전 + 윤리 다축 | Grafana 3 패널 + Alertmanager 3 룰 + `/runbooks/safety-guard-violation.md` |

**Sprint 3 합계: 17 포인트**

**전체 합계: 49 포인트**
