# Fast corpus re-embed rebuild

Rebuild the whole `docsuri-corpus` vector index into a fresh index in **hours, not days**, by
reindexing from the existing index (not re-harvesting arXiv) and fanning the work across many
one-off ECS tasks, then atomically swapping the read alias. No arXiv fetch, no PDF parse — every
field except `vector` is copied straight from the live index.

Two modes:

| Mode | When | Bedrock? | Steps |
|------|------|----------|-------|
| **A — copy** | reshard / index corruption / same embedding model | no | provision → **copy** → finalize → cutover |
| **B — re-embed** | embedding model or dimension change | yes | provision → **reembed** (×N shards) → finalize → cutover |

The steps live in `docsuri_ingestion.reembed` and dispatch through the worker entrypoint exactly
like the v4 migration (`python -m docsuri_ingestion.worker <step>`), so they run as one-off ECS
`run-task`s on the existing `WorkerTaskDef` — no new service, queue, or task definition.

## Why it's fast (and safe)

- **Source = the existing index**, read once (mode A, server-side `_reindex slices=auto`) or via
  sliced scroll (mode B). No 1-req/3s arXiv token bucket, no pdfplumber.
- **Target is offline** (`number_of_replicas=0`, `refresh_interval=-1`) until finalize → minimal
  write amplification. Live reads keep serving the old index the whole time.
- **Fan-out** is `run-task` count, independent of the ingestion service's `max_capacity=1` cap
  (that cap exists to protect arXiv + OpenSearch during harvest backfills; this path harvests
  nothing).
- Floor is Bedrock embed throughput (mode B) — request a `cohere.embed-v4` quota bump first.

## Prerequisites

1. **Resize the OpenSearch domain up** for the rebuild window (cost-no-object → e.g.
   `r6g.2xlarge.search` ×4). This is a blue/green, online change in `ops/cdk/stacks/search_stack.py`
   (`data_nodes`, instance type) — `cdk deploy Docsuri-Search`. Revert after cutover.
2. **Bedrock quota** (mode B): raise the `cohere.embed-v4` on-demand TPM/RPM in Service Quotas so
   N parallel tasks don't sit in throttle backoff. Throttling is now retried (not DLQ'd), but
   headroom is what makes it fast.
3. Confirm env: the target index name defaults to `docsuri-corpus-v3`
   (`DOCSURI_OPENSEARCH_INDEX_REEMBED`); the source defaults to the live alias `docsuri-corpus`
   (`DOCSURI_REEMBED_SOURCE`). For mode B set `DOCSURI_BEDROCK_MODEL_ID` to the **new** model.

## Config (all `DOCSURI_*` env on the run-task container override)

| Env | Default | Meaning |
|-----|---------|---------|
| `DOCSURI_OPENSEARCH_INDEX_REEMBED` | `docsuri-corpus-v3` | rebuild target index |
| `DOCSURI_REEMBED_SOURCE` | (alias `docsuri-corpus`) | index/alias to read from |
| `DOCSURI_REEMBED_SHARDS` | `6` | target primary shards (good for both bulk write and k-NN serve) |
| `DOCSURI_REEMBED_SHARD` / `DOCSURI_REEMBED_SHARD_COUNT` | `0` / `1` | this task's sliced-scroll slice / total slices (mode B fan-out) |
| `DOCSURI_REEMBED_BATCH_SIZE` | `96` | scroll page = embed batch (≤96, Bedrock Cohere limit) |
| `DOCSURI_REEMBED_MIN_DOCUMENTS` | `1` | finalize floor; a good rebuild sets this near the known corpus size (~1.5M) |
| `DOCSURI_REEMBED_COPY_RPS` | `-1` | mode A `_reindex` throttle; `-1` = unlimited |

## Run order

All commands are one-off `aws ecs run-task` on the worker task def, overriding the `worker`
container `command` (and env for the reembed step). Skeleton:

```sh
aws ecs run-task --cluster <cluster> --task-definition <WorkerTaskDef> --launch-type FARGATE \
  --network-configuration '{...worker subnets + SG...}' \
  --overrides '{"containerOverrides":[{"name":"worker","command":["<step>"],
                 "environment":[{"name":"DOCSURI_REEMBED_SHARD","value":"<i>"},
                                {"name":"DOCSURI_REEMBED_SHARD_COUNT","value":"<N>"}]}]}'
```

1. **provision** — `command:["reembed_provision"]`. Creates the tuned target (idempotent).
2. **load**:
   - Mode A: `command:["reembed_copy"]` — one task; server-side `_reindex`, polls to completion.
   - Mode B: launch **N** tasks `command:["reembed"]`, each with `DOCSURI_REEMBED_SHARD=i`
     (i = 0..N-1) and `DOCSURI_REEMBED_SHARD_COUNT=N`. Pick N from Bedrock RPM headroom
     (≈ RPM / per-task RPM; 24–100 is typical). Each task scrolls its slice, re-embeds, bulk-writes.
3. **finalize** — `command:["reembed_finalize"]`. Restores `replicas=1` + `refresh_interval=1s`,
   force-merges, and **gates on `DOCSURI_REEMBED_MIN_DOCUMENTS`** — set it to the expected count so
   a truncated rebuild can't cut over. Run only after all mode-B tasks exit 0.
4. **cutover** — `command:["reembed_cutover"]`. Atomically repoints the `docsuri-corpus` alias to
   the target. Search now serves the new vectors.
5. Revert the domain resize; optionally delete the old index once verified.

## Idempotency & rollback

- Every step is re-runnable. `provision` skips an existing target; `reembed`/`reembed_copy` overwrite
  by `_id` (`chunkId`), so a re-run or a redelivered task converges, never duplicates.
- A mode-B shard that dies just gets relaunched with the same `DOCSURI_REEMBED_SHARD`.
- **Rollback after cutover**: re-point the alias back to the previous index with a one-off
  `reembed_cutover` where `DOCSURI_OPENSEARCH_INDEX_REEMBED=<previous index>`. Instant; the old
  index is untouched until you delete it.

## Caveats

- The worker task def bundles the GROBID sidecar (~20 GB image) — it starts idle on every reembed
  task (no parse work) and just adds cold-start. Acceptable for a one-off; not worth a separate
  task def.
- Long abstracts (> `max_chunk_chars`, rare) split into multiple abstract chunks; mode B re-embeds
  the full `abstract` field for each such sub-chunk. Negligible for a model change (text is
  re-embedded anyway) and irrelevant to mode A. Body chunks reproduce exactly (`lexicalTerms`).
- Mode B `skipped_empty` in the logs counts docs whose stored embed text was empty (should be ~0);
  investigate if non-trivial before cutover.
