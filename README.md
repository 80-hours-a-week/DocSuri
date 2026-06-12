# DocSuri

AI/ML 논문 탐색·이해·차별화·인용 추적을 돕는 한국어 우선 연구 보조 도구 (MVP).

본 저장소는 **AI-DLC(AI-Driven Development Lifecycle)** 방법론으로 개발된다 — 모든 코드는 [`aidlc-docs/`](aidlc-docs/)의 동결 산출물(요구사항 → 스토리 → unit 분해 → 컴포넌트 모델 → ADR)에서만 도출한다.

## 구조

| 경로 | 내용 |
|---|---|
| [`aidlc-docs/`](aidlc-docs/) | AI-DLC 산출물 — 요구사항·페르소나·스토리·unit·컴포넌트 모델·ADR·계획 로그 |
| [`backend/`](backend/) | Python 백엔드 (모듈러 모놀리스, unit별 모듈: `docsuri/u0/`·`u1/` …) |
| [`frontend/`](frontend/) | Next.js 프론트엔드 (App Router + shadcn/ui — U1 Discover 검색 UI) |

## 시작점

- 설계 단일 진실: [`aidlc-docs/design-artifacts/component-model.md`](aidlc-docs/design-artifacts/component-model.md) (동결) · [`architecture_decision_record.md`](aidlc-docs/design-artifacts/architecture_decision_record.md) (D1~D10 확정)
- 백엔드 실행·테스트: [`backend/README.md`](backend/README.md)
- 프론트엔드 실행: [`frontend/README.md`](frontend/README.md) — 단독(mock) 또는 `BACKEND_URL`로 백엔드 연결

## 기술 스택 (ADR 확정, 2026-06-10)

Python 3.12 + FastAPI · Amazon Bedrock(Claude Haiku 4.5, Titan Text Embeddings V2) · Bedrock Knowledge Bases + S3 Vectors · DynamoDB · Lambda + API Gateway + Amplify Hosting (풀 서버리스, 서울 리전 — ADR-D3 재검토 반영) · Next.js + shadcn/ui + React Flow
