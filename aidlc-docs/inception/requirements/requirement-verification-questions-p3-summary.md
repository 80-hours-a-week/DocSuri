# 페이즈 3 요약/번역(U7 Summarization) — 요구사항 명확화 질문 (Requirement Verification — Summary/Translate)

**단계**: INCEPTION → Requirements Analysis 재진입 (재인셉션 페이즈 3) · **일자**: 2026-06-26
**담당**: 본인
**대상 기능**: 검색된 논문의 온디맨드 **구조화 요약**·**초록/본문 번역**. DocModel → Input Refine → LLM → **Grounding(페이즈 4 동시)** → Cache. **D6**(DocModel eager·인덱싱 기반) 반영.
**영향 유닛**: U7(`backend/modules/summarization/`) · `shared/dtos/summarization.schema.json`·`docmodel.schema.json` · U1(DocModel writer, D6) · 페이즈 4(grounding).
**근거 SSOT**: 차터(**D6**) · 베이스라인(§4 "요약/번역은 정합 작업") · (구) doc-model 피벗 게이트 · `summarization/domain/*`.
**답변 상태**: ⏳ **답변 대기**. 각 질문에 **권장(차터)** 을 별도 줄로 적어두었다. `[Answer]:` 는 비워 두고 **letter(A/B/X)** 로 채워 주세요.

> **성격**: 페이즈 3은 그린필드가 아니다 — summarization 모듈(refiner·grounding·map_reduce·structured_translator·glossary·cache_key·worker)이 상당 구현됨. 실체는 **D6 DocModel 반영 + 페이즈 4 grounding 통합 정합**.
> **실질 갈림길**: **Q2(D6에 따른 lazy 빌드 큐 역할)**.

---

## Q1. 요약/번역 입력 = DocModel 완성형 (정합 확인)

요약·번역 LLM 입력을 DocModel 완성형으로 두는가? (doc-model 피벗으로 이미 전환됨 — 재확인.)

- **A) DocModel 완성형 입력 유지**(피벗 정합): 표=데이터·수식=LaTeX·그림 webp 참조. 생성/근거화/캐시 로직 불변, 입력만 DocModel.
- **B) 평문 회귀** — 기각.
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q2. D6 전환에 따른 DocModel 빌드 큐 역할 — **실질 갈림길**

D6(U1 수집 시점 eager DocModel)로 바뀌면 U7의 lazy 빌드 큐를 어떻게 두는가?
(현재 코드: `SqsDocModelBuildQueue.enqueue_build` → U1 워커가 요약 시점 lazy 빌드.)

- **A) U7은 DocModel **read-only 소비자**로, lazy enqueue는 **누락/신버전 보강 fallback**으로 축소** (차터 D6):
  정상 경로는 U1 eager 산출물(S3)을 읽기만. 큐는 미존재/버전 불일치 시에만 보강.
- **B) 현행 lazy 빌드 주경로 유지** — D6과 충돌(기각).
- **X) 기타**

[Answer]:
**권장(차터·D6)**: A — read-only 소비 + 보강 fallback. U1 Q5(eager)와 한 쌍.

---

## Q3. 번역 소스 계약

번역 입력을 무엇으로 하는가?

- **A) 초록 = Metadata 저장 Abstract · 본문 = DocModel(Block) 사용** (차터):
  초록은 메타데이터 Abstract 직접, 본문은 DocModel Block 구조(structured_translator) 번역.
- **B) 본문도 평문** — 기각(구조 손실).
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q4. 요약 Grounding — 페이즈 4 통합과 정합

요약 grounding을 어떻게 두는가?
(현행: `GroundingValidator` = U7 자체 **결정적** 검사 — anchor 존재·숫자 일치·스키마·truncation; LLM-judge 아님; 실패→1회 재시도→기권 fail-closed.)

- **A) U7 자체 결정적 Validator 유지 + 페이즈 4 통합 인터페이스의 "Summary Validator"로 편입** (차터 D3):
  검색 enforce(set 멤버십)와 **검사 종류가 다름**(문서 충실도) → "단일권위 U6"는 *검색 grounding*에 한정. 공유하는 건 verdict(pass/block/abstain)·violations 인터페이스.
- **B) U6 enforce로 요약도 강제** — 검사 종류 불일치(기각).
- **X) 기타**

[Answer]:
**권장(차터)**: A — 페이즈 4 Q1과 한 쌍(도메인별 Validator + 공유 인터페이스).

---

## Q5. Anchor 계약 — DocModel 결정적 id

근거 앵커("출처 보기") 핸들을 무엇으로 하는가?

- **A) DocModel Section/Block 결정적 id**(피벗 정합·에이전트 공통): `Anchor.target`=id(+선택 span). 검증 결정적. 에이전트 `SourceRef.anchor`와 동일 계약.
- **B) 섹션 라벨+정규식** — 취약(기각).
- **X) 기타**

[Answer]:
**권장(차터)**: A

---

## Q6. 캐시 정책 유지

요약/번역 산출물 영속·캐시를 무엇으로 하는가?

- **A) S3 영구 + Redis 핫캐시, 키 = `(paperId, version, task, persona/view/glossary)` 불변** (현행):
  논문당 평생 1회 생성(immutable). 만료/무효화 정책 명시(무한 캐시 금지, 차터 Part 2-A).
- **B) 변경**.
- **X) 기타**

[Answer]:
**권장(차터)**: A — 만료·무효화 정책은 NFR에서 수치 확정.

---

## Q7. 비용 제어 유지

LLM 비용 제어를 무엇으로 하는가?

- **A) 모델 분리(요약=Sonnet·초록=Haiku) + 초장문 map-reduce 비동기 잡 + `CostGuard` 게이트** (현행):
  대부분 단일 콜 동기 스트리밍, 초장문만 비동기(배포 ③).
- **B) 변경**.
- **X) 기타**

[Answer]:
**권장(차터)**: A — 모델 선택은 최신·최적 기준 NFR에서 재검토 여지.

---

## 다음 단계

답변(특히 **Q2**) 확정 후 → `requirements.md`에 페이즈 3 FR/NFR/C 등재. Q2는 U1 Q5(eager)와, Q4는 페이즈 4 Q1과 **쌍으로** 확정.
