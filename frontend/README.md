# frontend — U5 Frontend (Track 3)

> **Owner:** @kyjness (Track 3) · **Deploy unit:** ④ frontend (independent) · **Stack:** Next.js (App Router SSR) · TypeScript · CSS Modules · pnpm
> **Status:** 🟢 production pass — hero + library/saved/history implemented; aligned to the real backend routes; real transport wired via the BFF (mock-first default).

SSR phone-first web UI: hero → signup → login → search → grounded results + state UX,
plus the personal-data screens (library / saved searches / history).
Independent deploy unit (④), not part of the backend monolith.

## Quick start

```bash
pnpm install
pnpm dev            # http://localhost:3000  (runs fully on MockTransport — no backend needed)
pnpm test           # Vitest + Testing Library (48 tests)
pnpm build          # Next.js production build (standalone)
pnpm e2e            # Playwright hero-flow E2E (phone viewport)
pnpm gen:types      # refresh the schema drift-dump under types/.schema-raw/
```

## Configuration (mock ↔ real)

| Env var | Scope | Effect |
|---|---|---|
| _(none)_ | — | **Mock-first default:** client uses in-browser `MockTransport`. No backend needed. |
| `NEXT_PUBLIC_DOCSURI_REAL_API=1` | client (build-time) | Client routes calls through the same-origin BFF (`RouteHandlerTransport` → `/bff/*`). |
| `DOCSURI_GATEWAY_URL=https://…` | **server-only** | The BFF forwards to the real U6 gateway (`HttpTransport`); the httpOnly session cookie and the URL stay server-side (SEC-3/12). Unset ⇒ the BFF serves mock. |

Real path: browser → same-origin `/bff/*` (cookie auto-attached) → server `HttpTransport` → U6 gateway. The token never enters client JS.

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
- **ApiClient + Transport seam** (`lib/api/`) — single entry to the backend → U6 gateway. `getApiClient()` selects the transport by config (mock vs BFF); components/ApiClient are untouched.
- **BFF** (`app/bff/[...path]/route.ts`) — server-side seam that owns the gateway URL and forwards the inbound httpOnly cookie (+ relays Set-Cookie). Real path is `HttpTransport` (`import 'server-only'`, never bundled to the client).
- **Routes** — `/` hero · `/signup` · `/login` · `/search` (protected) · `/library`, `/library/saved`, `/library/history` (protected, US-L2/L1/L3). Collections paginate via opaque cursor ("더 보기") — no offset/total-count.
- **Backend contract** — search `POST /api/search`; accounts `/auth/*` (login sets the cookie and returns `{status,message}` only — the client refreshes via `GET /auth/session`); library `/library/{saved-searches,items,history}` (+ `/rerun`).
- **Session** — httpOnly cookie (transport); only non-sensitive `SessionInfo` reaches the client (SEC-3/12).
- **State machine** — `SearchScreen` branches the `SearchResponse` union (page/empty/abstain/degraded/invalid) via `StateView`; abstain ≠ empty (BR-U5-9). Saved/history rerun reuse the same classifier (`OutcomeView`).
- **Security** — `ResultCard` renders only the 7 exposed fields (SEC-9; library cards drop `relevance`), escapes external text, http/https + noopener links; CSP/`frame-ancestors 'self'` in `middleware.ts`; 2-layer error boundaries (fail-closed, SEC-15).

## Dependency flags (tracked outside U5)
- **Gateway auth injection** — the assembled backend must resolve the session cookie into `request.state.principal` for `/library/*` and `/api/search`; until then those endpoints fail-closed (401) when run against the real backend. Backend coordination zone + system-infra step.
- **reCAPTCHA** — `POST /auth/login` accepts an optional reCAPTCHA token; sending it needs the site key (secret/infra) and is part of the real-deploy wiring.

## Contract (from `shared/`, do not fork or edit)
- `shared/dtos/*.schema.json` is the SSOT. `types/generated/*.ts` mirror the exposed contract; `pnpm gen:types` dumps a raw codegen to `types/.schema-raw/` for drift review. See `aidlc-docs/construction/u5-frontend/code/README.md` for the TypeGen design note.

## Invariants
- Render only externally-exposed DTO fields (SEC-9). `password` is request-input-only (SEC-12/3).
- Stable `data-testid` on interactive elements (automation-friendly).
- All backend calls go through `ApiClient` → U6 gateway (no direct fetch in components).
