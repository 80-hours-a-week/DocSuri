# U8 Citation Graph — Runtime Architecture

**Unit**: U8 Citation Graph  
**Stage**: CONSTRUCTION -> NFR Design  
**Date**: 2026-06-21

```text
Client / FE branch
  -> U6 gateway/auth/rate path
  -> FastAPI CitationGraphApi
  -> CitationGraphService
     -> Redis snapshot store
     -> Semantic Scholar Graph API
     -> U4 Library save path
     -> U6 ObservabilityHub/EventStore
```

## Runtime Placement

U8 runs inside the existing backend FastAPI app-shell behind the U6 gateway. No new ECS service is introduced.

## Provider Boundary

- Provider: Semantic Scholar Graph API.
- Direction: backward references only.
- Timeout: 2 seconds target.
- Retry: at most 1 retry.
- Default CI: no external provider calls.

## Cache Boundary

- Store: existing Redis.
- TTL: 7 days.
- Payload: normalized response shape, provider status, fetched timestamp.

## Security Boundary

All APIs require the existing user session. Provider credentials are server-only env/secrets. Library save remains owner-scoped through U4.
