# unit-of-work-dependency.md — 유닛 의존성 매트릭스

**단계**: INCEPTION → Units Generation · **일자**: 2026-06-15
**근거**: `application-design/component-dependency.md`. 종류: **sync**(동기 호출/REST), **event**(이벤트 백본, 비동기), **lib**(빌드 시 공유 계약/인터페이스 의존).

---

## 의존성 매트릭스 (from → to)

| from \\ to | U1 | U2 | U3 | U4 | U5 | U6 | U7 | shared |
|---|---|---|---|---|---|---|---|---|
| **U1 Ingestion** | — | — | — | — | — | event(인시던트/관측 발행) | — | lib(VectorSpec·이벤트) |
| **U2 Discovery** | (인덱스 read = capability, 코드 의존 아님) | — | — | event(SearchExecuted 발행) | — | lib(근거화·비용 후크 via `shared/ports`) | — | lib(VectorSpec·DTO) |
| **U3 Accounts** | — | — | — | — | — | — | — | lib(DTO) |
| **U4 Library** | — | event(SearchExecuted 소비) | sync(인가 결정 위임) | — | — | — | — | lib(DTO) |
| **U5 Frontend** | — | sync(REST, 게이트웨이 경유) | sync(REST) | sync(REST) | — | sync(게이트웨이 진입) | sync(REST, 게이트웨이 경유) | lib(DTO) |
| **U6 Reliability/Ops** | event(인제스천 신호 소비) | sync(게이트웨이→U2 핸들러 호출) | sync(authz 위임 호출) | sync(게이트웨이→U4 핸들러) | — | — | sync(게이트웨이→U7 핸들러) | lib(이벤트·ports) |
| **U7 Summarization** | (전문 원본 S3 read = capability, 코드 의존 아님) | — | — | — | — | lib(근거화·비용 후크 via `shared/ports`) + event(관측/비용 발행) | — | lib(DTO·ports) |
| **shared** | — | — | — | — | — | — | — | — (leaf) |

> U5 사용자 경로는 **U6 게이트웨이를 단일 진입**으로 U2/U3/U4/**U7** 핸들러에 도달한다(표의 U5→U2/U3/U4/U7 sync는 게이트웨이 프런티드).
> **U7은 U2와 동일 의존 패턴**: U1 전문 원본은 capability read(코드 의존 아님), U6 근거화·비용 후크는 `shared/ports` 인터페이스 의존(U6 구현) → U7↔U6 코드 순환 없음.

## 통신 패턴
- **동기 REST**(NFR-P1 읽기 경로): U5 → U6 게이트웨이 → U2/U3/U4 핸들러 → 응답. U4 rerun도 동일 경로 재진입(백도어 금지).
- **이벤트 백본**(비동기): new-arXiv → U1; U2 `SearchExecuted` → U4(이력); 탐지기(비용/할루시네이션/반쪽짜리) → IncidentEventPublisher; 관측성 팬아웃.
- **lib(의존성 역전)**: 횡단 후크(근거화·비용) 인터페이스는 `shared/ports`에 정의, U6가 구현, U2가 인터페이스에 의존 → **코드 순환 없음**.

## 비순환 검증 (코드 의존 그래프)
- `shared`는 leaf(무의존). U1/U2/U3/U4/U5는 `shared`에만 lib 의존.
- U4 → U3: 인가 결정 위임(sync, 단방향).
- U6 → U2/U3/U4: 게이트웨이가 핸들러 호출(런타임 호출, 단방향). U2 → U6는 **코드 의존이 아님**(U2는 `shared/ports` 인터페이스에 의존; U6가 구현) → U2↔U6 코드 순환 없음.
- U2 ↔ U4: `SearchExecuted`는 **event**(비동기) — 코드 순환 아님.
- U2 → U1: 벡터 인덱스는 **공유 capability**(런타임 데이터 의존), 코드 의존 아님(U1 단일 writer, U2 단일 reader).
- **U7 → U1**: 전문 원본은 **공유 capability**(S3 텍스트 read, 런타임 데이터 의존), 코드 의존 아님(U1 단일 writer, U7 reader). U7 → U6도 `shared/ports` 인터페이스 의존(U6 구현) → U7↔U6 코드 순환 없음(U2와 동형). U6 → U7은 게이트웨이가 핸들러 호출(런타임, 단방향).
- **결론**: 코드 의존 그래프 비순환(DAG) — U7 추가 후에도 유지. 런타임 호출/이벤트는 단방향 또는 비동기로 순환 없음.

## ASCII 흐름도

### 동기 디스커버리 읽기 (NFR-P1)
```text
U5 ──REST──> U6 게이트웨이 ──> U2(질의→검색→랭킹→근거화어댑터→조립) ──> 응답
                  │  (authz는 U3 위임, 근거화/비용 후크 주입)
                  └──> [응답 엣지] U6 GroundingEnforcementHook (단일 권위)
```
### 온디맨드 요약/번역 (U7, NFR-P2 — 검색 SLA 비대상)
```text
U5 ──REST──> U6 게이트웨이 ──> U7(STORE 조회→비용게이트→전문 fetch→정제→LLM→근거화→저장)
                  │  (authz는 U3 위임, 근거화/비용 후크 주입)
                  ├──> [캐시 HIT] Redis/S3 즉시 반환 (LLM 0콜)
                  ├──> [비용게이트 OPEN] 요약 일시 기권(FR-11)
                  └──> [응답 엣지] U6 GroundingEnforcementHook (근거 없으면 기권)
U7 전문 read <── 공유 capability(S3, U1 writer) ;  U7 결과 ──> S3 영구 + Redis 핫
```
### 인제스천 (이벤트/스케줄)
```text
new-arXiv 이벤트 / 스케줄 ──> U1 워커 ──> (fetch→parse→chunk→embed) ──> 공유 벡터 인덱스(write)
                                              └─실패─> DLQ/재시도/경보(U6 관측)
```
### 이력·인시던트 (이벤트 백본)
```text
U2 ──SearchExecuted(event)──> U4 SearchHistory
U2/U6 ──근거화 위반/비용 급증/반쪽짜리(event)──> U6 탐지기 ──> IncidentEventPublisher ──> Ops 대시보드
```
