# U5 Frontend — NFR Requirements (NFR Requirements)

**단계**: CONSTRUCTION → NFR Requirements · **유닛**: U5 Frontend (Track 3) · **일자**: 2026-06-16
**스코프**: 히어로 슬라이스(가입→로그인→검색→근거화 결과 + 상태 UX). 라이브러리/이력 = 계약만(후속 패스).
**근거**: U5 FD 4종 · components.md §U5 · 전역 NFR(NFR-U1/U2/P1/R1/C1) · SEC/RES 베이스라인.
**시스템 전역 계승**: NFR-C1 $1600/월(시스템 전역) — **U5는 LLM 직접 호출 없음 → 비용 기여 0**. 모든 백엔드 호출은 U6 게이트웨이 단일 진입.

> 표기: `NFR-U5-n`. 정량 수치 미확정 항목은 측정 단계 확정으로 표시.

---

## 1. 성능 (Performance)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-P1 | 폰 우선 초기 로드 | 초기 JS 번들 경량(코드 스플릿)·LCP 합리적 수준 유지. **정량 SLO는 측정 단계 확정**(조기 과최적화 회피) | NFR-U1 |
| NFR-U5-P2 | 검색 응답 처리 | 단일 요청/응답 계약, 로딩 표시 즉시·중복 제출 차단(디듀프) | NFR-P1 |
| NFR-U5-P3 | SSR 초기 렌더 | 서버 렌더로 첫 콘텐츠 제공, 하이드레이션 후 인터랙션 | NFR-U1 |
| NFR-U5-P4 | 목업 프레임 | 데스크톱 목업 전환 시 리플로우 0(내부폭 고정) | NFR-U2 |

## 2. 가용성·복원력 (Availability / Resiliency)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-R1 | 전역 에러 바운더리 | fail-closed 일반화 에러, 스택/내부정보 차단 | NFR-R1, SEC-15, BR-U5-11 |
| NFR-U5-R2 | 백엔드 장애 피드백 | 401/403/429/5xx·네트워크 실패를 UserFacingError로 정규화, 명확한 안내 + 재시도 경로(무한 로딩 금지) | RES-9, BR-U5-10/16 |
| NFR-U5-R3 | 저하 응답 | DegradedResultDTO 시 상단 비기술 배너 + 부분 결과 렌더 | US-R2, QT-3, BR-U5-12 |
| NFR-U5-R4 | SSR 서버 가용성 | 렌더 서버 장애 시 거동(폴백 페이지)·헬스는 Infra 단계 | NFR-R1 |

## 3. 보안 (Security)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-S1 | 토큰 비노출 | 세션=httpOnly 쿠키. SSR 서버측 쿠키 포워딩, 클라 JS·번들 토큰 미접근 | SEC-3, SEC-12, BR-U5-13/14 |
| NFR-U5-S2 | XSS 방어 | 외부 데이터(제목·초록 등) 텍스트 이스케이프 렌더, 원시 HTML 주입 금지 | SEC-5, BR-U5-6 |
| NFR-U5-S3 | 안전 링크 | `arxivUrl` http/https 스킴 검증 + rel=noopener noreferrer | BR-U5-7 |
| NFR-U5-S4 | 노출 필드 한정 | ResultCard 7필드만, 내부 점수·owner id·debug meta·degradationMode 원문 비노출 | SEC-9, BR-U5-4/5/8 |
| NFR-U5-S5 | 프레임 보호 | frame-ancestors=self 부합 마크업/헤더(목업은 self 내부) | SEC-4 |
| NFR-U5-S6 | 클라 시크릿 0 | 번들·로그·URL에 시크릿/토큰 없음. 게이트웨이 baseURL만 환경 구성 | SEC-12 |
| NFR-U5-S7 | 보호 라우트 | SessionContext 가드(클라 편의) + 백엔드 401/403 권위 | SEC-8, BR-U5-15 |

## 4. 사용성·접근성 (Usability / Accessibility)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-U1 | 폰 우선 | 폰 뷰포트 1급, 터치 타깃·세이프 에어리어 고려 | NFR-U1 |
| NFR-U5-U2 | 접근성 | WCAG 2.1 AA 지향(시맨틱 마크업·키보드·스크린리더·대비) | BR-U5-21 |
| NFR-U5-U3 | UI 언어 | 한국어 단일(i18n 프레임워크 미도입), 논문 콘텐츠 원문 렌더. cross-lingual 질의(한국어→영문 결과) UX 일관 | TD-3 |
| NFR-U5-U4 | 상태 UX | 로딩/빈/기권/저하/에러 비기술 안내(기권≠빈결과 구분) | FR-11, BR-U5-9 |

## 5. 관측 가능성 (Observability)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-O1 | 핵심 경로 계측 | 검색·로그인 경로 에러율·지연을 경량 훅으로 측정·노출 | Part 2-A |
| NFR-U5-O2 | 외부 APM | Sentry 등 연동은 Infra/후속(현 슬라이스 제외) | — |

## 6. 유지보수 (Maintainability)
| ID | 요구 | 목표 | 추적 |
|---|---|---|---|
| NFR-U5-M1 | 단일 책임 컴포넌트 | FD 9컴포넌트 경계 준수, 사유 없는 새 컴포넌트/훅 금지 | Part 1 |
| NFR-U5-M2 | 계약 단일 출처 | DTO 타입은 shared/dtos 생성물(드리프트 0) | BR-U5-19 |
| NFR-U5-M3 | 독립 배포 | `frontend/` 배포 ④ 독립, 트랙 경계(shared/·backend/ 미편집) 준수 | unit-of-work ④ |
| NFR-U5-M4 | 테스트 게이트 | 컴포넌트·E2E·DTO 계약 테스트 + lint(ESLint/Prettier) CI | TD-U5-5/7 |

## 7. 스코프 제외 (명시)
- **오프라인/PWA**: 제외 확정(FD 합의). SSR 동기 REST 범위.
- **SEO**: 인증 기반 앱 — 공개 표면(히어로 랜딩)만 해당, 우선순위 낮음.
- **레이트리밋 권위**: US-A1 레이트리밋은 U6 권위. U5는 429를 UserFacingError로 안내만.
- **정량 성능 SLO·호스팅 토폴로지·헬스체크**: NFR Design/Infrastructure Design 단계.

## 8. 비용 (Cost)
- NFR-C1 시스템 전역 $1600/월에 **U5 직접 기여 0**(LLM·임베딩 직접 호출 없음). 호스팅/CDN 비용은 Infra 단계 산정.
