# U11 차별화(novelty) 에이전트 — 요구사항 검증 질문

**단계**: INCEPTION → Requirements Analysis 재진입  
**일자**: 2026-06-28  
**대상 유닛**: U11  
**개발 대상**: `차별화(novelty) 에이전트`  
**비대상**: `문헌탐색 & 근거형성 에이전트` 구현. 해당 에이전트는 U11 내 병렬 에이전트지만 별도 과정에서 개발한다. 본 질문지는 두 에이전트가 공유해야 하는 공통 협약/계약과 novelty 에이전트 요구사항만 다룬다.

## 답변 방법

각 질문의 `[Answer]:` 뒤에 선택지 문자를 입력해 주세요. 선택지가 맞지 않으면 마지막 `X) Other`를 선택하고 원하는 내용을 적어 주세요.

---

## Question 1
기존 `research-agent` 요구사항(FR-22~25, QT-8)을 U11 novelty 에이전트 관점에서 어떻게 처리할까요?

A) 기존 Agent 요구사항 중 novelty 관련 부분만 U11 novelty 에이전트 요구사항으로 개정하고, 문헌탐색&근거형성 부분은 별도 과정으로 분리한다. (Recommended)

B) 기존 Agent 요구사항은 유지하고 U11 novelty 에이전트는 별도 FR 번호로만 추가한다.

C) 기존 Agent 요구사항을 폐기하고 U11 novelty 에이전트 요구사항으로 완전히 대체한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 2
U11 안의 두 에이전트 관계를 어떻게 정의할까요?

A) 병렬 에이전트 2개가 같은 U11 공통 계약을 공유한다. novelty 에이전트는 필요 시 문헌탐색&근거형성 에이전트의 산출물을 입력으로 소비하지만, 그 에이전트를 구현하지 않는다. (Recommended)

B) novelty 에이전트가 문헌탐색&근거형성 에이전트를 내부 sub-agent로 직접 호출한다.

C) 두 에이전트는 완전히 독립이며 공통 계약도 두지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A, 다만 유저가 One-Shot 질문이 아닌 논문을 업로드 하였을 경우, 문헌탐색&근거형성 에이전트를 먼저 호출하여 공통 산출물을 생성하도록 한다. 이후 novelty 에이전트는 문헌탐색&근거형성 에이전트의 산출물을 입력으로 소비하여 novelty 분석을 수행한다.

## Question 3
novelty 에이전트의 v1 입력은 무엇인가요?

A) 사용자의 연구 의도 텍스트 + 선택적으로 문헌탐색&근거형성 에이전트가 만든 공통 산출물. (Recommended)

B) 사용자의 논문 초안 업로드만 입력으로 받는다.

C) 문헌탐색&근거형성 에이전트 산출물만 입력으로 받는다.

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 4
문헌탐색&근거형성 에이전트가 novelty 에이전트에 넘길 공통 산출물의 최소 형태는 무엇이어야 하나요?

A) `EvidenceBundle`: 사용자 의도/초안에서 추출된 주장·방법·실험 후보, sourceRefs, confidence, unresolved gaps를 포함한다. (Recommended)

B) 자유 형식 Markdown 요약만 넘긴다.

C) 검색 query 목록만 넘긴다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 5
공통 source reference 계약은 어느 수준이어야 하나요?

A) 모든 근거는 `sourceId`, `sourceType`, `title`, `url`, `retrievedAt`, `snippet`, 내부 corpus `paperId/version/blockRefs` 중 가능한 값을 포함한다. (Recommended)

B) URL과 제목만 있으면 충분하다.

C) 내부 corpus 근거만 source reference로 인정한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 6
novelty 에이전트의 제품 약속은 무엇인가요?

A) "새롭다/아니다" 판정은 하지 않고, 유사 연구·겹치는 점·차별화 가능한 지점·불확실성을 근거와 함께 제시한다. (Recommended)

B) novelty 점수와 "논문화 가능성" 판정을 제공한다.

C) 유사 논문 목록만 제공하고 차별화 지점은 사용자가 판단한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 7
내부 corpus retrieval은 novelty 에이전트에서 어떤 역할인가요?

A) 1차 비교 근거다. U1 Corpus / U2 Discovery 인덱스를 먼저 검색하고, 외부 검색은 보강으로 사용한다. (Recommended)

B) 외부 검색과 동등한 여러 소스 중 하나다.

