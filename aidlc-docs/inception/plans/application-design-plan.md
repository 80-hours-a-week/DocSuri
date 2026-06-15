# 애플리케이션 설계 계획 (Application Design Plan)

**단계**: INCEPTION → Application Design · **일자**: 2026-06-15
**입력**: `requirements.md`(FR/NFR/SEC/RES/QT), `stories.md`(21개), `personas.md`(P1/P2/OP), `execution-plan.md`(예비 유닛 U1~U6).
**범위**: 고수준 컴포넌트 식별 + 서비스 계층 설계(상세 비즈니스 로직은 CONSTRUCTION/Functional Design). **기술 스택(언어·프레임워크)은 여기서 확정하지 않음** — NFR Requirements/Construction 소관. 단 **아키텍처 스타일·토폴로지·통신 패턴**은 본 단계에서 결정.

아래 설계 질문에 답하거나(또는 **"approve plan"** 으로 권장안 수락) 후, 설계 산출물을 생성한다.

---

## 설계 질문 (Design Questions)

## DQ1 — 아키텍처 스타일
배포·운영 단위를 어떻게 구성할까? (중간 티어·소규모 팀·공개 프로덕션·단일 리전 멀티 AZ 전제)

A) **모듈형 모놀리스 + 분리된 인제스천 워커(권장)** — 단일 배포 API(도메인 모듈 경계 명확) + 스케줄 인제스천 잡 분리. 운영·비용 단순, 데모·확장 균형.

B) 마이크로서비스 — 유닛별 독립 서비스(운영 복잡도↑, 소규모 팀엔 과함).

C) 풀 서버리스 — 기능별 Lambda 함수(이전 사이클 경험; 콜드 스타트·NFR-P1 긴장).

D) 하이브리드 — 서버리스 인제스천 + 모놀리스 API 등 혼합.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ2 — 프런트엔드/백엔드 토폴로지
폰 우선 모바일 웹(NFR-U1/U2)을 어떻게 전달할까?

A) **SSR 모바일 웹(예: Next.js) + 백엔드 API(권장)** — 이전 사이클 Amplify/Next.js 경험 부합, 폰 목업 프레임(NFR-U2) 처리 용이.

B) SPA + 별도 API.

C) 기타.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ3 — 인제스천 실행 모델
arXiv 인제스천·인덱싱(U1/FR-6)을 어떻게 실행할까?

A) **스케줄 배치 잡/워커(API와 분리)(권장)** — 일 1회 갱신, 사용자 경로와 디커플; 실패가 검색에 영향 없음.

B) API 서비스 내부 작업.

C) 이벤트 드리븐(신규 논문 트리거).

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ4 — 컴포넌트 조직 방식
코드/모듈을 어떻게 묶을까?

A) 유닛별 모듈(Discovery/Accounts/Library/Ingestion/Ops).

B) 레이어드(컨트롤러/서비스/리포지토리)만.

C) **하이브리드(권장)** — 도메인 모듈(유닛) + 공유 레이어(공통 어댑터·횡단 관심사).

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ5 — 횡단 관심사 위치
비용 가드/서킷 브레이커(NFR-C1), 근거화 강제(FR-5), 관측성(NFR-O1), 인증/인가(SEC-8/12)를 어디에 둘까?

A) **전용 횡단 모듈/미들웨어(권장)** — 게이트웨이/미들웨어 계층에 집중(SEC-11 격리 원칙 부합).

B) 컴포넌트별 내장.

C) 외부 서비스 위임.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ6 — 통신 패턴
컴포넌트 간 통신은?

A) **사용자 경로 동기 REST + 인제스천 비동기/스케줄(권장)** — 디스커버리는 요청/응답, 인제스천은 잡.

B) 전부 동기.

C) 이벤트 드리븐 전반.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

## DQ7 — API 스타일
클라이언트-백엔드 API는?

A) **REST(권장)** — 단순, 모바일 웹·캐싱 친화.

B) GraphQL.

C) 기타.

X) 기타 (아래 [Answer]: 태그 뒤에 기술)

[Answer]: 

---

## 필수 설계 산출물 (답변·승인 후 생성)
- [ ] `application-design/components.md` — 컴포넌트 정의·책임·인터페이스
- [ ] `application-design/component-methods.md` — 메서드 시그니처·입출력(상세 비즈니스 규칙은 Functional Design)
- [ ] `application-design/services.md` — 서비스 정의·오케스트레이션
- [ ] `application-design/component-dependency.md` — 의존성 매트릭스·통신 패턴·데이터 흐름
- [ ] `application-design/application-design.md` — 위 문서 통합본
- [ ] 설계 완전성·일관성 검증(스토리/요구사항 추적)

## 생성 단계 실행 방식 (승인 후)
- 6 유닛(U1~U6)에 대한 컴포넌트·메서드·서비스·의존성을 **병렬 생성 → 적대적 비평(일관성·추적성·경계) → 통합**(멀티에이전트 워크플로). API 회복 상태이므로 워크플로 사용.
