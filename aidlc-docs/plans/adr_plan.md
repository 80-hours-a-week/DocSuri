# ADR(기술 스택 결정) — 작업 계획 (Construction Phase)

> **Phase**: AIDLC Construction — Architecture Decision Records
> **입력 산출물**: [`handoff.md §4`](../story-artifacts/handoff.md) (Open Decisions D1~D10) · [`nfr.md`](../requirements/nfr.md) (NFR 33키) · [`units/`](../design-artifacts/units/) (결정→unit 매핑) · [`component-model.md`](../design-artifacts/component-model.md) (포트·컴포넌트 경계)
> **입력 범위 제약** (사용자 지시, 2026-06-10): `aidlc-docs/` 밖의 코드·문서는 근거로 사용하지 않는다.
> **출력 산출물**: [`design-artifacts/architecture_decision_record.md`](../design-artifacts/architecture_decision_record.md) — handoff §4가 권고한 파일명.
> **결정 권한**: 기술 스택은 임의 결정 금지 — 결정 10건 각각 사용자 확정 게이트를 거친다 (권장안 + 대안 + 트레이드오프 제시).

---

## 사전 확인 (완료)

- [x] **S0. 입력 정독** — handoff §2 위험(R1~R7)·§3 가정(A1~A8)·§4 결정(D1~D10), NFR 10 카테고리 33키, units-overview §5.2 결정→unit 매핑, 컴포넌트 모델 포트 시그니처 추출 완료.
- [x] **S1. 결정 순서 확인** — handoff §5.2: U0 라운드에 D1·D2·D3·D4·D8·D9·D10 (7개 집중). D5·D6(U1)·D7(U4)도 병렬 팀 시작을 위해 본 라운드에서 함께 닫는다 (units-overview §3 "완전 병렬" 옵션 근거).

---

## 방향 전환 (2026-06-10, 사용자 지시)

- [x] **P1. 결정 보류 확인** — D1~D4 결정 게이트에 사용자 응답 "We will decide it later" — **10건 전부 결정 보류**.
- [x] **P2. 조사 우선 지시 접수** — "기술 스택 후보는 AWS 중심으로 조사해줘" → 결정 전 단계로 **AWS 중심 후보 조사 보고서**를 신설 산출물로 작성한다. ADR 확정은 보고서 검토 후 별도 라운드.

## 조사 단계 (AWS 중심 후보 조사)

- [x] **R1. 최신 정보 웹 확인** (2026-06-10) — S3 Vectors GA·**서울 리전 포함** 확인 / Claude 4.5+ 서울 소스 `global.*` CRIS (추가 과금 없음) / Nova `apac.*`에 서울 포함 / OpenSearch Serverless 최소 ~$175 → COST-01 탈락 / Aurora SLv2 0 ACU auto-pause(재개 ~15s) / App Runner 유휴 $3~13 / Amplify SSR 50만 req 무료.
- [x] **R2. D1~D10별 AWS 후보 정리** — 보고서 §2~§11. D6·D7·D8은 AWS 중립 결정으로 판정 (Cloudscape는 콘솔용이라 부적합).
- [x] **R3. 참조 아키텍처 2안 구성** — 보고서 §10: (a) 서버리스 일괄(Amplify+Lambda+KB/S3 Vectors+DynamoDB) vs (b) 상시 컨테이너(App Runner+Chroma/SQLite). §13 포트 매핑.
- [x] **R4. 비용 시뮬레이션** — 보고서 §12: (a)+Haiku 4.5 ≈ **월 $45 ≤ $50** / Nova Lite ≈ $5 / 혼합(Haiku+DIFF만 Sonnet) ≈ $46 / (b)는 +$3~13.
- [x] **R5. 조사 보고서 작성** — [`design-artifacts/tech-stack-aws-candidates.md`](../design-artifacts/tech-stack-aws-candidates.md) (한국어·Mermaid·앵커 링크·출처 §15).
- [x] **R6. 사용자 검토 → 결정 라운드 재개** — 2026-06-10 재개·완료: D9·D2 선행 확정 → "나머지 원안 그대로" → D3 리전 분기만 추가 확인(도쿄+Cohere).

## 사용자 결정 게이트 (10건 — 조사 보고서 검토 후 확정, 현재 전부 보류)

