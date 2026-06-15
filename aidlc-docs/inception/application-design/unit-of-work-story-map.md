# unit-of-work-story-map.md — 스토리 → 유닛 매핑

**단계**: INCEPTION → Units Generation · **일자**: 2026-06-15
**근거**: `stories.md`(21개), `unit-of-work.md`(U1~U6). 각 스토리에 **주 소유 유닛(Owner)** + 기여 유닛.

---

## 매핑 (21개 전수)

| 스토리 | Owner | 기여 유닛 |
|---|---|---|
| **US-H1** 히어로(가입→질의→근거화 결과) | U5 | U2(백킹 검색), U3(가입), U1(인덱스) |
| **US-D1** 자연어 질의 입력 | U2 | U5(검색 화면) |
| **US-D2** 시맨틱 검색 | U2 | U1(공유 인덱스) |
| **US-D3** 상위 N 랭킹 | U2 | — |
| **US-D4** 폰 결과 카드 | U2(조립) | U5(카드) |
| **US-D5** 엄격 근거화 | U6(근거화 후크) | U2(어댑터), U1(추적 메타) |
| **US-D6** 기권 | U2(어댑터) | U6(후크) |
| **US-D7** 빈/실패/저하 UX | U5(StateView) | U2 |
| **US-A1** 공개 가입 | U3 | U5(계정 화면), U6(레이트리밋) |
| **US-A2** 로그인/세션 | U3 | U5, U6(게이트웨이) |
| **US-L1** 검색 저장 | U4 | U5 |
| **US-L2** 라이브러리 | U4 | U5 |
| **US-L3** 검색 이력 | U4 | U2(SearchExecuted 생산) |
| **US-I1** 인제스천·인덱싱(시드) | U1 | — |
| **US-I2** 스케줄 갱신 | U1 | U6(갱신 실패 경보) |
| **US-I3** 복원력 인제스천 | U1 | U6(관측) |
| **US-R1** 근거화 보장+할루시네이션 탐지 | U6 | U2 |
| **US-R2** 우아한 저하+반쪽짜리 탐지 | U6 | U2(저하 폴백) |
| **US-R3** 비용 상한+비용 폭발 탐지 | U6 | — |
| **US-R4** 관측성+AI 인시던트 경보 | U6 | (전 유닛 신호원) |
| **US-R5** 헬스 체크 | U6 | — |

## 유닛별 스토리 묶음
- **U1 Ingestion** — US-I1, US-I2, US-I3 (+US-H1/US-D2 인덱스 백킹)
- **U2 Discovery** — US-D1, US-D2, US-D3, US-D4, US-D6 (+US-D5/US-D7/US-R1/R2 기여, US-H1 백킹, US-L3 생산자)
- **U3 Accounts** — US-A1, US-A2 (+US-H1 가입)
- **U4 Library** — US-L1, US-L2, US-L3
- **U5 Frontend** — US-H1(주), US-D7(주) (+US-D1/D4/A1/A2/L1/L2/L3 UI 기여)
- **U6 Reliability/Ops** — US-D5(주), US-R1, US-R2, US-R3, US-R4, US-R5 (+US-A1 레이트리밋, US-I2/I3 관측)

## 전수 할당 검증
- 스토리 21개 = US-H1 + US-D1..D7(7) + US-A1..A2(2) + US-L1..L3(3) + US-I1..I3(3) + US-R1..R5(5) → **전부 Owner 배정 완료(미할당 0)**.
- 횡단 스토리(US-D5 근거화)는 Owner=U6(단일 권위 후크), 기여=U2(어댑터) — Application Design 단일-소유자 규칙과 일치.
- US-H1(히어로)은 통합 슬라이스 — Owner=U5(프런트 표면), 다수 유닛 백킹(US-D*/US-A1으로 실현).
