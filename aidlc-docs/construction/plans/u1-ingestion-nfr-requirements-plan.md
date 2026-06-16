# u1-ingestion-nfr-requirements-plan.md — NFR Requirements 계획 + 질문 게이트

**단계**: CONSTRUCTION → NFR Requirements (유닛별 루프, U1) · **유닛**: U1 Ingestion · **일자**: 2026-06-16
**근거**: `construction/u1-ingestion/functional-design/`(FD 산출물·답변 Q1~17=A·**FD Q13=B**) · `requirements.md` · `unit-of-work.md`(UQ2 모노레포·UQ5 공유계약)
**목적**: U1 비기능 요구사항 확정 + **기술 스택 선정**. FD 보류 수치(AS-4)·VectorSpec 구체값 확정.
**고도(altitude)**: **스택 종류·NFR 목표**를 정한다. 클라우드 자원 매핑·리전/AZ 토폴로지(RES-2)는 **Infra Design**; CI/CD·롤백·배포·복원력 테스트(RES-4/RES-12)는 **NFR Design**으로 계속 보류. (단 SEC-10의 "무엇을 산출/핀할지"는 본 단계, "CI에서 어떻게 스캔할지"는 NFR Design.)
**데모 우선**: 머지 기준 "데모가 부팅되는가". 권장안은 로컬 부팅·저비용에 편향하되 프로덕션 타깃(팀 AWS 선행 사례)을 함께 문서화(2-트랙).
**검증**: 본 계획은 적대적 비평(3 렌즈: 고도/경계·완전성·근거/교차유닛) 1패스로 보강(arXiv 접근 질문 신설·스토어 능력 기준·철회 신호 타당성 등).

> **⚠️ 프로덕션 직행 답변(2026-06-16)** — 팀 결정으로 **데모 트랙 폐기**(§7 "데모 우선" 무효). **§4 답변 = 프로덕션**: Q1=A(Python) · Q2=B(OAI-PMH 시드 하베스트 + Atom API 증분) · **Q3=cross-lingual(Cohere Embed Multilingual v3, Bedrock, 1024차원·코사인)[전역]**(2026-06-16 Titan→cross-lingual; 한국어 질의 대응, 질의 언어 가정 팀 확인) · **Q4=OpenSearch**(ANN+BM25+멱등 삭제 단일 스토어; **[전역]·팀 리뷰 포인트** — 대안 Aurora pgvector / S3 Vectors+동반 lexical) · Q5=B(EventBridge) · Q6=B(SQS+DLQ) · Q7=프로덕션 S3(전문 보관 **활성**, SEC-9 공개 차단) · Q8=A(Hypothesis) · Q9=컨테이너(ECS/Fargate 또는 Lambda — 실배포는 Infra) · Q10=프로덕션 배치(수십만 시드, 시간 단위 허용) · Q11=B(병렬 fetch/embed + 인덱스 쓰기 직렬화 — 단일 writer·FD BR-13 유지) · Q12=A(논문 단위 커밋 유지) · Q13=A(일 1회 증분, RPO=마지막 인제스천) · Q14=A(프로덕션 수치) · Q15=A+전문 신호(철회 탐지=메타+전문) · Q16=A + **NFR-C1=$1600/월 확정**(팀 AWS 크레딧 전액·시스템 전역; 기존 $300 대체) · Q17=A(RDS/OpenSearch/S3 암호화+TLS) · Q18=A(SEC-10 풀). **이 배너가 §4 인라인 [Answer]를 오버라이드.** 팀 리뷰 대상(특히 [전역] Q3·Q4).

> **[전역] 표기**: U1은 빌드 순서 #1이라 일부 결정(임베딩 모델/VectorSpec·벡터+lexical 스토어·공용 언어)은 U2~U6가 상속하는 **시스템 전역 계약**이다. 해당 질문에 `[전역]`.
> **FD 질문 인용**: FD 계획서의 질문은 `FD Q##`, 본 계획 질문은 `Q##`로 구분.

---

## 1. 유닛 컨텍스트 (NFR 렌즈)

- U1 = **비동기 인제스천 워커**(사용자 동기 경로 아님). 따라서:
  - **NFR-P1**(P50<3s) — **U2/U6 API 대상, U1 N/A**.
  - **NFR-A1**(99.5% 가용성) — API 대상; U1은 "복구·재시도·정체 없음"(NFR-R1, RES-7/9)으로 표현(SLA 아님).
  - **Usability(NFR-U*)** — **U1 N/A**(사용자 표면 없음; OP CLI/런북 인체공학은 Operations로, AS-5).
