# U8 Citation Graph — Logical Components

**Unit**: U8 Citation Graph  
**Stage**: CONSTRUCTION -> NFR Design  
**Date**: 2026-06-21

| Component | Responsibility |
| --- | --- |
| `CitationGraphApi` | Authenticated FastAPI handlers for tree read and node save. |
| `CitationGraphService` | Cache read, provider fetch, tree build, save, telemetry orchestration. |
| `SemanticScholarClient` | Backward-reference lookup through Semantic Scholar Graph API. |
| `CitationSnapshotStore` | 7-day Redis snapshot read/write. |
| `CitationTreeBuilder` | Sorts, folds duplicates/cycles, enforces depth <= 2 and nodes <= 50. |
| `CitationQuotaGuard` | Applies U6 gateway/quota signal before provider calls. |
| `LibrarySaveGateway` | Adapts saveable citation nodes to U4 Library minimal metadata. |
| `CitationTelemetryPublisher` | Emits U8 lookup/refresh/save events to U6. |

## API Surface

| Route | Purpose |
| --- | --- |
| `GET /api/papers/{paper_id}/citation-tree` | Read tree; supports `depth`, `expandNodeId`, `refresh`. |
| `POST /api/papers/{paper_id}/citation-tree/save` | Save one saveable citation node to U4 Library. |

U8 does not own paper-detail frontend, LLM citation inference, or durable graph storage in v1.
