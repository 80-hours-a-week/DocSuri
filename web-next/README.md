# DocSuri — web (Next.js 14)

Phase 0 frontend per AGENTS.md §5. Vanilla web stays at `demo/web/` for the
walking-skeleton smoke tests.

## Local dev

```bash
pnpm install     # or npm / yarn
cp .env.example .env.local
pnpm dev
```

## Layers

- **App Router** (`app/`) — RSC by default, client islands for chat.
- **NextAuth** (`app/api/auth/[...nextauth]/route.ts`) — Kakao + Google. ORCID arrives with #04 / #11.
- **Vercel AI SDK** (`app/api/chat/route.ts`) — Anthropic Claude Haiku 4.5 direct. Bedrock switch is bundled with the EKS sprint.
- **PWA** (`next-pwa`) — production-only service worker registered from `public/manifest.webmanifest`.
- **Backend proxy** — `/api/backend/*` rewrites to the FastAPI app in `BACKEND_URL`.