- U1 핵심 NFR 동인: **임베딩 비용(NFR-C1 주 동인)**, **시드 빌드 처리량/시간**, **최신성/RPO**(RES-2), **arXiv 쿼터 준수**(RES-8), **의존성 격리 수치**(RES-9, FD AS-4 확정).
- FD 잠금(프로덕션 재스코핑, L10 배너): 전문 청킹(FD Q2=C)·풀 슬라이스 5cat×5년(FD Q1=D)·이벤트 경로 활성(FD Q12=B)·철회 tombstone 활성(FD Q13=B)·논문 단위 원자성(FD Q8=A)·max-clamp 워터마크(FD Q17=A)·INV-1 커밋 순서.

---

## 2. NFR Requirements 실행 계획 (Step 2 — 답변 확정 후, 체크박스)

> 산출물은 `aidlc-docs/construction/u1-ingestion/nfr-requirements/` 에 생성. **답변(§4) 전 미생성.**

- [ ] **nfr-requirements.md** — U1 NFR 확정:
  - 확장성(시드 빌드 처리량·워커 동시성), 성능(인제스천 지연·배치·최신성/RPO), 가용성/신뢰성(워커 복구·RES-9 수치).
  - 보안: **SEC-1**(at-rest/TLS)·**SEC-5**(입력 검증)·**SEC-9**(공개 스토리지 차단)·**SEC-10**(공급망: 락파일·SCA·SBOM·이미지 다이제스트 핀).
  - 관측성(**NFR-O1 명시 처분**): 구조화 로깅·메트릭 라이브러리는 언어(Q1) 따름; 독립 워커(DQ1) → `U6.ObservabilityHub`(`emitFailureSignal`, BR-17) **전송 채널**은 데모=로컬 구조화 로그/인-프로세스 메트릭, 이벤트 백본 전송은 U6 NFR Requirements[전역]/Infra로 보류.
  - 유지보수성(PBT 프레임워크·모노레포 빌드).
- [ ] **tech-stack-decisions.md** — ADR 형식 결정 + 근거 + 데모/프로덕션 2-트랙 + 전환 비용:
  - 언어/런타임 · **arXiv 접근 클라이언트+프로토콜** · **임베딩 모델 + VectorSpec[전역]** · **벡터+lexical 스토어[전역]** · 스케줄러 · 큐/DLQ · 오브젝트 스토리지(FD Q2=A→데모 N/A) · PBT 프레임워크 · 데모 패키징.
  - **전환 비용 행 필수**: VectorSpec 변경=전체 재임베딩; 스토어 변경=재색인; S3 Vectors/KB 채택 시 lexical 동반 스토어 비용(아래 Q4).
- [ ] **VectorSpec 확정값[전역]** — 차원·모델 ref·거리 메트릭 구체값(U1 writer=U2 reader 동일). **ANN 호환 게이트**: 확정 VectorSpec(차원·거리 메트릭)이 선택 스토어의 ANN 인덱스 타입(예 pgvector HNSW/IVFFlat 차원·연산자)에서 지원되는지 교차 검증(domain-entities §8 / business-rules §6 동일 공간 불변식).
- [ ] **FD AS-4 수치 확정** — 재시도·백오프·타임아웃·동시성·배치 크기 구체값을 RES-8/9 근거로 고정(BR-10/16/18 갱신). **수렴 검증**: (타임아웃×재시도 엔벨로프) × 단일 워커 동시성(Q11) × arXiv 최소 요청 간격(Q2/RES-8)이 시드 빌드 시간 예산(Q10)에 수렴하고 쿼터 미위반.
- [ ] **추적성** — NFR/스택 결정 → NFR-C1/S1, RES-2/7/8/9, SEC-1/9/10, QT-4, C-5 역추적.

---

## 3. 가정 (잘못이면 §4 또는 지적으로 정정)

