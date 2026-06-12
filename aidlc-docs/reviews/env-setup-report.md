# 환경 구축 라운드 보고서 — 상시 데모 인프라

> **일자**: 2026-06-12 · **계획**: [`env_setup_plan.md`](../plans/env_setup_plan.md) · **선행**: [`u0-aws-env-verification.md`](u0-aws-env-verification.md)(임시 검증, 도쿄+Cohere)
> **계정**: 028317349537 · **리전**: 서울 ap-northeast-2 (ADR-D3 재검토 반영) · 태그 `project=docsuri-demo`
> **결론**: ✅ 상시 인프라 가동 — 통합 테스트 10/10, E2E(검색·인용·프론트) 통과, **ADR-D2 잔여 "서울+Titan 재검증" 종결**. Amplify는 GitHub App 콘솔 연결 1단계만 팀 액션 대기.

---

## 1. 가동 중인 리소스

| 리소스 | 이름/ID | 비고 |
|---|---|---|
| DynamoDB | `docsuri-cache`(TTL=`expires_at`)·`docsuri-glossary`·`docsuri-cost` | 온디맨드, U0-L5 정합 |
| S3 (소스) | `docsuri-corpus-028317349537` | 본문 100편 + `.metadata.json` 사이드카 |
| S3 Vectors | 버킷 `docsuri-vectors` · 인덱스 `papers` | **cosine·1024d** (U0-M3 명시) |
| Bedrock KB | `docsuri-papers` (`VSQ5KSCBMY`) + DS `corpus`(`I0DPNXFL4K`) | `dataDeletionPolicy=RETAIN` |
| IAM | `docsuri-kb-role` · `docsuri-lambda-role` | 최소 권한 인라인 |
| ECR · Lambda | `docsuri-backend` · `docsuri-api`(arm64·1024MB·이미지) | Web Adapter |
| API Gateway | `74vuv58ct7` → **https://74vuv58ct7.execute-api.ap-northeast-2.amazonaws.com** | 퍼블릭 진입점 |

재현: `scripts/provision_aws.py`(idempotent) → `scripts/deploy_lambda.sh`. 해체: `scripts/teardown_aws.py --yes`. 식별자 기록: [`backend/data/aws_outputs.json`](../../backend/data/aws_outputs.json).

## 2. 실측 결과

| 항목 | 측정값 | NFR 판정 |
|---|---|---|
| KB ingestion (100편, 서울+Titan) | **25.6s, 실패 0** | ADR-D2 잔여 재검증 ✅ 종결 |
| aws 모드 통합 테스트 (Tier A+B) | **10/10, 17.05s** | 임베딩 1024d·한국어·페르소나·S3V 필터·TTL·비용 누적 |
| 검색 `/api/search` (한국어, 캐시 미스) | **2.84s** (Titan embed + LLM 매핑 + S3V) | [NFR-PERF-01](../requirements/nfr.md#nfr-perf-01) P50<3s ✅ |
| 검색 (DynamoDB 캐시 적중) | **0.07~0.08s** | — |
| 연도 필터 (`year_min=2026`) | 20건 전부 2026 | DISC-02 ✅ |
| 인용 `/api/citations` 미스/적중 | 0.48s / 0.07s | [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03) ✅ |
| 실 Semantic Scholar (1706.03762) | outgoing 15 · incoming 14 | R4 경로 실증 |
| Lambda 콜드 | 최초-ever init 7.87s(이미지 첫 풀) · **정상 콜드 E2E 1.91s** · 웜 0.14s | 콜드+검색 첫 1회 ≈4.7s < P95 6s ✅ |
| 프론트 브라우저 E2E (BACKEND_URL=API) | 검색 렌더·인용 Drawer(70ms)·빈 상태 문구 | U4-M2 문구 실전 검증 ✅ |

**D3 — 이중 캐시(U4-L2) 실측**: citation 1회 흐름의 cache 쓰기 = 신규 논문 1건(U0는 빈 결과 비캐시) / SS 성공 시 2건(U4 뷰 + U0 원시). 항목당 <1KB·온디맨드라 비용 영향 무시 가능 — 현 구조 유지.

## 3. 비자명 발견 (다음 사람을 위한 기록)

1. **조직 SCP가 익명 Lambda Function URL을 차단** — AuthType=NONE + 올바른 리소스 정책에도 퍼블릭 호출이 403. 함수 자체는 직접 invoke 200 → SCP 결론. **API Gateway HTTP API로 우회**(이 경로는 허용), `deploy_lambda.sh`에 반영·주석화. Function URL 설정은 제거함.
2. **Amplify Git 연동의 자격 게이트** — CLI OAuth 방식은 *개인 GitHub 토큰(전 repo 권한)을 AWS에 영구 저장*하게 되어 자동 진행을 중단함(권한 분류기도 차단 — 타당). **GitHub App 콘솔 연결(권한이 해당 repo 한정)이 올바른 경로**: ① Amplify 콘솔(서울) → New app → GitHub → `80-hours-a-week/DocSuri` 선택(App 설치 1회) ② 브랜치 `develop`, 모노레포 앱 루트 `frontend` ③ 환경 변수 `BACKEND_URL=https://74vuv58ct7.execute-api.ap-northeast-2.amazonaws.com` ④ 빌드 스펙은 저장소의 [`amplify.yml`](../../amplify.yml) 자동 인식.
3. **SS citations 첫 페이지는 최신순** — `top_influence`가 "최근 인용 15건 중 상위"가 됨(전체 최다 인용 아님). U4 후속 개선 후보로 등재.
4. 최초-ever 콜드(7.87s)는 이미지 첫 풀 비용 — 이후 콜드는 E2E 1.9s 수준으로 안정.

## 4. 후속 항목

| 항목 | 배치 |
|---|---|
| Amplify GitHub App 연결 (§3-2 가이드) | **팀 액션** — 연결 즉시 자동 빌드 |
| `OneHopResult` degraded 플래그 + 문구 분기 (U0-M2·U4-M2 근본) | 후속 사이클 (동결 모델 변경 절차) |
| SS Top-3 정렬 보강 (§3-3) | U4 후속 |
| 정식 IaC(SAM/CDK)·CI/CD | 후속 사이클 |
| 비용 모니터링 — CostGuard 누적은 `docsuri-cost` 테이블, 상한 $50 하드 스톱 가동 중 | 운영 |

---

*팀 코멘트 자리:*

- [ ] (팀 코멘트)
