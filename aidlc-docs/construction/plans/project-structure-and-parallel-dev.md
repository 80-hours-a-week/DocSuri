# project-structure-and-parallel-dev.md — 프로젝트 구조 + 병렬 개발 조율 (제안)

**단계**: CONSTRUCTION → 병렬 트랙 착수 전 구조/조율 제안 · **일자**: 2026-06-16 · **상태**: 🟡 **제안(팀 승인 대기)** — 승인 전 디렉터리/파일 미생성
**근거**: `unit-of-work.md`(UQ2=A 모노레포·코드 조직·4 배포 단위·UQ5=A `shared/` 단일 소유) · `execution-plan.md`(3 트랙) · U1 FD/NFR/NFR Design(Python·OpenSearch·Cohere…) · `shared/` 계약 5종
**목적**: 팀원 3명이 3 트랙을 **충돌 없이 병렬 개발**하도록 (1) 디렉터리 구조·소유, (2) 조율 존, (3) 브랜치/변경 프로토콜, (4) 지금 세울 것 vs 트랙별로 미룰 것, (5) **선결 결정**을 합의.

---

## 1. 모노레포 트리 (unit-of-work.md 확정) + 배포 단위

```text
<repo-root>/
├── frontend/                # U5 — SSR 폰 우선 웹            ……… 배포 ④
├── backend/                 # 모듈형 모놀리스 API(단일 런타임) … 배포 ①
│   ├── (app shell)          #   부트스트랩·라우터·DI·공통 미들웨어 결선  ⚠️ 조율 존
│   ├── modules/discovery/   #   U2
│   ├── modules/accounts/    #   U3
│   ├── modules/library/     #   U4
│   └── middleware/          #   U6 게이트웨이(authn/authz·검증·레이트·근거화 후크)  ⚠️ 조율 존
├── ingestion/               # U1 — 인제스천 워커              ……… 배포 ②
├── ops/                     # U6 — 탐지기·대시보드 워커        ……… 배포 ③
└── shared/                  # 공용 계약(단일 소유 UQ5=A)       ⚠️ 조율 존
    ├── vector-spec  ├── dtos  ├── events  └── ports
```

**배포 단위 4**: ① backend API(U2+U3+U4+U6-미들웨어) · ② ingestion 워커(U1) · ③ ops 워커(U6 탐지기) · ④ frontend(U5).

> **핵심**: 배포 ①(backend)은 **하나의 모듈형 모놀리스** — U2·U3·U4 모듈과 U6 미들웨어가 **같은 앱·같은 런타임**에 공존한다. 따라서 backend 모듈들은 스택을 **독립적으로 고르지 않는다**(아래 §5-A).

## 2. 트랙 ↔ 디렉터리 소유 (팀원 3명)

| 트랙 | 소유자(2026-06-16 배정) | 유닛 흐름 | 소유 디렉터리(클린 레인) | 배포 단위 |
|---|---|---|---|---|
| **Track 1** | **@ELSAPHABA** | U1 → U6 | `ingestion/`, `ops/` | ②, ③ |
| **Track 2** | **@revenantonthemission** | U3 → U4 | `backend/modules/accounts/`, `backend/modules/library/` | ① |
| **Track 3** | **@kyjness** | U2(mock 선행) → U5 | `backend/modules/discovery/`, `frontend/` | ①, ④ |

- **클린 레인(낮은 충돌)**: `ingestion/`·`ops/`·`frontend/`·`backend/modules/{discovery,accounts,library}/` — 각 트랙 단독 소유, 파일 겹침 최소.
- **⚠️ 조율 존(다수 트랙이 손댐 — 소유자+프로토콜 필요)**:
  1. **`shared/`** — 3 트랙 모두 소비(UQ5=A 단일 소유).
  2. **`backend/` app shell + `backend/middleware/`** — backend 모듈 3개(T1 미들웨어·T2 accounts/library·T3 discovery)가 **같은 앱**에 결선. 부트스트랩·라우터·DI·공통 미들웨어는 공유 표면.