- **NS-1**: 리전/AZ 토폴로지(RES-2)·IaC·CI/CD·롤백·배포(RES-4)·복원력 테스트(RES-12)는 본 단계 밖(NFR Design/Infra).
- **NS-2**: VectorSpec·벡터+lexical 스토어·공용 언어 등 `[전역]` 결정은 U1에서 확정하되 U2~U6 상속(재논의 아님).
- **NS-3**: 정량 NFR(NFR-C1 $300/월, NFR-S1 ~3,000/동시 50)은 제안값 → U1 관점 확정/조정.
- **NS-4**: C-5(AWS 지향)는 프로덕션 타깃 선호이나 데모 부팅 스택과 분리(2-트랙).
- **NS-5**: **VectorSpec 소유권** — `shared/vector-spec` 계약 산출물은 **공유 임베딩 게이트웨이 레이어 소유**(UQ5=A). U1(빌드 #1)은 그 **구체값을 PIN**할 뿐이며, U1 writer·U2 reader가 동일 값을 소비하고 후속 유닛에서 **재결정하지 않는다**.

---

## 4. 명확화 질문 (Step 3 — `[Answer]:` 태그; A/B/C/D 또는 E=기타)

### A. 기술 스택 — 핵심

**Q1 [전역] — 워커 언어/런타임.**
- A) **Python** — ML/임베딩/arXiv 생태계·Hypothesis(PBT)·선행 사례. (권장)
- B) TypeScript/Node — 프런트(U5) 통일·fast-check.
- C) 워커=Python, API=별도(폴리글랏).
- **권장**: A. (API 언어는 U2~U4 NFR Requirements; 워커는 독립 배포라 분리 가능.)
- **[Answer]**:

**Q2 — arXiv 접근 메커니즘.** ArxivSourceClient(`fetchMetadataPage`/`resolveSliceCategories`)의 원천 접근 방식. **Q14 타임아웃/재시도 수치는 이 프로토콜의 문서화된 한도에 근거함.**
- A) **arXiv Atom 질의 API**(HTTP / `arxiv.py`), 시드·증분 모두, **~1 req/3s 예양 지연**(RES-8). (권장 — 데모 단일 메커니즘; cs.LG~1년 수천 건은 페이지네이션으로 수분 내)
- B) **하이브리드**: 시드(SEED_REBUILD)는 **OAI-PMH 하베스팅**(`set=cs`, resumptionToken — 대량 수집 적합), 증분은 Atom API.
- C) OAI-PMH 단독.
- **권장**: A(데모 단순). 슬라이스가 수십만으로 커지면(프로덕션) B로 승급. RES-8 보수 동시성(Q11=A)과 정합, Q14 수치의 근거.
- **[Answer]**:

**Q3 [전역] — 임베딩 모델 + VectorSpec.** U1 writer·U2 reader 공유 공간. **변경 = 전체 재임베딩.**
- A) **로컬 오픈 임베딩 모델**(예: sentence-transformers 계열, 384–768차원, 코사인) — 무료·로컬 부팅·결정적·데모 비용 0(NFR-C1 동인 제거). (권장 — 데모)
- B) **AWS Bedrock Titan Text Embeddings V2**(Seoul, 선행 spike 검증) — 프로덕션 타깃·검증, 단 AWS 의존·비용.
- C) 기타 임베딩 API.
- **권장**: A(데모)·B(프로덕션 타깃). 선택 후 VectorSpec 구체값 PIN(차원·모델 ref·거리 메트릭) + ANN 호환 게이트(§2). **팀 AWS spike 투자 고려해 B 선호 시 명시.**
- **[Answer]**:

**Q4 [전역] — 벡터 + lexical 스토어.** FD Q4=A(IndexRecord = vector + lexicalTerms). **선택 스토어는 (i) ANN 벡터 검색 + (ii) lexical/FTS(BM25) + (iii) per-paperId 멱등 삭제/tombstone(BR-14 strictly-newer-vN-wins·INV-1) 3가지를 모두 충족해야 함**(U2.HybridRetriever 하이브리드 FR-2·비용 서킷 lexical 폴백 US-R2/QT-3·FD Q13=B tombstone을 구속).
- A) **PostgreSQL + pgvector(ANN) + FTS(lexical)** — 단일 스토어로 (i)(ii)(iii) 충족·로컬 docker·RDS/Aurora 프로덕션 경로. (권장)
- B) **AWS S3 Vectors + Bedrock KB** — **벡터-ANN 전용**: 단독으로 (ii) lexical·(iii) 멱등 삭제 미충족 → **동반 lexical 스토어 필요 + 삭제 최종일관성 검증 항목**. 프로덕션 타깃이라도 하이브리드/철회 계약 보강 전제.
- C) OpenSearch/Elasticsearch — (i)(ii)(iii) 단일 스토어 충족.
- **권장**: A — 데모 단일 스토어로 3요건 일체. B 단독은 [전역] 스토어 계약(하이브리드·tombstone)을 벡터 능력만으로는 미충족.
- **[Answer]**:

**Q5 — 스케줄러(onSchedule, US-I2).**
- A) **경량**: 데모는 수동 CLI 트리거 + 단순 스케줄 태스크(cron 류). (권장)
- B) AWS EventBridge Scheduler(프로덕션).
- **권장**: A(데모)·B(프로덕션). triggerFullRebuild는 수동/CLI 진입(US-I1).
- **[Answer]**:

**Q6 — 큐/DLQ(재시도·DLQ, US-I3).**
- A) **DB 백드 큐/DLQ 테이블**(또는 인-프로세스 재시도) — 데모 단순·로컬. (권장)
- B) AWS SQS + DLQ(프로덕션).
- **권장**: A — 외부 큐 인프라 회피(FD Q12=A 이벤트 스텁과 정합).
- **[Answer]**:

**Q7 — 오브젝트 스토리지(OA 전문 보관).** FD Q2=A(초록 전용)에서 데모 부재.
- A) **데모 N/A**(전문 미보관 — SEC-9 정당화된 N/A); 프로덕션 Q2=C 승급 시 S3(공개 차단). (권장; FD BR-20 정합)
- B) 데모에도 메타 원천 보관(재구축 재취득 회피).
- **권장**: A.
- **[Answer]**:

**Q8 — PBT 프레임워크(QT-4/PBT-08).**
- A) **언어 따라**(Python→Hypothesis / TS→fast-check). (권장; Q1 종속)
- B) 예시 기반만(PBT 후순위).
- **권장**: A — PBT-08 차단성(P1/P3/P4/P5)·도메인 제너레이터·shrinking·시드 재현성.
- **[Answer]**:

**Q9 — 데모 패키징/런타임("부팅" 정의) + 이미지 핀(SEC-10 일부).**
- A) **docker-compose**(스토어 + 워커), **베이스 이미지 다이제스트 핀(`:latest` 금지, SEC-10)** — 재현 가능 로컬 부팅. (권장)
- B) 로컬 네이티브 실행.
- C) AWS 배포(이 단계 아님).
- **권장**: A — "부팅" = `docker compose up` + 시드 빌드. 실제 배포는 Infra Design.
- **[Answer]**:

### B. 확장성 (Scalability)

**Q10 — 시드 빌드 처리량/시간 목표** (cs.LG~1년 수천 건, US-I1).
- A) **단발 준비 작업 — 수십 분 내 허용**(실시간 아님). (권장; Q14 엔벨로프가 이 예산에 수렴)
- B) 더 빠르게(분 단위) — 동시성↑(쿼터 위험).
- C) 목표 미설정.
- **권장**: A — RES-8 쿼터 보수와 균형.
- **[Answer]**:

**Q11 — 워커 확장 모델.**
- A) **단일 워커·낮은 동시성**(RES-8 arXiv 보수 준수). (권장)
- B) 다중 워커 — 단일 writer 인덱스라 쓰기 직렬화 필요(**FD BR-13 REBUILD_LOCK 상호배제** 복잡).
- **권장**: A — 단일 writer 계약 정합·데모 충분.
- **[Answer]**:

### C. 성능 · 최신성 (Performance / Freshness)

**Q12 — 임베딩 배치 크기 + arXiv 페이지 크기.**
- A) **보수적 기본**(중간 배치·표준 페이지, 쿼터/타임아웃 내) — 구체값 tech-stack-decisions 고정. (권장)
- B) 큰 배치(처리량↑·재처리 비용↑).
- **권장**: A — NFR-C1·RES-8 균형. **불변식**: 임베딩 배치 크기는 embed 호출 처리량 최적화일 뿐, **커밋은 논문 단위 유지(FD Q8=A/BR-7)** — 다중 논문 배치도 논문별 IndexRecordBatch로 커밋.
- **[Answer]**:

**Q13 — 최신성/RPO 확정 (RES-2).**
- A) **증분 일 1회, RPO = 마지막 인제스천 시점**(재구축 가능 자산, 별도 백업 없음). (권장; 제안 확정)
- B) 더 잦은 증분(시간 단위).
- **권장**: A — RES-2 그대로. 데모는 수동 트리거로 충분.
- **[Answer]**:

### D. 신뢰성 (Reliability)

**Q14 — 의존성 격리 수치(타임아웃·재시도·백오프).** FD 정책(BR-16/18)의 수치 확정 (RES-9).
- A) **제안값 확정**: 외부 호출 타임아웃 ~10s, 재시도 최대 5회, 지수 백오프(기본 1s·배수 2·지터), 서킷 개방 임계 정의. (권장; 조정 가능)
- B) 다른 값(직접 기술 — E).
- C) Infra Design까지 추가 보류.
- **권장**: A. **근거**: 이 엔벨로프 × 단일 워커(Q11=A) × arXiv 최소 간격(Q2/RES-8)이 시드 빌드 예산(Q10=A "수십 분")에 수렴하고 쿼터 미위반해야 함. Infra에서 실측 재조정 가능.
- **[Answer]**:

**Q15 — 철회 신호 탐지 타당성 (FD Q13=B / BR-14, Q2=A 초록 전용 제약).** 전문 미취득 + 선택 arXiv 접근(Q2)에서 탐지 가능한 철회 신호는?
- A) **arXiv 메타데이터/comment 철회 표시**(예 comment에 "withdrawn") — 메타 기반 탐지로 tombstone 활성 유지. (권장 if 신뢰 가능)
- B) **초록 텍스트 withdrawal 공지 패턴 매칭**(메타에 없을 시 폴백).
- C) **신뢰 가능 신호 부재 → 데모 tombstone을 best-effort로 강등**(BR-14 무조건 약속 회피, 인터페이스 보존).
- **권장**: A(가능 시) 또는 A+B. 메타/초록 어느 쪽도 신뢰 못 하면 C로 정직하게 강등(FD Q13=B를 데모 best-effort로 한정). Q2 답과 연동.
- **[Answer]**:

### E. 비용 (Cost) — NFR-C1

**Q16 — 임베딩 비용 접근 + 텔레메트리 계측.**
- A) **Q3 따라**: A(로컬)면 임베딩 비용 ~0(데모); 텔레메트리는 호출수/토큰/배치 카운트로 계측(프로덕션 Titan 비용 모델 대비 환산). 디덥(BR-4)으로 재임베딩 0. (권장)
- B) 별도 비용 모델(직접 기술).
- **권장**: A — NFR-C1 $300/월은 프로덕션(Titan) 가드레일; 데모 로컬은 비용 동인 제거.
- **[Answer]**:

### F. 보안 · 유지보수성

**Q17 — 인제스천 데이터 at-rest/전송 (SEC-1).**
- A) **스토어 기본 at-rest 암호화 + TLS**(로컬은 컨테이너 내; 프로덕션 RDS 암호화/TLS). (권장)
- B) 데모 비암호화, 프로덕션만.
- **권장**: A — SEC-1 준수.
- **[Answer]**:

**Q18 — 모노레포 빌드/의존성 + 공급망(SEC-10) (UQ2=A).**
- A) **모노레포 `ingestion/`** + 언어 표준 도구(Python: uv/poetry) + **락파일 + 의존성 취약점 스캔(SCA) + SBOM 생성**(SEC-10; 이미지 핀은 Q9). (권장; Q1 종속)
- B) 다른 도구(직접 기술).
- **권장**: A — UQ2=A·SEC-10 산출물("무엇을 핀/산출"은 본 단계; 스캔 **CI 실행**은 NFR Design 보류).
- **[Answer]**:

---

## 5. 다음 절차

1. 팀이 `§4` `[Answer]:` 채움(또는 채팅; "approve recommendations"로 일괄 권장 수락 가능). `[전역]`(Q1·Q3·Q4)은 시스템 전역 영향 인지 후 결정.
2. 모호 답변 시 후속 명확화.
3. 답변 확정 → `§2` 산출물 생성(nfr-requirements.md / tech-stack-decisions.md + VectorSpec 확정 + AS-4 수치).
4. 완료 메시지 + 리뷰 게이트 → 승인 시 다음 단계(**NFR Design** — NFR 패턴·논리 컴포넌트·보류 RES-4/RES-12).

> 본 계획·질문은 **리뷰 게이트**입니다. 답변 전까지 산출물 미생성, 미커밋.
