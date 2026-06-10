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
- [ ] **R6. 사용자 검토 → 결정 라운드 재개** — 보고서 기반으로 C-D1~C-D10 게이트 재실행.

## 사용자 결정 게이트 (10건 — 조사 보고서 검토 후 확정, 현재 전부 보류)

- [ ] **C-D1. 백엔드 언어/프레임워크** — ⏸ 보류 (2026-06-10)
- [ ] **C-D2. 임베딩 인덱스** — ⏸ 보류 (2026-06-10)
- [ ] **C-D3. 임베딩 모델** — ⏸ 보류 (2026-06-10)
- [ ] **C-D4. LLM 모델** — ⏸ 보류 (2026-06-10) (NFR-COST-01 직결)
- [ ] **C-D5. 프론트엔드 프레임워크** — (조사 후)
- [ ] **C-D6. 컴포넌트 라이브러리** — (조사 후)
- [ ] **C-D7. 그래프 시각화** — (조사 후)
- [ ] **C-D8. 오프라인 캐시 메커니즘** — (조사 후)
- [ ] **C-D9. 호스팅 환경** — (조사 후)
- [ ] **C-D10. 관찰가능성 스택** — (조사 후)
- [x] **C-G1. 산출물 커밋·PR 처리** — 사용자 확정 (2026-06-10): 열려 있는 **PR #12 브랜치에 커밋** (머지는 보류 유지). D1~D10 결정은 **팀 협의로 진행** 예정 — 본 보고서가 협의 자료.

## 실행 단계 (결정 확정 후)

- [ ] **A1. ADR 문서 작성** — 결정 요약 표 + ADR-01~10 (컨텍스트/결정/근거/대안 비교/결과) + 스택 다이어그램(Mermaid)
- [ ] **A2. 비용 시뮬레이션 확정판** — R4 결과를 선택안 기준으로 갱신 (U0 §6 "빌드 가능 정의"의 시뮬레이션 보고 항목 선이행)
- [ ] **A3. 포트↔구현체 매핑** — component-model §2~§6의 각 포트·컴포넌트가 받는 구현 기술 명시

## 검증·마감

- [ ] **V1. 결정 누락 검사** — handoff §4의 D1~D10 전부 기록되었는지 확인
- [ ] **V2. NFR 추적성** — 각 ADR이 인용한 NFR 키 표 (근거 없는 결정 0건)
- [ ] **V3. 사용자 최종 리뷰** — ADR 문서 제출·피드백 반영

---

## 범위 밖 (Out of Scope)

- 코드 생성·환경 구축 — 본 단계는 결정 기록만.
- handoff.md 수정 — §4 각주가 "본 표는 결정을 강제하지 않으며, 다음 단계 산출물에서 기록·승인하면 된다"고 명시 → 동결 문서는 건드리지 않는다.
- PDF 추출 라이브러리 등 unit 내부 결정 (U2 §5) — 해당 unit 진입 시 결정.
