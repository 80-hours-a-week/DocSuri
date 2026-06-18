# u7-summarization-code-generation-plan.md — Code Generation 계획 (Part 1: Planning)

**단계**: CONSTRUCTION → Code Generation (유닛별 루프, U7) · **유닛**: U7 Summarization · **트랙**: 단일 트랙 · **일자**: 2026-06-19
**근거(SSOT)**: `construction/u7-summarization/{functional-design,nfr-requirements,nfr-design,infrastructure-design}/` 전부 · 계획서 답변(FD 17·NFRReq 15·NFRDes 10·Infra 9) · 기존 모듈 선례(`backend/modules/discovery` src-layout·real 어댑터, `backend/modules/library` 마이그레이션)
**본 문서 = Code Generation의 단일 진실원본(SSOT).** Part 2(생성)는 이 단계 시퀀스를 **정확히** 따른다(하드코딩·일탈 금지). 본 Part 1은 **승인 게이트** — 승인 전 코드 미생성.

---

## 1. 유닛 컨텍스트 (Part 1 — Step 1·3)

- **코드 위치(워크스페이스 루트)**: `backend/modules/summarization/` (모노레포 모놀리스 모듈, src-layout — discovery 선례). **문서**: `aidlc-docs/construction/u7-summarization/code/`(markdown만).
- **구현 스토리**: US-S1(구조화 요약)·US-S2(한국어 번역)·US-S3(출처보기+기권)·US-S4(개인화)·US-S5(온디맨드 캐시/스트리밍)·US-S6 기여(비용 게이트·근거화 운영).
- **의존(소비)**: U1 전문(S3 `stored_full_text_ref` read=capability)·U6 `CostGuardCircuitBreaker.get_budget_state`·`ObservabilityHub.emit*`(`shared/ports`)·U3 accounts(개인 용어집 FK·인증)·게이트웨이(인증/인가/레이트리밋). **신규 DTO**: `shared/dtos/summarization`(PROVISIONAL).
- **소유 엔티티(DB)**: RDS `user_glossary`(개인 용어집). **소유 스토리지**: S3 `summaries/` 프리픽스·Redis `sum:` 키스페이스.
- **서비스 경계**: 온디맨드 요약/번역 읽기 경로. 근거화 = **U7 고유 결정적 게이트**(검색용 enforce 미사용). 비용/관측 = U6 단일 권위 소비.
- **real-first**: 실 어댑터 단일본(Bedrock·S3·Redis·RDS). **Production Mock Adapter 없음**; 테스트는 테스트 전용 Fixture/Stub.
- **불변식**: INV-1(C-2 추출)·INV-2(비용/관측 U6)·INV-3(SEC-9 비노출)·INV-4(fail-closed)·INV-5(캐시 키 immutable).

### 목표 모듈 구조 (greenfield 신규)
```
backend/modules/summarization/
├── pyproject.toml · ruff.toml
├── src/summarization/
│   ├── domain/      models·source_selector·refiner·glossary·length_router·grounding·assembler·cache_key
│   ├── service/     orchestrator
│   ├── ports/       ports (Llm/Store/FullText/GlossaryRepo/Cost/Observability)
│   ├── adapters/    settings·bedrock_llm·s3_redis_store·s3_full_text·rds_glossary   ← real 단일본
│   ├── api/         router(/api/summarize 스트리밍)·gateway_seam
│   ├── prompts/     템플릿(시스템 지시·본문 격리·persona·용어집·grounding 지시)
│   └── real_wiring.py
├── migrations/      001_create_user_glossary.sql
└── tests/           conftest(Fixture/Stub)·test_domain_*·test_orchestrator·test_pbt_*·test_integration_*
```

---

## 2. 생성 단계 (Part 2 — 승인 후 순차 실행, 체크박스)

> **NO HARDCODED LOGIC · FOLLOW PLAN EXACTLY · 각 단계 완료 즉시 [x].** 앱 코드=워크스페이스 루트, 문서=aidlc-docs만.