C) 내부 corpus는 사용하지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 8
외부 탐색 범위는 novelty 에이전트 v1에 어디까지 포함할까요?

A) GitHub 검색, 최신 뉴스 검색, 관련 데이터셋 검색을 모두 포함한다. (Recommended)

B) GitHub 검색과 데이터셋 검색만 포함하고 뉴스는 제외한다.

C) 외부 탐색은 모두 다음 사이클로 둔다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 9
Agent-Browser 사용 방식은 어떻게 제한할까요?

A) 서버 측 U11 novelty Agent Worker에서만 실행하고, 결과 URL·타임스탬프·스니펫·근거만 저장한다. 사용자 원문 전체는 외부 사이트에 보내지 않는다. (Recommended)

B) 품질을 위해 사용자 초안/의도 전체를 외부 사이트 검색 질의에 사용할 수 있다.

C) Agent-Browser는 PoC에서만 사용하고 프로덕션은 공식 API로 대체한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 10
GitHub 검색 결과는 novelty 분석에서 어떻게 사용할까요?

A) 관련 구현체·baseline 코드·벤치마크 코드·재현 단서를 찾되, "재현 가능" 판정은 하지 않고 사실 추출만 한다. (Recommended)

B) repository star/fork/license 기준으로 구현체 품질 점수까지 산출한다.

C) 참고 링크로만 표시하고 novelty 분석에는 반영하지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 11
최신 뉴스 검색 결과는 novelty 분석에서 어떻게 사용할까요?

A) 최근 동향·산업 적용·출시·정책 보강 근거로만 사용하고, 학술 novelty 근거는 논문/데이터셋/코드를 우선한다. (Recommended)

B) 뉴스도 논문과 같은 수준의 novelty 근거로 사용한다.

C) 뉴스 검색은 v1에서 제외한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 12
관련 데이터셋 검색 결과는 어떤 출력에 반영할까요?

A) 실험 아이디어와 실험 계획에 반영한다: 데이터셋 이름, 출처 URL, 라이선스/접근성, 평가 가능 태스크를 추출한다. (Recommended)

B) 데이터셋 이름과 링크만 표시한다.

C) 데이터셋 검색은 수동 참고 자료로만 저장하고 출력에는 반영하지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 13
기존 한계 분석의 출력 범위는 무엇인가요?

A) 검색된 논문/코드/데이터셋 근거에서 추출 가능한 한계만 표로 정리하고, 근거 없는 한계는 기권한다. (Recommended)

B) LLM이 일반 지식으로 가능한 한계를 추론해 추가한다.

C) 한계 분석은 실험 아이디어 뒤의 부록으로만 제공한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 14
실험 아이디어 생성은 어떤 경계 안에서 허용할까요?

A) 기존 연구 한계와 사용 가능한 데이터셋/코드 근거를 바탕으로 아이디어 후보를 생성하되, 논문 문장·문헌리뷰 산문 작성은 하지 않는다. (Recommended)

B) 논문 introduction, related work, contribution 문장 초안까지 생성한다.

C) 아이디어 생성 없이 실험 계획만 작성한다.

X) Other (please describe after [Answer]: tag below)

[Answer]:

## Question 15
실험 계획의 최소 산출물은 무엇인가요?

A) 가설, 비교 baseline, 데이터셋, metric, 실험 절차, 예상 리스크, 필요한 구현/리소스, 근거 링크를 포함한다. (Recommended)

B) 간단한 bullet list 수준의 실험 아이디어와 TODO만 포함한다.

C) 재현 가능한 코드 skeleton까지 생성한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 16
Notion 저장은 어떻게 제공할까요?

A) 사용자가 연결한 Notion workspace/page에 novelty 분석 결과를 저장한다. 저장 전 미리보기와 사용자 승인 단계를 둔다. (Recommended)

B) 분석이 끝나면 자동으로 Notion에 저장한다.

C) Notion 저장은 v1에서 제외하고 Markdown export만 제공한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 17
DocSuri 내부 저장과 Notion 저장의 관계는 어떻게 둘까요?

A) 내부 DB/S3에 owner-scoped 세션과 결과를 저장하고, Notion은 선택적 외부 export로 둔다. (Recommended)

B) Notion에만 저장하고 DocSuri에는 저장하지 않는다.

