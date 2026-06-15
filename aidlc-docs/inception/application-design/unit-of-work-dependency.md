# unit-of-work-dependency.md — 유닛 의존성 매트릭스

**단계**: INCEPTION → Units Generation · **일자**: 2026-06-15
**근거**: `application-design/component-dependency.md`. 종류: **sync**(동기 호출/REST), **event**(이벤트 백본, 비동기), **lib**(빌드 시 공유 계약/인터페이스 의존).

---

## 의존성 매트릭스 (from → to)

| from \\ to | U1 | U2 | U3 | U4 | U5 | U6 | shared |
|---|---|---|---|---|---|---|---|
| **U1 Ingestion** | — | — | — | — | — | event(인시던트/관측 발행) | lib(VectorSpec·이벤트) |
| **U2 Discovery** | (인덱스 read = capability, 코드 의존 아님) | — | — | event(SearchExecuted 발행) | — | lib(근거화·비용 후크 via `shared/ports`) | lib(VectorSpec·DTO) |
| **U3 Accounts** | — | — | — | — | — | — | lib(DTO) |
| **U4 Library** | — | event(SearchExecuted 소비) | sync(인가 결정 위임) | — | — | — | lib(DTO) |
| **U5 Frontend** | — | sync(REST, 게이트웨이 경유) | sync(REST) | sync(REST) | — | sync(게이트웨이 진입) | lib(DTO) |
| **U6 Reliability/Ops** | event(인제스천 신호 소비) | sync(게이트웨이→U2 핸들러 호출) | sync(authz 위임 호출) | sync(게이트웨이→U4 핸들러) | — | — | lib(이벤트·ports) |
| **shared** | — | — | — | — | — | — | — (leaf) |

> U5 사용자 경로는 **U6 게이트웨이를 단일 진입**으로 U2/U3/U4 핸들러에 도달한다(표의 U5→U2/U3/U4 sync는 게이트웨이 프런티드).

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
- **결론**: 코드 의존 그래프 비순환(DAG). 런타임 호출/이벤트는 단방향 또는 비동기로 순환 없음.

## ASCII 흐름도

### 동기 디스커버리 읽기 (NFR-P1)
```text
U5 ──REST──> U6 게이트웨이 ──> U2(질의→검색→랭킹→근거화어댑터→조립) ──> 응답
                  │  (authz는 U3 위임, 근거화/비용 후크 주입)
                  └──> [응답 엣지] U6 GroundingEnforcementHook (단일 권위)
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
