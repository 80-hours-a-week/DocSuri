# DocSuri Frontend — U1 Discover

[`unit-u1-discover.md`](../aidlc-docs/design-artifacts/units/unit-u1-discover.md) 검색 UI.
**Next.js App Router + TypeScript**(ADR-D5) · **Tailwind + shadcn/ui + vaul**(ADR-D6).
백엔드 계약 단일 진실: [`backend/src/docsuri/u1/dtos.py`](../backend/src/docsuri/u1/dtos.py).

## 실행

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

기본은 **단독 모드** — 백엔드 없이 내장 mock으로 동작한다(U1 §6 독립 빌드).
실제 백엔드에 연결하려면 `BACKEND_URL`을 설정한다(`.env.example` 참조):

```bash
# 터미널 1 — 백엔드
cd backend && uv run uvicorn docsuri.app:create_app --factory --port 8000
# 터미널 2 — 프론트 (BFF가 /api/search를 백엔드로 프록시, 실패 시 mock 폴백)
cd frontend && BACKEND_URL=http://localhost:8000 npm run dev
```

## 데이터 경로 (BFF)

브라우저는 항상 `POST /api/search`(Next Route Handler)만 호출한다(CORS 불필요).
BFF는 `BACKEND_URL`이 있으면 FastAPI로 프록시(도달 불가 시 mock 폴백), 없으면 내장 mock.
초기 진입은 서버 컴포넌트(`app/page.tsx`)가 `searchParams`로 1차 검색해 SSR — 새로고침 시 URL 상태·결과 복원(US-DISC-02).

## 검증

```bash
npm run lint && npx tsc --noEmit && npm run build
```

## 구조

```
frontend/
├── app/
│   ├── page.tsx              # 서버 컴포넌트: searchParams → 초기 검색(SSR)
│   ├── layout.tsx            # 루트(lang="ko")
│   └── api/search/route.ts   # BFF: 입력 검증 + performSearch 위임
├── components/
│   ├── search-experience.tsx # 'use client' 상태 컨테이너 + URL 동기 + 재검색
│   ├── search-bar.tsx · paper-card.tsx · result-list.tsx
│   ├── filter-sort-bar.tsx   # 데스크톱 인라인 / 모바일 Drawer(vaul)
│   ├── expanded-terms.tsx · query-mapping.tsx
│   └── ui/                    # shadcn 생성물
└── lib/
    ├── types.ts              # dtos.py 미러
    ├── search-service.ts     # 프록시↔mock (서버 전용)
    ├── mock-data.ts · api.ts · url-state.ts · utils.ts
```

## 스토리 매핑 (US-DISC)

- **01 의미 검색**: 검색 폼 + 결과 카드(데스크톱 6메타 1뷰 / 모바일 3메타 + "더 보기").
- **02 정렬·필터**: 정렬(유사도·인용수·최신) + 연도·분야 필터, URL 직렬화로 새로고침 유지.
- **03 키워드 확장**: 확장 칩 체크/해제 → 즉시 재검색.
- **04 한국어 검색**: 한→영 매핑 1줄 표시 + 난이도 라벨(입문 적합 상위).
