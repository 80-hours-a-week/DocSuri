# 유닛 분해 계획 (Unit of Work Plan)

**단계**: INCEPTION → Units Generation (Part 1: 계획) · **일자**: 2026-06-15
**입력**: `application-design/`(U1~U6 컴포넌트·서비스·의존성), `stories.md`(21개), `execution-plan.md`.
**목표**: 시스템을 개발 단위(unit of work)로 공식 분해 — 경계·의존성·스토리 매핑·코드 조직(Greenfield)·빌드 순서.

아래 질문에 답하거나(또는 **"approve plan"** 으로 권장안 수락) 후, 유닛 산출물을 생성한다.

---

## 분해 질문 (Decomposition Questions)

## UQ1 — 유닛 집합
Application Design의 6 유닛(U1~U6)을 그대로 개발 단위로 확정할까?

A) **6 유닛 그대로(권장)** — U1 Ingestion / U2 Discovery / U3 Accounts / U4 Library / U5 Frontend / U6 Reliability·Ops. 설계와 1:1.

B) U6를 유닛이 아닌 횡단 관심사로 흡수 → 5 유닛(미들웨어는 API에 내장, 탐지/대시보드만 별도).

C) 기타 재그룹핑(아래 기술).

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: A (approve plan — 권장안 수락)

## UQ2 — 코드 조직 / 리포 구조 (Greenfield)
디렉터리·배포 구조는?

A) **모노레포(권장)** — `frontend/`(SSR 폰 우선) · `backend/`(모듈형 모놀리스 API: `modules/discovery|accounts|library`, `middleware/`(U6 게이트웨이)) · `ingestion/`(U1 워커) · `ops/`(U6 탐지·대시보드 워커) · `shared/`(공유 계약: VectorSpec·DTO·이벤트 스키마).

B) 멀티 레포(유닛별 분리 저장소).

C) 단일 앱 단일 디렉터리.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: A (approve plan — 권장안 수락)

## UQ3 — 배포 단위 매핑
런타임 배포 단위(모듈형 모놀리스 전제)는?

A) **4 배포 단위(권장)** — ① API 서비스(U2+U3+U4+U6 게이트웨이 미들웨어, 동기 REST) ② 인제스천 워커(U1, 이벤트/스케줄) ③ Ops/탐지 워커(U6 탐지기·대시보드, 이벤트 백본) ④ 프런트엔드(U5, SSR). 공유 벡터 인덱스·DB·이벤트 버스·오브젝트 스토리지는 공유 capability.

B) 3 배포 단위(Ops를 API에 흡수).

C) 기타.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: A (approve plan — 권장안 수락)

## UQ4 — 빌드/개발 순서
어떤 순서로 구축할까? (각 유닛은 CONSTRUCTION 유닛별 루프로 진행)

A) **데모 우선 / 히어로 경로(권장)** — U1 Ingestion → U2 Discovery → U5 Frontend(히어로 US-H1 동작) → U3 Accounts → U4 Library → U6 Reliability·Ops 강화. 매직 모먼트를 가장 먼저 가시화.

B) 파운데이션 우선 — U6 미들웨어 + U3 Accounts 먼저(공통 게이트·인증), 이후 디스커버리.

C) 기타.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: A (approve plan — 권장안 수락)

## UQ5 — 공유 계약 소유권
공유 계약(VectorSpec 임베딩 스키마, 결과/DTO, 이벤트 스키마)은 어디서 소유?

A) **`shared/` 공유 패키지 단일 소유(권장)** — U1 writer·U2 reader가 동일 VectorSpec 소비; 이벤트 스키마(SearchExecuted·AI 인시던트) 공유. 버전·호환 한 곳 관리.

B) 생산자 유닛이 각자 소유·노출.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: A (approve plan — 권장안 수락)

---

## 필수 유닛 산출물 (답변·승인 후 생성)
- [x] `application-design/unit-of-work.md` — 유닛 정의·책임 + **코드 조직 전략(Greenfield)**
- [x] `application-design/unit-of-work-dependency.md` — 유닛 의존성 매트릭스(동기/이벤트/공유)
- [x] `application-design/unit-of-work-story-map.md` — 스토리(21개) → 유닛 매핑(전수 할당 검증)
- [x] 유닛 경계·의존성 검증, 모든 스토리 유닛 할당 확인

## 생성 단계 (승인 후)
- application-design/ + stories.md 기반으로 3 산출물 생성, 스토리 전수 매핑·의존성 비순환 검증. (설계가 이미 확정적이므로 직접 생성 + 정합 검증; 필요 시 경량 비평.)
