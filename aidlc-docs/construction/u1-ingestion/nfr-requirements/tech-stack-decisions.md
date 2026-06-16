# tech-stack-decisions.md — U1 Ingestion 기술 스택 결정 (ADR, 프로덕션)

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: 계획서 프로덕션 답변 배너 · FD 산출물 · `requirements.md`(C-5 AWS) · [[project-aws-integration-spike]]
**스코프**: 단일 프로덕션 트랙(데모 폐기). `[전역]`=U2~U6 상속. **팀 리뷰 대상**(특히 TD-3·TD-4).

> 형식: 결정 · 근거 · 대안 · 전환 비용. 수치/리전/IaC는 Infra Design.

---

## TD-1 — 워커 언어/런타임: **Python**
- **근거**: ML/임베딩/arXiv(arxiv.py·OAI-PMH) 생태계, Hypothesis(PBT), 선행 사례(사이클 1 Python). 
- **대안**: TS/Node(프런트 통일). 폴리글랏(워커 Python·API 별도).
- **전환 비용**: 워커는 독립 배포(DQ1)라 API 언어와 분리 가능 — 낮음. (API 언어는 U2~U4 NFR Requirements.)

## TD-2 — arXiv 접근: **OAI-PMH(시드 하베스트) + Atom 질의 API(증분)**
- **근거**: 풀 슬라이스 수십만(Q1=D) 시드는 OAI-PMH(`set=cs`, resumptionToken) 대량 하베스트 적합; 일 증분은 Atom API(updated 기준 Q7=A). RES-8 보수 쿼터(예양 지연). **이 프로토콜 한도가 TD-있음: RES-9 타임아웃/재시도 수치(nfr-requirements §3) 근거.**
- **대안**: Atom API 단독(소규모엔 단순하나 수십만 하베스트엔 부적합).
- **전환 비용**: 낮음(어댑터 교체).

## TD-3 [전역] — 임베딩 모델 + VectorSpec: **Cross-lingual 임베딩(Cohere Embed Multilingual v3, Bedrock) · 1024차원 · 코사인** _(2026-06-16 팀 결정 Titan→cross-lingual)_
- **근거**: **한국어 사용자/팀이 영어 arXiv 코퍼스를 질의** → cross-lingual 모델이 한국어 질의와 영어 논문을 동일 벡터 공간에 매핑(KR↔EN 검색). Titan V2(영어 최적)는 한국어 질의 열위. Cohere Embed Multilingual v3는 Bedrock 제공·100+ 언어·1024차원으로 **AWS 트랙·기존 VectorSpec(1024·코사인) 그대로 유지**.
- **가정(팀 확인됨, 2026-06-16)**: **cross-lingual 질의 가정 확정.** (영어 전용이었다면 Titan V2로 충분했으나 팀이 cross-lingual 채택 — 한국어 질의 대응.) cross-lingual은 KR·EN 모두 처리.
- **교차 유닛**: U2 질의 임베딩이 **동일 모델** 사용(VectorSpec 불변식); **QT-2 관련도 평가셋에 한국어 질의 포함**해 cross-lingual 검색 품질 검증 필수.
- **대안**: Bedrock Titan V2(영어 최적, spike 검증); 자체 호스팅 다국어 오픈 모델(multilingual-e5 / BGE-M3, GPU 운영).
- **전환 비용**: **매우 높음 — VectorSpec 변경 = 전체 코퍼스(수십만) 재임베딩**. 사실상 단방향. → 본 단계 PIN. 현 Bedrock 다국어 모델 가용성/단가 확인 권장.

## TD-4 [전역] — 벡터+lexical 스토어: **OpenSearch** _(팀 결정 2026-06-16)_
- **요건(3종 모두 필수)**: (i) ANN 벡터 검색 + (ii) BM25/FTS lexical(U2 하이브리드 FR-2·비용 서킷 lexical 폴백 US-R2) + (iii) **per-paperId 멱등 삭제/tombstone**(FD Q13=B·BR-14·INV-1).
- **근거**: OpenSearch는 k-NN ANN + BM25 + 신뢰성 문서 삭제를 **단일 스토어**로 충족; Bedrock KB 백킹으로도 일반적; TD-3 임베딩(Cohere Embed Multilingual v3, 1024·코사인)과 정합.
- **대안**: **Aurora PostgreSQL(pgvector+FTS)** — 단일 스토어·트랜잭션 삭제·최저 운영비; **S3 Vectors + Bedrock KB**(spike 산출)는 **벡터-ANN 전용** → 동반 lexical 스토어 필요 + 삭제 최종일관성 검증 필요(요건 ii·iii 미충족).
- **전환 비용**: 스토어 변경 = 재색인(재임베딩은 불요 if VectorSpec 동일). **팀 결정 필요**: OpenSearch(권장) vs Aurora pgvector vs S3 Vectors+동반.

