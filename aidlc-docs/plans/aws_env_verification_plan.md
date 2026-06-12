# AWS 환경 구축 검증 — 변경 계획서 (handoff §6 절차)

> **Phase**: AIDLC Construction — U0 빌드 라운드 부속 (환경 실증)
> **트리거**: [`prompts.md` Prompt 25](../prompts.md#prompt-25) (2026-06-11)
> **성격**: ADR가 빌드 단계로 *명시적으로 미뤄둔* 검증 항목([ADR §14](../design-artifacts/architecture_decision_record.md))을 실 AWS에 프로비저닝하여 닫음. **결정 확인**이지 결정 변경이 아니다.
> **작업 계정/리전**: SSO `AdministratorAccess-028317349537` (계정 `028317349537`) · `ap-northeast-1` (도쿄, ADR-D3/D9 기준 리전)
> **입력 범위 제약** (기존 지시 유지): 근거는 `aidlc-docs/` 문서만.

---

## 1. 왜 handoff §6 절차를 타는가

[`handoff.md §6`](../story-artifacts/handoff.md)·[ADR 운영 방식](../design-artifacts/architecture_decision_record.md)은 **동결 문서 본문의 변경**에 4단계(프롬프트→계획→승인→갱신)를 요구한다. 본 작업은 검증 *결과를 동결 본문(ADR·U0 §6)에 주석으로 반영*하므로, 비록 결정을 바꾸지 않더라도 "조용한 수정 금지" 원칙상 절차를 밟는다.

- (1) 프롬프트 기록 — [Prompt 25](../prompts.md#prompt-25) ✅
- (2) 변경 계획서 — 본 문서 ✅
- (3) 사용자 승인 — 2026-06-11, 기록 방식 선택지에서 **"신규 산출물 + 동결 본문 갱신"** 채택 ✅
- (4) 산출물 작성·본문 갱신 — §3 참조

## 2. 검증 결과 요약 (상세·증거: [`reviews/u0-aws-env-verification.md`](../reviews/u0-aws-env-verification.md))

| # | 항목 (ADR) | 결과 | 결정 영향 |
|---|---|---|---|
| ① | 도쿄 KB×S3 Vectors 생성 ([D2](../design-artifacts/architecture_decision_record.md#adr-d2)) | ✅ 가능 (8/8 색인, 16.4s) | D2 결과⑤ "콘솔 최종 확인" 닫힘. 폴백(iii) 불요 |
| ② | KB Retrieve 연도 범위 필터 ([D2](../design-artifacts/architecture_decision_record.md#adr-d2)) | ✅ 표현·동작 (KB `andAll`/`gte`·S3V `$and`/`$gte`) | D2 결과① 구현 경로 확인 |
| ③ | Lambda 콜드스타트 P50<3s 영향 ([D9](../design-artifacts/architecture_decision_record.md#adr-d9)) | ✅ 위협 없음 (콜드 init P50 887ms) | D9 결과⑤ 워밍 발동 조건 미충족 — 결정 유지 |
| ④ | Haiku 4.5 KKL 4급 톤 ([D4](../design-artifacts/architecture_decision_record.md#adr-d4)) | ✅ 충족 (pro 260자 보존·student 419자 풀어쓰기) | D4 톤 분기·접근 게이트 확인 |

## 3. 동결 본문 변경 범위 (정확·최소)

**갱신함** (검증완료 주석 *추가*, 기존 텍스트는 감사 추적 위해 보존):
- `architecture_decision_record.md`
  - ADR-D2 "검증 항목" 라인 → ①② ✅ 주석 + ③ 8편 선검증
  - ADR-D9 "검증 항목" 라인 → ③ ✅ 실측 주석
  - ADR-D4 결과 → ④ ✅ 톤 실측 주석
  - §14 "환경 구축 시 검증 항목 모음" → 4건 ✅ + 산출물 링크
- `units/unit-u0-foundation.md`
  - §6 증거 라인 → "mock 모드" → **"mock + 실 AWS 확인 (2026-06-11)"**. **체크박스 6/6 상태 불변** (§6 항목은 설계상 "실모델 OR 결정적 mock" 허용 — 어떤 항목도 상태가 바뀌지 않음).

**갱신 안 함** (사유 명시 — §6 step 4의 충실한 적용):
- handoff `§1` 동결 산출물 표 — Inception 산출물 표이며 본 검증 문서는 Construction *리뷰* 산출물이라 범주 불일치. 추가 시 노이즈.
- handoff `§2` 위험 — [R3](../story-artifacts/handoff.md#r-3)(LLM *비용* 변동성)은 ADR-D4로 이미 "1차 닫힘"이고 ④는 *톤* 검증이라 비용 상태를 바꾸지 않음. [R4](../story-artifacts/handoff.md#r-4)(인용 API)는 U0 구현 단계 소관으로 본 작업 밖. → §2 변경 없음.
- `component-model.md` 포트 시그니처 — 변경 0 (구현체 확인만).

## 4. 실증 환경 — 생성·정리(teardown)

전 리소스 `docsuri-it-*` 접두사로 생성 후 **전량 삭제**(생성·삭제 모두 성공 = 실재 증명). 총 비용 수 센트 미만(서버리스·분 단위 보유). 상세 ARN·삭제 로그는 검증 산출물 §5.

## 5. 마감

- 4건 검증 통과 → ADR §14 닫힘. U0 §6은 mock 6/6에 실 AWS 증거가 더해져 **이중 근거**.
- 다음: PR로 develop 병합(사용자 commit 게이트). 후속 unit(U1·U2) 진입에는 영향 없음 — 본 작업은 기반 결정의 사후 실증.
