# unit-of-work.md — 유닛 정의 (Units of Work)

**단계**: INCEPTION → Units Generation · **일자**: 2026-06-15
**근거**: `application-design/`(U1~U6), UQ1=A(6 유닛), UQ2=A(모노레포), UQ3=A(4 배포 단위), UQ4=A(데모 우선), UQ5=A(공유 계약 `shared/`).
**정의**: 유닛 = 개발용 스토리 논리 묶음. 모듈형 모놀리스(DQ1)이므로 일부 유닛은 한 배포 단위(API) 내 **모듈**, 일부는 **독립 배포**(워커·프런트).

---

## 유닛 정의

| 유닛 | 책임 | 유형 | 배포 단위 | 코드 위치 | 경로 종류 |
|---|---|---|---|---|---|
| **U1 Ingestion** | arXiv OA AI/ML 슬라이스 수집·청크·임베딩 → 공유 벡터 인덱스 생성·갱신(단일 writer) | 독립 워커 | ② 인제스천 워커 | `ingestion/` | 이벤트/스케줄 |
| **U2 Discovery** | 자연어 질의 동기 검색 읽기 경로(질의 이해·하이브리드 검색·랭킹·근거화 어댑팅·결과 조립) | API 모듈 | ① API | `backend/modules/discovery/` | 동기 REST |
| **U3 Accounts/Auth** | 가입/로그인/세션·자격증명·**객체 소유권 인가 단일 결정점** | API 모듈 | ① API | `backend/modules/accounts/` | 동기 REST(+이벤트 신호) |
| **U4 Library** | 검색 저장·라이브러리·이력(소유자 비공개) | API 모듈 | ① API | `backend/modules/library/` | 동기 CRUD(+이력 이벤트 소비) |
| **U5 Frontend** | SSR 폰 우선 웹 UI(검색·결과·계정·라이브러리·상태; 폰 목업 프레임) | 독립 프런트 | ④ 프런트엔드 | `frontend/` | 동기 REST(클라이언트) |
| **U6 Reliability/Ops** | DQ5 횡단 미들웨어/게이트웨이(API 내) + 운영 워커(탐지·대시보드) | 미들웨어 + 워커 | ① API(게이트웨이) · ③ Ops 워커(탐지·대시보드) | `backend/middleware/` · `ops/` | 동기 게이트 + 이벤트 백본 |

> **U6 분할 주석**: U6는 두 곳에 산다 — (a) **게이트웨이 미들웨어**(authn/authz·검증·레이트리밋·비용 상태·근거화 강제 후크)는 API 배포 단위 ① 내부, (b) **Ops 워커**(AI 인시던트 탐지기·대시보드)는 이벤트 백본 소비 독립 워커 ③.

## 배포 단위 (UQ3=A)
1. **API 서비스** — U2 + U3 + U4 + U6 게이트웨이 미들웨어 (동기 REST, 모듈형 모놀리스)
2. **인제스천 워커** — U1 (이벤트/스케줄)
3. **Ops/탐지 워커** — U6 탐지기·대시보드 (이벤트 백본)
4. **프런트엔드** — U5 (SSR)

공유 capability(기술 미확정): 벡터 인덱스, 관리형 DB/영속화, 이벤트 버스/백본, 오브젝트 스토리지, 임베딩/LLM 게이트웨이, DLQ.

## 코드 조직 전략 (Greenfield, UQ2=A 모노레포)
```text
<repo-root>/
├── frontend/                # U5 — SSR 폰 우선 웹 (배포 ④)
├── backend/                 # 배포 ① API (모듈형 모놀리스)
│   ├── modules/
│   │   ├── discovery/       # U2
│   │   ├── accounts/        # U3
│   │   └── library/         # U4
│   └── middleware/          # U6 게이트웨이(authn/authz·검증·레이트리밋·비용·근거화 후크)
├── ingestion/               # U1 — 인제스천 워커 (배포 ②)
├── ops/                     # U6 — 탐지기·대시보드 워커 (배포 ③)
└── shared/                  # UQ5=A 공유 계약 단일 소유
    ├── vector-spec          # 임베딩 스키마(U1 writer ↔ U2 reader 동일 공간 불변식)
    ├── dtos                 # 결과/카드/계정/라이브러리 DTO
    ├── events               # 이벤트 스키마(SearchExecuted, AI 인시던트)
    └── ports                # 횡단 후크 인터페이스(근거화·비용) — 의존성 역전(코드 순환 방지)
```
구체 언어·프레임워크·런타임은 **NFR Requirements/Construction**에서 확정(이전 사이클 Python 백엔드 + Next.js 프런트는 선행 사례).

## 빌드/개발 순서 (UQ4=A 데모 우선)
1. **U1 Ingestion** — 코퍼스·인덱스가 있어야 검색 가능(US-I1 시드 빌드 우선).
2. **U2 Discovery** (+ U6 게이트웨이 미들웨어 최소 스캐폴드) — 동기 검색 경로.
3. **U5 Frontend** — 히어로 US-H1 종단 동작(매직 모먼트 가시화).
4. **U3 Accounts** — 공개 가입/로그인.
5. **U4 Library** — 검색 저장·라이브러리·이력.
6. **U6 Reliability/Ops 강화** — 비용 가드·AI 인시던트 탐지·관측성·헬스 전면화(게이트웨이 최소본은 2단계에서 선행).

> 각 유닛은 CONSTRUCTION의 유닛별 루프(Functional/NFR/Infra Design → Code Generation)로 진행한다.
