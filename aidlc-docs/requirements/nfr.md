# DocSuri MVP — 비기능 요구사항 (NFR)

- **결정 근거**: [`aidlc-docs/plans/user_stories_plan.md`](../plans/user_stories_plan.md) 부록 A · 결정 2.E
- **참조 방식**: 사용자 스토리는 본 파일의 NFR 키([`NFR-PERF-01`](#nfr-perf-01) 등)를 *Definition of Done* 줄에서 인용한다.

---

## NFR-PERF — 성능

> 모든 성능 목표는 **데스크톱·와이파이** 기준이다. 모바일(4G) 목표는 [NFR-MOBILE-03](#nfr-mobile-03) 참조.

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-perf-01"></a>NFR-PERF-01 | 검색 응답 시간 (데스크톱·WiFi) | P50 < 3초, P95 < 6초 (상위 20건 반환 기준) |
| <a id="nfr-perf-02"></a>NFR-PERF-02 | 단건 요약 응답 시간 (데스크톱·WiFi) | P95 < 20초 (논문 1편, 5~10 KB 텍스트 입력) |
| <a id="nfr-perf-03"></a>NFR-PERF-03 | 인용 1-hop 그래프 (데스크톱·WiFi) | P95 < 5초 |

## NFR-UX — 사용자 경험·가독성

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-ux-01"></a>NFR-UX-01 | 학부 모드 가독성 | 한국어 능력시험 4급 수준 어휘 · 평균 문장 길이 ≤ 22자 어절 |
| <a id="nfr-ux-02"></a>NFR-UX-02 | 전문 모드 어휘 | 학술 전문 어휘 보존 · 한국어 표현 우선 |
| <a id="nfr-ux-03"></a>NFR-UX-03 | 결과 카드 정보 밀도 (디바이스 분기) | **데스크톱(≥768px)**: 제목·저자·연도·인용수·유사도·난이도 6개 메타가 1뷰. **모바일(<768px)**: 제목·연도·유사도 3개 메타가 우선 노출, 나머지 3개는 "더 보기" 펼침 |
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
| <a id="nfr-a11y-02"></a>NFR-A11Y-02 | 키보드 내비게이션 | 주요 동작 100% 키보드 가능 (포커스 링 시각화 포함) |
| <a id="nfr-a11y-03"></a>NFR-A11Y-03 | 터치 친화 | 터치 타깃 ≥ 44×44 CSS px · 모든 호버 기반 인터랙션에 탭 대안 제공 · 스와이프 제스처는 명시적 버튼 대안 병기 |

## NFR-MOBILE — 모바일·반응형

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-mobile-01"></a>NFR-MOBILE-01 | 반응형 브레이크포인트 | **360 / 768 / 1280 px** (모바일 / 태블릿 / 데스크톱). 모든 핵심 화면이 360px 폭에서 가로 스크롤 없이 동작 |
| <a id="nfr-mobile-02"></a>NFR-MOBILE-02 | 터치 타깃 | 최소 44×44 CSS px (NFR-A11Y-03와 정합) |
| <a id="nfr-mobile-03"></a>NFR-MOBILE-03 | 모바일(4G) 응답 시간 | 검색 P95 < **5초**, 요약 P95 < **25초**, 인용 1-hop P95 < **7초** |
| <a id="nfr-mobile-04"></a>NFR-MOBILE-04 | 모바일 핵심 동작 도달성 | 검색·요약 모드 토글·필터·번역 호출이 각각 **최대 2탭 이내**로 도달 |
| <a id="nfr-mobile-05"></a>NFR-MOBILE-05 | 인용 그래프 모바일 거동 | <768px에서는 그래프 렌더링 대신 **간소화 리스트 + 노드 검색** 사용 (US-TRACE-01 AC와 정합) |

## NFR-NET — 네트워크·오프라인

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-net-01"></a>NFR-NET-01 | 데이터 절약 | 이미지·그래프 시각자료 lazy load, 셀룰러 감지 시 자동 저해상도 모드 |
| <a id="nfr-net-02"></a>NFR-NET-02 | 네트워크 변동 시 재시도 | 지수 백오프(1·2·4초) 최대 3회, 4회차에 사용자에게 알림 |
| <a id="nfr-net-03"></a>NFR-NET-03 | 오프라인 빈 상태 | 오프라인 감지 시 다음 행동 1개 이상 제안 (NFR-UX-04 강화) |
| <a id="nfr-net-04"></a>NFR-NET-04 | 읽기 전용 캐시 | 최근 검색·요약 결과는 **24h 동안 오프라인에서 읽기 전용**으로 노출 가능. 쓰기·재검색은 차단 |

## NFR-OBS — 관찰가능성

| 키 | 항목 | 목표값 |
|---|---|---|
| <a id="nfr-obs-01"></a>NFR-OBS-01 | 요청 로깅 | 검색·요약 요청마다 latency, 토큰, 캐시 적중 여부 기록 |
| <a id="nfr-obs-02"></a>NFR-OBS-02 | LLM 호출 추적 | 입력 토큰·출력 토큰·모델명·비용 누적치 노출 |

---

## 페르소나별 NFR 매핑 요약

| 페르소나 | 핵심 NFR |
|---|---|
| [P1](../story-artifacts/personas.md#p1) 박지훈 (전문) | [NFR-UX-02](#nfr-ux-02), [NFR-LANG-02](#nfr-lang-02), [NFR-DATA-02](#nfr-data-02), [NFR-PERF-01](#nfr-perf-01)·[02](#nfr-perf-02), [NFR-MOBILE-03](#nfr-mobile-03)·[05](#nfr-mobile-05) (모바일 트리아지) |
| [P2](../story-artifacts/personas.md#p2) 김민서 (학부) | [NFR-UX-01](#nfr-ux-01)·[03](#nfr-ux-03), [NFR-LANG-01](#nfr-lang-01)·[03](#nfr-lang-03), [NFR-A11Y-01](#nfr-a11y-01)·[03](#nfr-a11y-03), [NFR-MOBILE-01](#nfr-mobile-01)·[02](#nfr-mobile-02)·[04](#nfr-mobile-04), [NFR-NET-01](#nfr-net-01)·[04](#nfr-net-04) |
