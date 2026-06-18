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
| **U7 Summarization** *(2026-06-18 편입)* | 검색된 단일 논문의 온디맨드 요약(Sonnet)·초록 번역(Haiku)·개인화(persona/뷰/용어집); 근거 앵커·기권; 영구저장(S3)+핫캐시(Redis) | API 모듈(+초장문 비동기 잡 옵션) | ① API (+③ 비동기 잡 옵션) | `backend/modules/summarization/` | 동기 REST(스트리밍) + 이벤트(관측/비용) |

> **U6 분할 주석**: U6는 두 곳에 산다 — (a) **게이트웨이 미들웨어**(authn/authz·검증·레이트리밋·비용 상태·근거화 강제 후크)는 API 배포 단위 ① 내부, (b) **Ops 워커**(AI 인시던트 탐지기·대시보드)는 이벤트 백본 소비 독립 워커 ③.

> **U7 주석 (요약/번역)**: U7은 결과 카드의 **온디맨드 보조 기능**(검색 SLA NFR-P1 비대상, NFR-P2). U6 게이트웨이를 단일 진입으로 도달하며, **U1 전문 원본(S3 read = capability)·U6 근거화 후크/비용 게이트(`shared/ports` lib)에 의존**한다(U2와 동일 패턴 — 코드 순환 없음). LLM 호출은 U2 검색과 별개 경로. 대부분 단일 콜 동기 스트리밍, **초장문(map-reduce)만 비동기 잡**(배포 ③). 산출물은 S3 영구 + Redis 핫캐시(키 immutable, 논문당 평생 1회 생성).

## 배포 단위 (UQ3=A)
1. **API 서비스** — U2 + U3 + U4 + **U7** + U6 게이트웨이 미들웨어 (동기 REST, 모듈형 모놀리스)
2. **인제스천 워커** — U1 (이벤트/스케줄)
3. **Ops/탐지 워커** — U6 탐지기·대시보드 (이벤트 백본) **(+ U7 초장문 요약 비동기 잡 옵션)**
4. **프런트엔드** — U5 (SSR)

공유 capability(기술 미확정): 벡터 인덱스, 관리형 DB/영속화, 이벤트 버스/백본, 오브젝트 스토리지, 임베딩/LLM 게이트웨이, DLQ. **(U7 추가 활용: 오브젝트 스토리지[전문 read + 요약 영구저장]·핫캐시[Redis]·LLM 게이트웨이[Sonnet/Haiku].)**

## 코드 조직 전략 (Greenfield, UQ2=A 모노레포)
```text
<repo-root>/
├── frontend/                # U5 — SSR 폰 우선 웹 (배포 ④)
├── backend/                 # 배포 ① API (모듈형 모놀리스)
│   ├── modules/
│   │   ├── discovery/       # U2
│   │   ├── accounts/        # U3
│   │   ├── library/         # U4
│   │   └── summarization/   # U7 — 요약/번역(온디맨드, Sonnet/Haiku)
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

## 빌드/개발 순서 (병렬화 조율 반영 - 2026-06-16)
개발 기간 단축을 위해 `shared/` 공용 규약을 선행 작성한 뒤, 아래와 같이 3개 독립 트랙으로 병렬 개발을 진행합니다.

* **준비 단계**: `shared/` 규약 고정 (`vector-spec` 및 API DTO, 이벤트 스펙 선행 작성)
* **[트랙 1] 데이터 파이프라인**: **U1 Ingestion** (인제스천 워커) ──> **U6 Reliability/Ops** (비동기 탐지 워커)
* **[트랙 2] 인증 및 사용자 데이터**: **U3 Accounts** (가입/로그인) ──> **U4 Library** (저장/라이브러리)
* **[트랙 3] 사용자 검색 및 UI**: **U2 Discovery** (Mock API 기반 선행 개발) ──> **U5 Frontend** (UI 화면 및 인터랙션)
* **[확장 / 2026-06-18] 요약·번역**: **U7 Summarization** — 코어(U1~U6) 빌드·배포 완료 후 편입되는 신규 유닛. **선행 의존**: U1(전문 원본 S3)·U6(근거화 후크·CostGuard)·shared(DTO·ports) = 이미 가용. 결과 카드 표면은 U2/U5와 연결. 단일 트랙으로 CONSTRUCTION 유닛 루프 진행(mock-first 권장 — LLM 어댑터 seam).

> 각 유닛은 CONSTRUCTION의 유닛별 루프(Functional/NFR/Infra Design → Code Generation)로 진행한다.
