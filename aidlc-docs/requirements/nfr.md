# DocSuri MVP — 비기능 요구사항 (NFR)

- **결정 근거**: [`aidlc-docs/plans/user_stories_plan.md`](../plans/user_stories_plan.md) 부록 A · 결정 2.E
- **참조 방식**: 사용자 스토리는 본 파일의 NFR 키([`NFR-PERF-01`](#nfr-perf-01) 등)를 *Definition of Done* 줄에서 인용한다.

---

## NFR-PERF — 성능

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-perf-01"></a>NFR-PERF-01 | 검색 응답 시간 | P50 < 3초, P95 < 6초 (상위 20건 반환 기준) |
| <a id="nfr-perf-02"></a>NFR-PERF-02 | 단건 요약 응답 시간 | P95 < 20초 (논문 1편, 5~10 KB 텍스트 입력) |
| <a id="nfr-perf-03"></a>NFR-PERF-03 | 인용 1-hop 그래프 | P95 < 5초 |

## NFR-UX — 사용자 경험·가독성

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-ux-01"></a>NFR-UX-01 | 학부 모드 가독성 | 한국어 능력시험 4급 수준 어휘 · 평균 문장 길이 ≤ 22자 어절 |
| <a id="nfr-ux-02"></a>NFR-UX-02 | 전문 모드 어휘 | 학술 전문 어휘 보존 · 한국어 표현 우선 |
| <a id="nfr-ux-03"></a>NFR-UX-03 | 결과 카드 정보 밀도 | 제목·저자·연도·인용수·유사도·난이도 6개 메타가 1뷰에 보여야 함 |
| <a id="nfr-ux-04"></a>NFR-UX-04 | 빈 상태 가이드 | 모든 빈 상태에 다음 행동 1개 이상 제안 |

## NFR-LANG — 언어·번역

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-lang-01"></a>NFR-LANG-01 | 기본 출력 언어 | 한국어 |
| <a id="nfr-lang-02"></a>NFR-LANG-02 | 영문 자연어 입력 허용 | 박지훈 페르소나 입력 지원 |
| <a id="nfr-lang-03"></a>NFR-LANG-03 | 번역 충실도 | 학술 용어 사전(MVP는 수기 50개) 일관 적용 |

## NFR-DATA — 데이터·출처

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-data-01"></a>NFR-DATA-01 | 코퍼스 출처 | arXiv 공개 메타데이터 + Semantic Scholar 그래프 (MVP 한정) |
| <a id="nfr-data-02"></a>NFR-DATA-02 | 출처 표시 | 모든 요약·차별성 노트에 원문 링크 및 인용 메타 노출 |
| <a id="nfr-data-03"></a>NFR-DATA-03 | 캐시 TTL | 검색 결과 캐시 24시간, 요약 결과 캐시 7일 |

## NFR-SEC — 보안·프라이버시

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-sec-01"></a>NFR-SEC-01 | 인증 | MVP는 비로그인. 익명 세션만. |
| <a id="nfr-sec-02"></a>NFR-SEC-02 | 업로드 PDF 처리 | 임시 저장 후 24시간 내 삭제, 영구 보관 금지 |
| <a id="nfr-sec-03"></a>NFR-SEC-03 | 외부 호출 키 관리 | 환경 변수 + `.env.example` 동기화 (저장소에 평문 금지) |

## NFR-COST — 비용

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-cost-01"></a>NFR-COST-01 | 데모 LLM 비용 상한 | 월 USD 50 (MVP 데모 트래픽 기준) |
| <a id="nfr-cost-02"></a>NFR-COST-02 | 토큰 최적화 | 요약 입력에 청크 단위 압축 적용 |

## NFR-A11Y — 접근성

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-a11y-01"></a>NFR-A11Y-01 | 기본 준수 | WCAG 2.1 AA |
| <a id="nfr-a11y-02"></a>NFR-A11Y-02 | 키보드 내비게이션 | 주요 동작 100% 키보드 가능 |

## NFR-OBS — 관찰가능성

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-obs-01"></a>NFR-OBS-01 | 요청 로깅 | 검색·요약 요청마다 latency, 토큰, 캐시 적중 여부 기록 |
| <a id="nfr-obs-02"></a>NFR-OBS-02 | LLM 호출 추적 | 입력 토큰·출력 토큰·모델명·비용 누적치 노출 |

---

## 페르소나별 NFR 매핑 요약

| 페르소나 | 핵심 NFR |
|---|---|
| [P1](../story-artifacts/personas.md#p1) 박지훈 (전문) | [NFR-UX-02](#nfr-ux-02), [NFR-LANG-02](#nfr-lang-02), [NFR-DATA-02](#nfr-data-02), [NFR-PERF-01](#nfr-perf-01)·[02](#nfr-perf-02) |
| [P2](../story-artifacts/personas.md#p2) 김민서 (학부) | [NFR-UX-01](#nfr-ux-01), [NFR-LANG-01](#nfr-lang-01)·[03](#nfr-lang-03), [NFR-A11Y-01](#nfr-a11y-01) |