> ✅ **10/10 확정** (2026-06-10, 사용자·팀): "나머지 기술 스택도 원안 그대로" — 조사 보고서 1순위 후보 일괄 채택. 유일한 분기였던 D3·리전은 별도 확인을 거쳐 **도쿄 + Cohere** 확정.

- [x] **C-D1. 백엔드** — Python 3.12 + FastAPI (Lambda Web Adapter) → [ADR-D1](../design-artifacts/architecture_decision_record.md#adr-d1)
- [x] **C-D2. 임베딩 인덱스** — Bedrock KB + S3 Vectors → [ADR-D2](../design-artifacts/architecture_decision_record.md#adr-d2). ⚠️ D3 연쇄 제약(서울 KB 임베딩 = Titan V2만)은 D3에서 도쿄 이동으로 해소.
- [x] **C-D3. 임베딩 모델** — Cohere Embed Multilingual v3 + **전 스택 도쿄(ap-northeast-1) 통일** → [ADR-D3](../design-artifacts/architecture_decision_record.md#adr-d3)
- [x] **C-D4. LLM 모델** — Claude Haiku 4.5 (`global.` CRIS), 시뮬 ~$42 ≤ $50 → [ADR-D4](../design-artifacts/architecture_decision_record.md#adr-d4)
- [x] **C-D5. 프론트엔드** — Next.js App Router + Amplify Hosting → [ADR-D5](../design-artifacts/architecture_decision_record.md#adr-d5)
- [x] **C-D6. 컴포넌트 라이브러리** — shadcn/ui + Tailwind CSS → [ADR-D6](../design-artifacts/architecture_decision_record.md#adr-d6)
- [x] **C-D7. 그래프 시각화** — React Flow → [ADR-D7](../design-artifacts/architecture_decision_record.md#adr-d7)
- [x] **C-D8. 오프라인 캐시** — Service Worker(Serwist) + IndexedDB — R6 위험 닫힘 → [ADR-D8](../design-artifacts/architecture_decision_record.md#adr-d8)
- [x] **C-D9. 호스팅 환경** — 풀 서버리스 (Amplify + Lambda + DynamoDB + Bedrock, **도쿄 기준** — D3 연쇄로 갱신) → [ADR-D9](../design-artifacts/architecture_decision_record.md#adr-d9)
- [x] **C-D10. 관찰가능성** — CloudWatch(EMF) + Bedrock 호출 로깅 + X-Ray → [ADR-D10](../design-artifacts/architecture_decision_record.md#adr-d10)
- [x] **C-G1. 산출물 커밋·PR 처리** — 사용자 확정 (2026-06-10): 열려 있는 **PR #12 브랜치에 커밋** (머지는 보류 유지). D1~D10 결정은 **팀 협의로 진행** 예정 — 본 보고서가 협의 자료.

## 실행 단계 (결정 확정 후)

- [x] **A1. ADR 문서 작성** — [`architecture_decision_record.md`](../design-artifacts/architecture_decision_record.md): ADR-D1~D10 **10건 전부 기록** (컨텍스트/결정/근거/대안 기각/결과/NFR 추적) + 현황판 §1.
- [x] **A2. 비용 시뮬레이션 확정판** — ADR §13: 확정 스택 기준 월 ~$45 ≤ $50 (U0 §6 시뮬레이션 보고 항목 충족).
- [x] **A3. 포트↔구현체 매핑** — ADR §12: U0 포트 11행 전부 확정 구현 명시.

## 검증·마감

- [x] **V1. 결정 누락 검사** — handoff §4 D1~D10 = ADR-D1~D10, 누락 0 (ADR §1 현황판 10/10 ✅).
- [x] **V2. NFR 추적성** — 각 ADR 절에 "NFR 추적" 행 포함, 근거 없는 결정 0건. 위험 정리: R3 1차 닫힘(D4)·R6 닫힘(D8).
- [x] **V3. 사용자 최종 리뷰** — 2026-06-10 사용자 확정 지시("원안 그대로") + D3 분기 확인 응답으로 종결. **본 계획의 전 단계 완료.**

---

## 범위 밖 (Out of Scope)

- 코드 생성·환경 구축 — 본 단계는 결정 기록만.
- handoff.md 수정 — §4 각주가 "본 표는 결정을 강제하지 않으며, 다음 단계 산출물에서 기록·승인하면 된다"고 명시 → 동결 문서는 건드리지 않는다.
- PDF 추출 라이브러리 등 unit 내부 결정 (U2 §5) — 해당 unit 진입 시 결정.