### 프로젝트 구조
- [x] **Step 1 — 모듈 스캐폴드**: `pyproject.toml`(docsuri-summarization; deps `docsuri-shared`·`pydantic`; optional `api=[fastapi]`·`real=[boto3]`; dev `pytest`·`hypothesis`·`ruff`; uv.sources shared 경로) · `ruff.toml` · `src/summarization/` 트리 + `__init__.py`.

### 비즈니스 로직 (도메인 — 기술 무관 코어)
- [x] **Step 2 — 도메인 모델** `domain/models.py`: `SummaryRequest`·`RequestContext`·`SummaryCacheKey`·`SourceText`·`RefinedSource`/`Section`·`Glossary`/`TermMapping`·`SummaryDraft`·`Anchor`·`TranslationDraft`·`GroundingInput`·`AnchorVerdict`·`SummaryResponse` union(`SummaryResultDTO`·`AbstainDTO`·`CostDegradedDTO`·`SourceUnavailableDTO`). pydantic v2·SEC-9 경계. (domain-entities.md 1:1)
- [x] **Step 3 — 포트** `ports/ports.py`: `LlmGatewayPort`(스트리밍 generate)·`SummaryStorePort`(read/write-through)·`FullTextSourcePort`·`GlossaryRepositoryPort`·`CostGuardPort`·`ObservabilityPort`(U6 위임 추상).
- [x] **Step 4 — InputRefiner** `domain/refiner.py`: 노이즈 제거(BR-S3 Q2 — Header/Footer·페이지번호·저작권·저자정보만; 캡션·Appendix·Supplementary·수식 보존)·참고문헌 제거·섹션 도출(Q6 정규식 헤딩/Table/Figure→label+span, 실패 시 span-only)·SANITIZE(제어문자·본문 격리·토큰 카운트).
- [x] **Step 5 — SourceSelector·CacheKey·LengthRouter** `domain/{source_selector,cache_key,length_router}.py`: task별 소스 + 초록 폴백(Q1)·immutable 키 빌드(BR-S1)·단일/맵-리듀스 분기(Q3, 토큰 예산 형태).
- [x] **Step 6 — GlossaryResolver** `domain/glossary.py`: P1 시드(코드 자산)∪P2 개인 머지·프롬프트 강제 매핑 + 결정적 후치환(BR-S4 Q8, 조사 안전 단순 명사).
- [x] **Step 7 — GroundingValidator** `domain/grounding.py`: 결정적 체크(앵커 실재성·수치 정규화 일치·스키마 완전·잘림/빈출력)·verdict(BR-S7 Q4/Q15, LLM-judge 미사용).
- [x] **Step 8 — ResultAssembler** `domain/assembler.py`: 조립·SEC-9 비노출 필터·후치환 적용·종단 union 매핑(BR-S9).
- [x] **Step 9 — Orchestrator** `service/orchestrator.py`: 파이프라인(cache→cost→source→refine→glossary→len→generate(stream)→groundingValidate(1회 재시도)→assemble→write-through→telemetry)·**버퍼-검증-점진렌더**(Q5/BR-S8)·**저하 3계층 구분**(비용/장애/소스, NFR Design §1.3)·비차단 텔레메트리.
- [x] **Step 10 — 프롬프트 템플릿** `prompts/`: 시스템 지시·본문 격리(`[지시]┃[데이터]<paper>`)·persona(expert/beginner)·용어집 주입·grounding 지시·초록 밖 디테일·§3 JSON 계약.

### 비즈니스 로직 단위 테스트
- [x] **Step 11 — 도메인 단위 테스트 + PBT** `tests/`: `conftest.py`(테스트 전용 Fixture/Stub 포트)·`test_domain_*`(refiner 보존경계·glossary 후치환·grounding 앵커·source 폴백·cache_key·assembler SEC-9)·`test_orchestrator`(버퍼-검증·3계층 저하·기권)·`test_pbt_*`(Hypothesis PBT-S1~S5). **Production Mock Adapter 미생성**(테스트 더블만).

