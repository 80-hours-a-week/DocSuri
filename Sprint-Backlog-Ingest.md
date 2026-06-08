## 스프린트 백로그 — 01b. 논문 인입 (Paper Ingest)

> #01a Search에서 선택된 논문의 PDF 다운로드 → GROBID 구조화 파싱 → 청크 + anchor 부여 → 임베딩 → Qdrant 저장.
> **#02 요약·#03 번역·#05 유사 탐색·#06/#07 분석·#10 reading·#11 priority의 입력 데이터 제공.** 인입 없으면 후속 기능 모두 빈 corpus.
> 모듈 경계: `domain/papers/` (ingest-side, search와 같은 모듈 내 분할) + `crosscutting/audit/` + `infra/{grobid,vectordb,embedding,storage}/`.
> 출처: `feature-specs/01-paper-search-and-ingest.md` (후반부), AGENTS.md §3.2/§4.2.

---

### Sprint 1 — PDF → GROBID Skeleton

**Sprint 1 DoD:** 사용자가 "PDF 요약" 클릭 → PDF 다운로드 → GROBID 구조화 XML 파싱 → 인입 상태 UI에 결과 표시. 청크·임베딩·벡터 저장 미포함.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | infra/grobid: GROBID Docker 컨테이너 셋업 (image + healthcheck + resource limit) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | Docker + Java 서비스 셋업 무거움 | dev/staging 컨테이너 + /isalive endpoint OK + 메모리 cap 적용 |
| 2 | infra/grobid: GROBID 호출 어댑터 + 구조화 XML → JSON 변환 (TEI 파서) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 호출 + 파싱 | PDF 1편 → 섹션/문단/문장 JSON 출력 + 단위 테스트 |
| 3 | domain/papers: PDF Fetcher — Unpaywall API → 직접 URL fallback | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | API + 다중 fallback | OA hit/fallback/paywall 3 시나리오 통합 테스트 |
| 4 | domain/papers: 인입 파이프라인 orchestrator (PDF Fetch → GROBID → 임시 in-memory 저장 / AGENTS.md §4.2 영속 금지) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 단계 합성 + in-memory 정책 강제 | 파이프라인 1편 end-to-end + PDF 임시 디스크 자동 삭제 검증 |
| 5 | frontend: 논문 인입 상태 UI (진행률 표시 + 단계 표시 + 실패 메시지) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | UI 상태 + WebSocket/SSE | "Fetch → Parse → Done" 진행률 + 실패 단계 표시 + 빈/에러 상태 |

**Sprint 1 합계: 13 포인트**

---

### Sprint 2 — Chunking + Embedding + Vector Insert

**Sprint 2 DoD:** GROBID 출력 → anchor 부여 청크 → 임베딩 → Qdrant 저장. **#02 요약 Sprint 1이 Retriever로 호출 가능 상태.**

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | infra/vectordb: Qdrant chunks collection 스키마 + payload(메타데이터 필터링용, AGENTS.md §3.2) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 스키마 변경 비용 큼, 우선 결정 | collection 생성 + payload 필터링 검증 + 인덱스 빌드 < 5분/논문 |
| 2 | domain/papers: Chunker — GROBID 섹션/문단 경계 우선, `(section_id, page, char_offset)` anchor 부여 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 알고리즘 + 수식/표 edge case | 섹션 경계 보존 99%+ + anchor 유일성 검증 + 100자 미만 청크 자동 병합 |
| 3 | **[depends-on #01a infra/embedding]** domain/papers: 청크 임베딩 호출 + Qdrant insert + 멱등성 (재실행 시 중복 0건) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | #01a 어댑터 + 멱등 키 + Vector insert | 임베딩 호출 + 멱등성(paper_id+chunk_id 키) + 중복 insert 0건 |
| 4 | frontend: 인입 완료 상세 (paper detail + 청크 개수 + 인덱스 위치) | 2 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 인입 결과 가시화 | paper detail + chunk count + Qdrant collection 위치 표시 |

**Sprint 2 합계: 13 포인트**

---

### Sprint 3 — Storage Policy + Resilience + Ops

**Sprint 3 DoD:** PDF 영속 저장 0건 감사 강제 + 부분 진행 복구 + GROBID 실패 회귀 통과 + SLO 출시.

| 우선순위 | 이름 (업무 항목) | 포인트 | 기간 | 담당자 | 이유 | DoD |
|---|---|---|---|---|---|---|
| 1 | crosscutting/audit: PDF 영속 저장 금지 강제 (AGENTS.md §4.2) — 임시 파일 디스크 잔존 0건 감사 | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 정책 강제 + 감사 + 라이선스 보호 | /tmp 잔존 0건 daily audit + 위반 시 Sentry alert |
| 2 | crosscutting/audit: 인입 실패 retry + 부분 진행 복구 (Fetch 성공 → GROBID 실패 시 PDF 재다운 없이 재파싱) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 부분 복구 + retry 정책 | 단계별 retry + 단계 복구 시 이전 단계 재실행 0건 |
| 3 | tests: paywall fallback + GROBID 실패 + 청크 경계 edge case + Qdrant 디스크 풀 | 5 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 4 실패 시나리오 + 회귀 | 4 시드 시나리오 회귀 CI + flake율 < 1% |
| 4 | **[Ops]** crosscutting/ops: SLO(인입 < 5분, GROBID 실패 < 5%) + Qdrant 디스크 사용량 + 임베딩 비용 + runbook (GROBID worker 다운) | 3 | 2099년 00월 00일 → 2099년 00월 00일 | [이름] | 운영 가시성 + 사고 대응 | Grafana 4 패널 + Alertmanager 3 룰 + `/runbooks/grobid-down.md` |

**Sprint 3 합계: 14 포인트**

**전체 합계: 40 포인트**
