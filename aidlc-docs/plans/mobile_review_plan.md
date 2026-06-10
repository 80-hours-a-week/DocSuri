# 작업 계획서 — 모바일 검토 반영 (Mobile Review Apply)

- **단계**: AI-DLC › Inception › User Stories › 부속 검토 반영
- **사유**: [Prompt 10](../prompts.md#prompt-10) 모바일 검토에서 발견된 3개 층위(페르소나·NFR·스토리 본문)의 누락 일괄 보완
- **승인**: [Prompt 11](../prompts.md#prompt-11) (2026-06-10) — 옵션 1 채택, 5개 결정 권장값 채택
- **산출물 영향**: `personas.md`, `nfr.md`, `user_stories.md`, `coverage_matrix.md`, `epics.md`

---

## 결정 표 (적용 값)

| 항목 | 적용값 |
|---|---|
| 반응형 브레이크포인트 | **360 / 768 / 1280** (모바일 / 태블릿 / 데스크톱) |
| 모바일(4G) 검색 응답 목표 | **P95 < 5초** |
| 모바일 결과 카드 우선 메타 | **제목 · 연도 · 유사도** (그 외는 펼침) |
| US-TRACE-01 모바일 거동 | **간소화 리스트 + 노드 검색** (그래프 미표시) |
| 오프라인 거동 | **읽기 전용 캐시 24h** |

---

## 실행 단계

- [x] **A1** `personas.md` — P1·P2 각각에 *모바일 사용 시나리오* 한 단락 추가.
- [x] **A2** `nfr.md` — `NFR-MOBILE-01~04` 섹션 신설(브레이크포인트·터치 타깃·모바일 응답·1탭 도달).
- [x] **A3** `nfr.md` — `NFR-NET-01~04` 섹션 신설(데이터 절약·재시도·오프라인 안내·24h 캐시).
- [x] **A4** `nfr.md` NFR-UX-03 재정의 — 데스크톱 vs 모바일 분기.
- [x] **A5** `nfr.md` NFR-A11Y-02 보강 + NFR-A11Y-03 신설(터치 친화).
- [x] **A6** `user_stories.md` — US-COMP-02·04·05 인터랙션 동사 일반화.
- [x] **A7** `user_stories.md` US-TRACE-01 — 모바일 분기 AC 추가.
- [x] **A8** `coverage_matrix.md` — 디바이스×페르소나, 디바이스×Epic 매트릭스 + 변경 스토리 INVEST 재검증.

---

## 후속

- [x] `epics.md`에 모바일 정책 한 줄 추가 (Epic별 반응형 분기는 NFR-MOBILE-* 키로 위임한다).
- [x] 이번 변경의 결과를 `prompts.md` [Prompt 11](../prompts.md#prompt-11)에 마무리 줄로 기록.
- [x] 7단계(사용자 리뷰 게이트) 재실행 — 반영 결과 확인 후 8단계(인계 노트) 진행 여부 결정. → [Prompt 12](../prompts.md#prompt-12) "옵션 1로 진행해줘"로 통과. `handoff.md` 작성 완료.
