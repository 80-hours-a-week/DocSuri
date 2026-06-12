# U4 Trace 코드 리뷰

> **대상**: PR #22 — U4 데이터 레이어(TRACE-01a) + HTTP 표면 + UI(TRACE-01b·02) + U0 리뷰 후속 패치 (+1,565/−33, 31파일)
> **리뷰어**: Claude (작성) — 팀 리뷰어는 본 문서에 코멘트/체크 추가
> **일자**: 2026-06-11
> **기준**: [component-model §6](../design-artifacts/component-model.md) 계약 정합 · [U4 §8](../design-artifacts/units/unit-u4-trace.md) 변경 정책 · U1 기존 패턴(BFF·mock 폴백·동결 DTO 미러) 준수 · NFR 추적 · demo-scope 머지 기준
> **판정**: ✅ **승인** — Medium 2건 중 **U4-M1은 본 PR에서 수정 완료**, U4-M2는 U0-M2 후속 연계. Low 5건은 후속 배치.

---

## 1. 검증 요약

| 항목 | 결과 |
|---|---|
| pytest (U0+U1+U2+U4) | 60/60 통과 |
| `npm run lint` / `npm run build` | 0 errors (Next 16 React Compiler 규칙 포함) |
| 브라우저 E2E (프로덕션 빌드 + 실백엔드 프록시, 수동) | 검색 → 그래프(노드 9·방향 엣지 8) → 노드 클릭 → 사이드 패널 PaperCard → 학부 Top-3(인용수 내림차순) → 375px 리스트 분기 → 즉시 필터 ✅ |
| U4 §6 빌드 가능 정의 | 4/4 (체크 갱신 완료) |
| 계약 정합 (아래 §3) | `CitationView` 필드 추가/변경 0건 |

## 2. 발견 사항 (Findings)

### Medium

| ID | 위치 | 내용 | 상태 |
|---|---|---|---|
| U4-M1 | `frontend/components/citation-flow.tsx` | **경쟁 상태 가드 부재** — U1 `search-experience.tsx`의 `reqId` 전례와 달리 최신 응답 가드가 없어, 논문 A→닫기→논문 B 빠른 전환이나 학부 토글 연타 시 늦게 도착한 이전 응답이 화면을 덮어쓸 수 있음 | ✅ **본 PR에서 수정** — `reqId` ref로 최신 요청만 반영 + `handleClose`에서 진행 중 요청 무효화 |
| U4-M2 | `citation-flow.tsx` 빈 상태 문구 | "인용 정보를 가져오지 못했습니다"가 ① R4 폴백(조회 실패)과 ② 정말 인용 0건인 논문을 구분 못 함. 근본 원인은 [U0 리뷰 M2](u0-code-review.md)에서 지적한 `OneHopResult`의 degraded 플래그 부재 | ⏭ U0 후속(플래그 추가) 시 문구 분기 — 환경 구축 라운드와 병합 |

### Low — 후속 배치

| ID | 위치 | 내용 |
|---|---|---|
| U4-L1 | `u4/service.py` `_cache_key` | 일 단위 윈도우가 UTC 자정에 키를 회전 — 자정 직전 캐시 항목의 실효 수명이 짧아짐(TTL 24h와 별개). U4 §5 설계 의도이나 트레이드오프 주석 권장 |
| U4-L2 | `u4/service.py` + `u0/adapters/aws.py` | 이중 캐시(U4 뷰 24h + U0 SS 원시 24h) — 계약상 양쪽 책임이 맞으나 DynamoDB 쓰기 2배. 환경 구축 비용 실측 시 확인 |
| U4-L3 | `app/api/citations/route.ts` | viewport 검증 실패 기본값 1280(그래프) — 보수적 기본(list)으로 바꿀지 검토 |
| U4-L4 | `citation-flow.tsx` `undergrad` 토글 | TRACE-02 시연용 로컬 persona — **U2 전역 페르소나 도입 시 통합 필요** (U2 라운드 체크리스트 등재) |
| U4-L5 | 프론트 전반 | 자동화 테스트 0건(U1 스캐폴드부터 러너 부재 — 팀 공통 부채). E2E는 수동 playwright. U3 합류 전 smoke 테스트 도입 검토 |

### 보안·성능

- 클라이언트 제공 center 메타: React 이스케이프로 XSS 안전, ID 길이 64 제한, BFF 단일 진입(CORS 불필요), 비밀 값 없음 ✅
- 그래프 ≤30 노드 절단(인용수 가중), fixture 조회 수십 ms — [NFR-PERF-03](../requirements/nfr.md#nfr-perf-03)·[NFR-MOBILE-03](../requirements/nfr.md#nfr-mobile-03) 예산 대비 충분. 실호출 측정은 환경 구축 라운드

## 3. 계약·패턴 정합 검사

| 검사 | 결과 |
|---|---|
| `CitationView` ↔ [component-model §6.6](../design-artifacts/component-model.md) | 5필드 1:1, 변경 0 ✅ |
| `top_influence` 엔벨로프 배치 | U1 `query_mapping` 전례 준수 — 동결 DTO 오염 없음 ✅ |
| 렌더 분기 단일화 | 백엔드 `FormFactorRouter`만 결정, UI는 `view.render` 소비 (NFR-MOBILE-05 강제 1곳) ✅ |
| BFF 폴백 정책 | U1 search-service와 동일("도달 불가만 mock, 오류는 표면화") ✅ |
| U1 파일 수정 범위 | `paper-card`(footer prop·difficulty 옵셔널)·`result-list`(패스스루)·`mock-data`(풀 export) — 전부 추가적·기본 동작 불변. **U1 팀 확인 요청 중** |
| U4 §8 금지(다단계 트리) | `oneHop` 단일 호출만 ✅ |

## 4. 의도적 설계 선택 (리뷰어 참고)

1. **중심 논문 메타는 호출자가 전달** — U4 입력 계약(`SearchResult.papers[i].id`)의 HTTP 구현. 백엔드에 논문 조회 API를 만들지 않아 unit 경계 유지.
2. **렌더 분기 서버 결정** — viewport는 클라이언트가 보내되 규칙은 서버 한 곳.
3. **학부 토글은 Drawer 내부 로컬** — 전역 페르소나는 U2 소유 (침범 회피, U4-L4로 통합 예약).
4. **Next 16 React Compiler 대응** — effect 내 동기 setState 금지 규칙에 맞춰 파생 `loading` + promise 콜백 setState 패턴 채택.
5. **E2E는 프로덕션 빌드로 수행** — 이 환경에서 dev 서버 HMR WebSocket이 차단되어 주기적 전체 리로드가 발생하기 때문.

## 5. 후속 항목 배치

| 항목 | 배치 |
|---|---|
| U4-M2 (degraded 플래그 + 문구 분기) · U4-L1·L2 | 환경 구축 라운드 (U0-M1·M3·L5와 병합) |
| U4-L4 (persona 통합) | U2 전역 페르소나 라운드 |
| U4-L3 · U4-L5 (smoke 테스트) | 팀 합의 후 다음 frontend 커밋 |

---

*팀 리뷰어 추가 코멘트는 아래에:*

- [ ] (팀 코멘트 자리)