C) 세션 중에만 유지하고 저장하지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 18
U11 novelty 에이전트 실행 방식은 무엇이 적합한가요?

A) API는 job 생성/상태 조회만 담당하고, 별도 U11 Agent Worker가 SQS job을 처리한다. MCP/Agent-Browser/Notion tool은 worker 내부 sidecar 또는 internal gateway로만 접근한다. (Recommended)

B) Backend API 컨테이너 안에서 동기 요청으로 모두 처리한다.

C) Lambda 중심으로 agent loop와 tool call을 처리한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 19
성능/응답 UX는 어떻게 잡을까요?

A) U7/U8처럼 온디맨드 비동기 작업으로 둔다. 진행 상태, 부분 결과, 실패 소스 표시, 재시도 가능 상태를 제공한다. (Recommended)

B) 검색과 동일하게 P50 3초 내 전체 결과를 반환해야 한다.

C) 결과가 완성될 때까지 화면을 blocking 상태로 둔다.

X) Other (please describe after [Answer]: tag below)

[Answer]: A, 세션 페이지 종료 후 재접속시에도 진행 상태를 조회할 수 있도록 한다. 재접속 시 진행 상태가 완료되었으면 결과를 바로 보여주고, 진행 중이면 부분 결과를 보여주고 재시도/취소 옵션을 제공한다.

## Question 20
비용과 사용량 제한은 어떻게 둘까요?

A) 기존 NFR-C1 안에서 U6 CostGuard와 rate limit을 재사용하고, 외부 검색/LLM/tool call 횟수에 per-job budget을 둔다. 초과 시 부분 결과와 기권을 반환한다. (Recommended)

B) U11 전용 월 예산을 새로 신설한다.

C) v1에서는 비용 제한 없이 품질을 우선한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 21
품질 게이트(QT)는 어떻게 신설/개정할까요?

A) QT-8을 U11 novelty용으로 개정한다: 근거 출처 정확도, 날조 인용 0건, 유사 연구 적중, tool 장애 저하 처리, Notion 저장 무결성을 차단성으로 본다. (Recommended)

B) 기존 QT-8을 그대로 사용한다.

C) 수동 QA만 수행하고 자동 품질 게이트는 두지 않는다.

X) Other (please describe after [Answer]: tag below)

[Answer]: X) 독립적인 품질 게이트를 두되, U11 novelty 에이전트와 문헌탐색&근거형성 에이전트가 공유하는 공통 산출물에 대해서는 공동 품질 게이트를 둔다. 각 에이전트는 자체 산출물에 대해 별도 품질 게이트를 둔다.

## Question 22
업로드 문서 또는 upstream EvidenceBundle과 외부 tool 호출의 프라이버시 경계는 어떻게 둘까요?

A) 원문/EvidenceBundle은 DocSuri 내부 저장소/LLM 입력에만 사용하고, 외부 웹 검색에는 최소 질의어·키워드·익명화된 요약만 보낸다. 사용자 삭제/초기화 기능을 제공한다. (Recommended)

B) 품질을 위해 원문/EvidenceBundle 전체를 외부 검색/tool provider에 보낼 수 있다.

C) 원문/EvidenceBundle은 저장하지 않고 처리 직후 삭제한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 23
Security Extensions
Should security extension rules be enforced for U11 novelty agent?

A) Yes — enforce all SECURITY rules as blocking constraints. (Recommended)

B) No — skip all SECURITY rules for U11 novelty agent.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 24
Resiliency Extensions
Should the resiliency baseline be applied to U11 novelty agent?

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance. (Recommended)

B) No — skip the resiliency baseline for U11 novelty agent.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 25
Property-Based Testing Extension
Should property-based testing rules be enforced for U11 novelty agent?

A) Yes — enforce PBT rules as blocking constraints for U11 business logic and serialization/state invariants.

B) Partial — enforce PBT only for pure functions, DTO round-trips, session state invariants, and tool-result normalization. (Recommended)

C) No — skip PBT rules for U11 novelty agent.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 26
이번 사이클의 산출물 범위는 어디까지인가요?

A) Requirements 질문 답변과 requirements.md 개정까지만 진행한다.

B) Requirements, User Stories, Units Generation까지 진행한다. (Recommended)

C) Construction 계획까지 이어서 진행한다.

D) 코드 구현까지 바로 진행한다.

X) Other (please describe after [Answer]: tag below)

[Answer]: 

