# DocSuri AI-DLC 프롬프트 로그 (사이클 2 — 재시작)

이 파일은 AI-DLC 세션 동안 사용자에게 받은 모든 프롬프트를 시간순(append-only)으로 기록합니다.
각 항목은 `## Prompt N — YYYY-MM-DD` 형식으로 구분합니다.

> **재시작 메모 (2026-06-15)** — 이전 사이클(요구사항 → 스토리 → unit → 컴포넌트 모델 → ADR → U0~U4 빌드 →
> 풀스택 라이브 데모)을 사용자 지시로 **처음부터 재시작**했습니다.
> - **레포 블랭크 슬레이트**: `aidlc-docs/`·`backend/`·`frontend/`·`amplify.yml`·`README.md` 삭제(추적 165파일).
>   `.github/`(CODEOWNERS·이슈/PR 템플릿)·`.gitignore`만 유지.
> - **라이브 AWS 인프라 전체 해체**: Bedrock KB `VSQ5KSCBMY` · S3 Vectors(인덱스+버킷) · 소스 코퍼스 버킷 ·
>   DynamoDB 3테이블 · `docsuri-kb-role` · Lambda `docsuri-api` · API Gateway `74vuv58ct7` ·
>   `docsuri-lambda-role` · ECR `docsuri-backend` · CloudWatch 로그 그룹 · Amplify Hosting 앱 `d2gnwz547zl2ru`.
> - 이전 산출물·코드는 git 이력(`ba3b6a9` 및 그 이전, PR #32까지)으로 복구 가능합니다.

## 산출물 폴더 규약

| 폴더 | 내용 |
|---|---|
| `aidlc-docs/plans/` | 작업 계획서 (단계별 체크박스 — 사용자 승인 후 한 단계씩 실행) |
| `aidlc-docs/requirements/` | 요구사항·기능 변경 문서 |
| `aidlc-docs/story-artifacts/` | 사용자 스토리·페르소나·인계 노트 |
| `aidlc-docs/design-artifacts/` | 아키텍처·설계·컴포넌트 모델·ADR |
| `aidlc-docs/prompts.md` | 모든 프롬프트의 시간순 로그 (본 파일) |

규칙: 코드는 `aidlc-docs/`의 동결 산출물에서만 도출한다. 모든 작업은 계획서를 먼저 쓰고 승인을 받은 뒤 실행한다.
중대한 결정은 단독으로 내리지 않는다.

---

## Prompt 1 — 2026-06-15

> Audit the documents and restart the whole AI-DLC process from the beginning.

**조치 (감사 → 재시작):**

1. **문서 감사** — `aidlc-docs/` 4계층을 병렬 감사. 구조는 건전(스토리 포인트 합계·MoSCoW·페르소나×에픽 커버리지·앵커 대부분 정합)하나 **드리프트** 다수:
   - U1 §6 "빌드 가능" 체크박스 0/4 미체크인데 실제로는 가장 완성도 높은 unit(역방향 드리프트).
   - ADR-D3(도쿄+Cohere → 서울+Titan) 전파 누락 2건(`tech-stack-aws-candidates.md`, `unit-u0-foundation.md` L97).
   - `handoff.md` NFR 키 카운트 33 ↔ 실제 29 불일치; `coverage_matrix.md`가 NFR 전수 커버리지를 과대 주장(11개 키 미인용).
   - `prompts.md`가 Prompt 26에서 정지 — 빌드/배포 단계(PR #14~#32, 서울/Titan 전환, 라이브 데모) 미기록.
   - U1·U2 코드 리뷰 산출물 부재. **U3 Differentiate는 전혀 미구축**(유일 잔여 unit).
2. **재시작 결정** — 사용자가 *Full wipe & rebuild + blank slate + AWS 인프라 해체* 선택.
3. **실행** — 라이브 AWS 인프라 전체 해체(상단 재시작 메모 참조) + 레포 블랭크 슬레이트화 + 본 스캐폴드 재생성.

**다음 단계**: 사용자의 고수준 요구사항 입력 대기 → 승인 기반 계획서 작성 → **Inception › User Stories** 단계 시작.

---