### 어댑터 레이어 (real-first 단일본)
- [x] **Step 12 — BedrockLlmGatewayAdapter** `adapters/{settings,bedrock_llm}.py`: Sonnet 4.6/Haiku 4.5 `InvokeModelWithResponseStream`(boto3 bedrock-runtime, async)·task→모델 선택(BR-S5)·타임아웃/1회 재시도/서킷→기권(Q1)·U6 게이트웨이 경유 형태.
- [x] **Step 13 — SummaryStoreAdapter·FullTextSourceAdapter** `adapters/{s3_redis_store,s3_full_text}.py`: read-through(Redis `sum:`→S3 `summaries/`)·write-through·immutable 키 경로·전문 S3 read(`stored_full_text_ref`)·실패 시 폴백/기권.
- [x] **Step 14 — GlossaryRepository(RDS) + 마이그레이션** `adapters/rds_glossary.py` + `migrations/001_create_user_glossary.sql`: owner 스코프 CRUD·`glossary_ver` 증가·DDL(infrastructure-design.md §2.3, 기존 러너 패턴).

### API 레이어
- [x] **Step 15 — FastAPI 라우터 + gateway_seam** `api/{router,gateway_seam}.py`: `POST /api/summarize`(task·persona·스트리밍 응답)·요청 검증(SEC-5)·전역 fail-closed 핸들러(INV-4)·비용 게이트/관측 invocation 경계(U6 ports 소비).
- [x] **Step 16 — real_wiring + 마운트(제안)** `real_wiring.py`(실 어댑터 조립 `build_real_orchestrator`) 생성 완료. **`backend/wiring.py`는 변경하지 않음** — 쉘 소유 + `test_app_shell.py`의 모듈 집합 단언 보호(조율 존). 마운트 mounter는 **사인오프-레디 스니펫으로 `code/README.md`에 제시**(env 토글·graceful-skip·real-first). @ELSAPHABA 사인오프 후 `_INTEGRATIONS` 추가 + 쉘 테스트 갱신.

### 통합 테스트 · 문서 · 배포
- [x] **Step 17 — 통합 테스트(real, self-skip)** `tests/test_integration_*.py`: 실 Bedrock/S3/Redis/RDS 대상(자격증명 부재 시 자동 skip — discovery 선례)·근거화 통과/기권·캐시 read/write·스트리밍.
- [x] **Step 18 — 문서 + 배포 아티팩트**: `aidlc-docs/construction/u7-summarization/code/README.md`(코드 요약·실행/검증·의존성 플래그)·배포 체크리스트(IaC 증분·마이그레이션·IAM = infrastructure-design 연계, 조율 존 표기).

---

## 3. 스토리 추적성 (단계 → 스토리)

| 스토리 | 단계 |
|---|---|
| US-S1 구조화 요약 | 2·4·5·9·10·12 |
| US-S2 한국어 번역 | 2·6·9·10·12 |
| US-S3 출처보기·기권 | 2·4·7·8·9·11 |
| US-S4 개인화(persona·뷰·용어) | 2·6·10·14 |
| US-S5 온디맨드 캐시/스트리밍 | 9·13 |
| US-S6 기여(비용·근거화 운영) | 3·7·9·15 |

---

## 4. 검증 기준 (Build & Test 연계)

- `pytest`(단위 + PBT, Fixture/Stub) green · `ruff` clean · 통합 테스트는 자격증명 가용 시 실행(부재 시 skip).
- 코드=`backend/modules/summarization/`(워크스페이스 루트), 문서=`aidlc-docs/`. **Production Mock Adapter 미생성** 확인.
- 마운트(`backend/wiring.py`) = 조율 존 — 제안만, 사인오프 별도.

---

## 5. 다음 절차

1. 본 Part 1 계획 **승인**(전체 시퀀스 대상). 변경 요청 시 갱신 후 재승인.
2. 승인 → Part 2 생성(Step 1~18 순차, 각 단계 [x]·스토리 [x]).
3. 생성 완료 → 완료 메시지 + 리뷰 게이트 → 승인 시 **Build & Test**(U7 CONSTRUCTION 마무리).

> 본 계획은 **리뷰 게이트(Part 1)** 입니다. 승인 전 코드를 생성하지 않으며, 아직 커밋하지 않았습니다.
