# 페이즈 4 Grounding Framework 통합 — 요구사항 명확화 질문 (Requirement Verification — Grounding)

**단계**: INCEPTION → Requirements Analysis 재진입 (재인셉션 페이즈 4) · **일자**: 2026-06-26
**담당**: 본인
**대상 기능**: 흩어진 grounding(검색·요약·에이전트)을 **단일 철학·단일 인터페이스 + 도메인별 Validator**로 통합. **D3 = `shared/ports` 확장**(유닛 신설 없음).
**영향 유닛**: `shared/ports` · U6(게이트웨이 enforce) · U2(검색 grounding) · U7(요약 grounding) · 페이즈 5(에이전트 grounding).
**근거 SSOT**: 차터(**D3**) · 베이스라인(§4-1 설계 긴장점) · 코드: `shared/ports/README.md`·`discovery/domain/grounding_adapter.py`·`summarization/domain/grounding.py`.
**답변 상태**: ⏳ **답변 대기**. 각 질문에 **권장(차터)** 을 별도 줄로 적어두었다. `[Answer]:` 는 비워 두고 **letter(A/B/X)** 로 채워 주세요.

> **핵심 코드 사실 (이미 grounding이 둘로 갈려 있음)**:
> - 검색(U2): `GroundingEnforcementHook.enforce`(**U6 단일권위·FROZEN**) — candidate ↔ retrieved record **SET** 멤버십. U2는 thin 어댑팅만.
> - 요약(U7): `GroundingValidator`(**U7 자체 소유**) — 한 논문 source 대비 **문서 충실도**(anchor 존재·숫자 일치·스키마). 코드 주석이 *"단일권위 U6"를 '검색 grounding에 한정'으로 이미 해석*.
> → 두 검사는 **종류가 본질적으로 다름**. 통합은 "하나의 enforce로 합치기"가 아니라 **공유 인터페이스 + 도메인 Validator**가 코드 현실과 맞는다.
>
> **실질 갈림길**: **Q1(통합 모델)·Q2("단일권위" 재정의)**.

---

## Q1. 통합 모델 — 단일 enforce vs 공유 인터페이스+도메인 Validator — **실질 갈림길**

grounding 통합을 어떤 구조로 하는가?

- **A) 공유 인터페이스(`shared/ports`) + 도메인별 Validator 레지스트리** (차터 D3·코드 정합):
  공통 = `verdict(pass|block|abstain)` + `violations[]` 인터페이스 1개. 구현 = Search Validator(set 멤버십)·Summary Validator(문서 충실도)·Agent Validator(출처 실재·교차확인) 도메인별 분리. 호출 지점은 각 도메인 seam 유지.
- **B) U6가 모든 Validator 내부 보유 + enforce가 도메인 디스패치**:
  단일 진입이지만 U6가 요약/에이전트 검사까지 떠안음(현재 U7 자체 소유와 충돌, U6 비대).
- **X) 기타**

[Answer]:
**권장(차터·코드)**: A — 철학/인터페이스 하나, Validator 도메인별. (B는 U7이 이미 자체 grounding을 가진 코드 현실과 어긋남.)

---

## Q2. "단일 grounding 권위 = U6" 재정의 — **실질 갈림길**

`shared/ports`·코드 주석의 "single authority = U6"를 어떻게 공식화하는가?

- **A) U6 = **검색** grounding(enforce) 단일권위로 한정 명문화. 요약/에이전트는 도메인 Validator(공유 인터페이스 구현)** (코드 현실):
  검색 enforce(FROZEN) 권위는 U6 유지. 문서충실도/근거형성은 검사 종류가 달라 도메인 소유. 통합은 *인터페이스·관측 일원화*.
- **B) 모든 grounding을 U6 단일권위로 승격** — 요약 자체 Validator 해체 필요(범위·리스크 큼).
- **X) 기타**

[Answer]:
**권장(차터·코드)**: A

---

## Q3. 공유 인터페이스 시그니처

도메인 Validator가 공유하는 인터페이스를 무엇으로 하는가?

- **A) 공통 출력 = `verdict: pass|block|abstain` + `violations[]`(비기술 코드, 내부 상세 비노출 SEC-9); 입력은 도메인별 타입**:
  검색=candidate↔record set, 요약=draft↔refined source, 에이전트=evidence↔sources. enforce(검색, FROZEN)는 불변.
- **B) 입력까지 단일 타입으로 강제** — 도메인 이질성 상 비현실.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q4. Agent Validator 신규 (페이즈 5 연동)

페이즈 5 근거형성 산출(`EvidenceResult`) 검증을 통합 프레임워크에 넣는가?

- **A) Agent Validator 신규 — 같은 인터페이스(verdict/violations)** (차터·포트 계약 초안 §5):
  출처 실재성(IndexRecord/Block id 존재)·교차확인 일관성·기권 강제. 검색·요약과 인터페이스 공유, 검사 로직은 도메인.
- **B) 에이전트는 grounding 미적용** — 환각 방지 공백(기각).
- **X) 기타**

[Answer]:
**권장(차터)**: A — 에이전트 포트 계약 초안 §5와 한 쌍.

---

## Q5. 호출 지점(seam)

Validator 호출 지점을 무엇으로 하는가?
(현행: 검색=게이트웨이 post-handler에서 enforce, 요약=orchestrator 내부에서 validate.)

- **A) 도메인 seam 유지(검색=게이트웨이, 요약=orchestrator, 에이전트=오케스트레이터) + 공유 인터페이스로 일관화**:
  호출 위치는 도메인 책임, 인터페이스/결과 형태만 통일. 코드 변경 최소.
- **B) 전 도메인 게이트웨이 단일 호출로 이전** — 요약/에이전트의 내부 재시도·fail-closed 흐름과 충돌.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q6. Grounding 관측 일원화

grounding 결과 관측을 무엇으로 하는가?

- **A) verdict/violation 지표를 `ObservabilityHub`(emitMetric/emitLog)로 통일 수집** (`shared/ports` 정합):
  도메인 무관 grounding 헬스(zero-fabrication·abstain율) 단일 대시보드. PII/내부상세 비노출(SEC-3/9).
- **B) 도메인별 산발 로깅**.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q7. enforce FROZEN 변경 정책

검색 enforce 시그니처(FROZEN) 및 공유 인터페이스 변경을 어떻게 통제하는가?

- **A) enforce 시그니처 불변 + 공유 인터페이스 변경은 shared 계약 PR + 영향 유닛 사인오프** (기존 ports 정책 준용):
  통합은 enforce를 건드리지 않고 인터페이스를 *추가*(가산적). 도메인 Validator 추가는 레지스트리 등록.
- **B) enforce 재설계** — 영향 범위 큼(기각).
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## 다음 단계

답변(특히 **Q1·Q2**) 확정 후 → `requirements.md`에 페이즈 4 FR/NFR/C 등재 + `shared/ports` 확장 설계(application-design). Q4는 에이전트 포트 계약 초안과, Q1/Q2는 페이즈 2 Q4·페이즈 3 Q4와 **정합**시킨다.