## TD-5 — 스케줄러: **EventBridge Scheduler**(증분) + 수동 CLI(triggerFullRebuild)
- **근거**: 관리형 cron(일 1회 US-I2). 시드/재구축은 운영 수동 트리거(AS-5 런북).
- **전환 비용**: 낮음(스케줄 트리거 어댑터).

## TD-6 — 큐/DLQ: **SQS + DLQ**
- **근거**: 재시도·소진 격리(US-I3·BR-16/17), 이벤트 경로(Q12=B) 백본. 관리형·at-least-once.
- **전환 비용**: 낮음(포트 뒤 추상화).

## TD-7 — 오브젝트 스토리지(OA 전문 보관): **S3**
- **근거**: Q2=C 전문 보관(BR-20·StoredFullText), **공개 차단(SEC-9)** + at-rest 암호화(SEC-1), 재구축·재처리 재사용(RES-2).
- **전환 비용**: 낮음.

## TD-8 — PBT 프레임워크: **Hypothesis**(Python)
- **근거**: TD-1 종속; PBT-08 차단성(P1/P3/P4/P5)·도메인 제너레이터·shrinking·시드 재현성.

## TD-9 — 패키징: **컨테이너(이미지 다이제스트 핀, SEC-10)**
- **근거**: 재현 빌드·SEC-10(`:latest` 금지). **실배포 타깃(ECS/Fargate vs Lambda)·오토스케일·리전은 Infra Design**.
- **전환 비용**: 런타임 타깃은 Infra에서 확정.

## TD-10 — 빌드/의존성 + 공급망(SEC-10): **모노레포 `ingestion/` + uv/poetry + 락파일 + SCA + SBOM**
- **근거**: UQ2=A 모노레포; SEC-10 락파일·취약점 스캔·SBOM 산출(스캔 **CI 실행**은 NFR Design).
- **전환 비용**: 낮음.

---

## 비용·상한 주석 (NFR-C1)
- **NFR-C1 월 상한 = $1600/월**(2026-06-16 팀 결정 — 팀 AWS 크레딧 전액). **시스템 전역 상한**: U1 임베딩+스토리지뿐 아니라 전 유닛 AWS 지출(Bedrock 임베딩·U2 Bedrock LLM 근거화·OpenSearch·RDS·컴퓨트·S3) 합계가 $1600/월 이내. U1은 그 슬라이스 하나이며 **U6.CostGuardCircuitBreaker가 시스템 상한 강제**(80% 경보/100% 전 저하). 임베딩 1회(시드) 비용은 디덥(BR-4)·본문 크기 정책(BR-21)으로 통제.
- _주의(팀 확인): $1600이 일회성 크레딧 풀이면 런웨이=풀÷월지출; 월 한도 자체는 지시대로 $1600._

## 결정 완료(팀, 2026-06-16) & 후속
- ✅ **TD-4 스토어 = OpenSearch**(대안 Aurora pgvector / S3 Vectors+동반 기각) — [전역].
- ✅ **TD-3 = cross-lingual**(cross-lingual 질의 가정 확정) — [전역].
- ✅ **BR-1 = 엄격 OA 라이선스 검증**(재배포 가능 라이선스만; 미표기/불가 NON_OA 배제).
- ✅ **NFR-C1 = $1600/월**(시스템 전역).
- ✅ **FD 문서 규약 = 완전 추상**(FD는 구체 모델/차원/스토어/큐 미기재; NFR docs가 단일 진실 원천).
- 후속(보류): 유닛별 비용 배분 · 리전/배포 타깃(Infra) · CI 스캔 파이프라인(NFR Design) · $1600 크레딧 풀 vs 월 한도 런웨이 확인.
