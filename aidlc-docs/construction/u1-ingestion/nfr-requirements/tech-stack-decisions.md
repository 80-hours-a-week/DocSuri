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

## 멀티모달 자산 추출 ADR (FR-17 — 표시 전용, 2026-06-22 확장)

> 상속: TD-1 Python·TD-7 S3·TD-8 Hypothesis·TD-9 컨테이너·TD-10 패키징. TD-3/4(임베딩·OpenSearch)는 **무관**(자산 검색 비대상). NFR 계획 Q1~Q7=A.

## TD-11 — PDF 페이지 크롭(page-crop) 도구: **permissive 스택 휴리스틱** (Q1=A)
> **정정 (2026-06-22, Code Generation Q1=A)**: 초안의 **PyMuPDF(fitz)는 AGPL-3.0**라 "프로덕션·공개 모바일 웹"에 전파 위험 → **permissive 스택으로 대체**: **`pypdfium2`(Apache-2.0/BSD-3, PDF 렌더) + `pdfplumber`/`pdfminer.six`(MIT, 텍스트·rect·캡션 레이아웃)**. 알고리즘(내장 이미지 객체 + 캡션 근접 매칭 + page-crop)은 동일.
- **근거**: 내장 이미지 객체 + 캡션("Figure N"/"Table N") 근접 영역 크롭을 **CPU·ML 없이** 수행. permissive 라이선스, 오프라인 배치·$1600 전역 상한에 적합. distinct 논문×버전 1회(BR-22)라 처리량 bounded.
- **대안**: ~~PyMuPDF(AGPL — 기각)~~; 레이아웃 분석 ML 모델(pdffigures2[Java]/deepfigures[GPU]) — 검출 정밀도 우수하나 컴퓨트·운영 복잡도↑.
- **전환 비용**: 낮음 — 추출은 `AssetExtractor` 뒤 추상화. 정밀도 부족 시 차기 사이클 ML 검출로 교체(재추출은 NEW/CHANGED 재처리로 흡수).

## TD-12 — LaTeX 구조화(structured) 추출: **arXiv e-print tarball 그래픽 직접 추출 + 표는 PDF 크롭** (Q2=A)
- **근거**: e-print(`/e-print/{id}`) tarball에서 `\includegraphics` 참조 그래픽 파일(PDF/PNG/JPG/EPS)을 직접 취득 → 그림 **원본 화질**. **표(LaTeX `table`/`tabular`)는 이미지가 아니므로 항상 PDF 영역 크롭(TD-11)** — 별도 LaTeX 컴파일 파이프라인 회피. EPS/PDF 그래픽은 TD-13 정규화로 래스터화.
- **대안**: 표도 LaTeX→이미지 렌더(TeX 컴파일 파이프라인) — 복잡·비용 과다.
- **전환 비용**: 낮음. e-print 미제공/추출 실패 → TD-11 page-crop 폴백(BR-23 혼합).

## TD-13 — 이미지 포맷·정규화: **WebP 재인코딩 + 치수/픽셀 상한 + 메타데이터 스트립** (Q3=A)
- **근거**: 모든 자산을 안전 디코더로 **재인코딩(WebP)** — 모바일 대역폭 절감 + 원본 바이트 비서빙(보안 TD-15). 최대 치수·총 픽셀 상한(decompression-bomb 가드), EXIF/메타 스트립. 구체 수치(해상도·DPI·상한·품질)는 NFR Design.
- **대안**: 원본 포맷 보존(재인코딩 없음) — 보안·대역폭 불리.
- **전환 비용**: 낮음(인코딩 파라미터).

## TD-14 — 자산 저장: **S3 별도 prefix/버킷(private·SSE) + 매니페스트/메타 = 공유 RDS PostgreSQL** (Q5=A)
- **근거**: 바이너리는 기존 S3(TD-7) 자산 prefix(공개 차단 SEC-9·at-rest SEC-1), 매니페스트/자산 메타는 **공유 RDS PostgreSQL**(U3/U4 계정·라이브러리, U7 용어집 자산) — 읽기 측(U7)이 RDS 조회 후 서명 URL 발급(인셉션 Q3=A). **신규 스토어 0.**
- **대안**: 매니페스트도 S3(JSON) — RDS 미사용. U7 조회·갱신 일관성에 불리.
- **전환 비용**: 낮음(포트 `AssetStorePort` 뒤). RDS 스키마·마이그레이션은 Infra Design.

## TD-15 — 이미지 보안 재인코딩(외부 소스 파싱 방어): **안전 디코더 경유 강제** (Q3=A 보안 측)
- **근거**: 외부 소스(arXiv 그래픽/PDF) 이미지는 **파싱 공격 표면**. 신뢰 디코더(예: Pillow/안전 옵션)로 재디코드·재인코딩, 치수/픽셀 상한으로 decompression bomb 차단, 메타 스트립. **원본 바이트를 그대로 저장·서빙하지 않는다.** 외부 fetch는 기존 fail-closed(BR-18)·타임아웃(RES-9) 상속(SSRF/지연 방어).
- **대안**: 원본 패스스루 — 위험(거부).
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