## 3. 조율 존 소유 & 변경 프로토콜
> **배정(2026-06-16)**: Track1 @ELSAPHABA · Track2 @revenantonthemission · Track3 @kyjness. **`.github/CODEOWNERS` 작성됨**(PR #38 포함). 조율 존 소유자는 **기본값(확인 요)**: `shared/` → @revenantonthemission, `backend/` app-shell → @ELSAPHABA.

- **`shared/` 소유자 = @revenantonthemission**(기본값; UQ5=A 단일 소유). **계약 변경은 `shared/` 전용 PR + 3 트랙 사인오프**(변경이 전 트랙에 파급). 트랙 브랜치 안에서 `shared/`를 직접 편집 금지.
- **`backend/` app shell 소유자 = @ELSAPHABA**(기본값; U6 게이트웨이/미들웨어가 shell의 횡단 관심사). 모듈 팀은 자기 `modules/*`만; app shell/미들웨어 결선 변경은 소유자 경유.
- **CODEOWNERS 강제**(리뷰 라우팅, last-match-wins): `.github/CODEOWNERS` — 조율 존 → 지정 소유자, 각 레인 → 트랙. develop 브랜치 보호에서 "require review from Code Owners" 활성 권장.

## 4. 브랜치 전략 (git-flow, RES-3)
- **선결 랜딩**: PR #37(설계+계약 specs) 머지 → (승인 시) `shared/` 코드 패키지 + backend app-shell 스캐폴드를 **develop에 먼저 랜딩**.
- **트랙 브랜치**: 3 트랙은 `shared/`·app-shell 포함된 **develop에서 분기**(`feature/track1-…`, `feature/track2-…`, `feature/track3-…`). 각 트랙 PR → develop. 정기 리베이스/머지로 동기.
- **U2 mock(Track 3)**: U5는 `shared/dtos`(SearchResponse 계약) 기반 **mock U2 응답**으로 선행 — U2 실 구현 전 병렬 진행.

## 5. ⚠️ 선결 결정 (팀 합의 필요 — 병렬 착수 전)
- **A. backend 공유 스택** *(가장 중요)* — backend(①)는 단일 모놀리스라 **U2/U3/U4/U6-미들웨어가 한 언어/프레임워크 공유**. ⇒ backend 스택은 **유닛별이 아니라 시스템(backend-플랫폼) 결정**이며 **Track 2·3 구현 전 확정 필요**. U1=Python 잠금 고려 시 backend=Python 유력(미확정). _권장: backend 플랫폼 스택을 별도 결정(또는 U3/U2 중 먼저 NFR Requirements 진입하는 유닛에서 시스템 결정으로 격상)._
- **B. polyglot `shared/` 계약 포맷** — Python 서비스 + TS 프런트(유력) ⇒ `shared/` 계약을 **언어 중립 SSOT(JSON Schema/OpenAPI → Python·TS 타입 생성)** vs **언어별 수기 유지** 중 택. _권장: 언어 중립 SSOT(드리프트 방지)._
- ✅ **C. 소유자**(2026-06-16): 트랙 3인 배정 + `.github/CODEOWNERS` 작성. 조율 존 소유자는 **기본값**(`shared/` @revenantonthemission · `backend/` app-shell @ELSAPHABA) — **팀 확인 요**.
- **D. frontend·ops 스택** — 각 트랙 NFR Requirements에서(독립 배포라 backend와 분리 가능; frontend=TS/SSR 유력).

## 6. 지금 세울 것 vs 트랙별 미룰 것
| | 지금(승인 시 선행) | 트랙별(각 유닛 루프) |
|---|---|---|
| 디렉터리 | 위 §1 전체 트리(빈 디렉터리 + 레인별 README/소유) | 각 디렉터리 내부 구조 |
| `shared/` | 계약 코드 패키지(§5-B 포맷 결정 후) | 계약은 동결(변경은 §3 프로토콜) |
| backend | app-shell 스캐폴드(§5-A 스택 결정 후) | 각 모듈 구현 |
| 루트 규약 | `.gitignore`·`docker-compose`(스텁)·CODEOWNERS·README·CI 스켈레톤 | 언어별 deps/lint/test(스택 확정 유닛부터) |

> 루트 언어별 툴링은 **스택 확정된 것부터**(U1=Python 확정 → ingestion/shared-py 가능; backend/frontend는 §5-A/D 후).

---

## 7. 권장 순서 (승인 시)
1. §5 선결 결정(A backend 스택·B shared 포맷·C 소유자) 합의.
2. develop에 **모노레포 스켈레톤 + 루트 규약 + `shared/` 코드 패키지 + backend app-shell** 랜딩(조율 존 선행).
3. 3 트랙 develop에서 분기 → 병렬 개발(각 유닛 CONSTRUCTION 루프).

> **리뷰 게이트**: 본 제안 승인 시 §7 순서로 스캐폴드. 승인 전 디렉터리/파일 미생성. 미해결은 §5(특히 A backend 공유 스택)가 병렬 착수의 실질 선결 조건.
