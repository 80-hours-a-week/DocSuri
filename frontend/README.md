# frontend — U5 Frontend (Track 3)

> **Owner:** @kyjness (Track 3) · **Deploy unit:** ④ frontend (independent) · **Stack:** Next.js (App Router SSR) · TypeScript · CSS Modules · pnpm
> **Status:** 🟢 hero slice implemented (mock-first). Library/history screens deferred to a follow-up pass.

SSR phone-first web UI: hero → signup → login → search → grounded results + state UX.
Independent deploy unit (④), not part of the backend monolith.

## Quick start

```bash
pnpm install
pnpm dev            # http://localhost:3000  (runs fully on MockTransport — no backend needed)
pnpm test           # Vitest + Testing Library (32 tests)
pnpm build          # Next.js production build (standalone)
pnpm e2e            # Playwright hero-flow E2E (phone viewport)
pnpm gen:types      # refresh the schema drift-dump under types/.schema-raw/
```

### Mock-first demo
The app runs against `MockTransport` (DTO-derived fixtures). The search box branches by keyword so every terminal state is demoable:

| 입력에 포함 | 결과 |
|---|---|
| (일반어) | 결과 카드 페이지 |
| `없음` / `empty` | 빈 결과 |
| `기권` / `abstain` | 기권(근거 없음) |
| `저하` / `degraded` | 저하 배너 + 부분 결과 |
| `오류` / `error` | 서버 오류 + 재시도 |
| `네트워크` / `fail` | 네트워크 오류 + 재시도 |

(로그인은 mock에서 아무 이메일/비밀번호로 통과합니다.)

## Architecture
- **ApiClient + Transport seam** (`lib/api/`) — single entry to the backend → U6 gateway. Mock now, swap to `HttpTransport` (server-only) when the gateway lands; components are untouched.
- **Session** — httpOnly cookie (transport); only non-sensitive `SessionInfo` reaches the client (SEC-3/12).
- **State machine** — `SearchScreen` branches the `SearchResponse` union (page/empty/abstain/degraded/invalid) via `StateView`; abstain ≠ empty (BR-U5-9).
- **Security** — `ResultCard` renders only the 7 exposed fields (SEC-9), escapes external text, http/https + noopener links; CSP/`frame-ancestors 'self'` in `middleware.ts`; 2-layer error boundaries (fail-closed, SEC-15).

## Contract (from `shared/`, do not fork or edit)
- `shared/dtos/*.schema.json` is the SSOT. `types/generated/*.ts` mirror the exposed contract; `pnpm gen:types` dumps a raw codegen to `types/.schema-raw/` for drift review. See `aidlc-docs/construction/u5-frontend/code/README.md` for the TypeGen design note.

## Invariants
- Render only externally-exposed DTO fields (SEC-9). `password` is request-input-only (SEC-12/3).
- Stable `data-testid` on interactive elements (automation-friendly).
- All backend calls go through `ApiClient` → U6 gateway (no direct fetch in components).
