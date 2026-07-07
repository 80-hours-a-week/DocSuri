# Runbook — doc-model DLQ drain + native_html backfill (#343 / #344)

> **Status**: unblocked by v1.13.0 (the #420 throttle is now live in prod). This is a
> **production mutation** — run deliberately, verify live depths first (the counts below are
> point-in-time from 2026-07-07 and will have moved). Owner: ingestion/ops (U1).

## Why this was gated

A bulk arXiv backfill on 3 worker tasks blew past arXiv's ~1-req/3s budget → OpenSearch +
ingestion-queue saturation → live search 503 (k-NN 2.0s timeout) and viewer/citation-tree
doc-model starvation. The fix (**PR #420**, shipped in **v1.13.0**) throttles the arXiv caller
to a single task and drops the burst step, so drains no longer refeed the DLQ. With that live,
the drain is safe to run.

Relevant knobs (already in code, no change needed):
- `docsuri-docmodel-builder` autoscale `min_capacity=0, max_capacity=1` — `ops/cdk/stacks/ingestion_stack.py:419`
- bulk ingestion worker autoscale `max_capacity=1` (was 3) — `ingestion_stack.py:395`
- **Do NOT raise either above 1 during the drain** — that is exactly what caused the search 503s.

## 0. Preconditions (verify, don't assume)

```bash
export AWS_PROFILE=AdministratorAccess-028317349537   # region ap-northeast-2
ACCT=028317349537 ; REGION=ap-northeast-2

# a) throttle actually live? desired/running should be <=1, max_capacity 1
aws ecs describe-services --cluster docsuri --services docsuri-docmodel-builder \
  --query 'services[0].{desired:desiredCount,running:runningCount}' --region $REGION

# b) current DLQ depth (was ~24)
aws sqs get-queue-attributes --region $REGION \
  --queue-url https://sqs.$REGION.amazonaws.com/$ACCT/docsuri-docmodel-dlq \
  --attribute-names ApproximateNumberOfMessages

# c) current native_html coverage in S3 (was 10,660 / 21,252)
aws s3 ls s3://docsuri-papers-fulltext-$ACCT/native_html/ --recursive --summarize \
  --region $REGION | tail -1
```

If the daily harvest is mid-freeze (reembed era disabled `docsuri-arxiv-daily` + set autoscale 0),
confirm you actually want steady-state back before step 3 — see [[project_reembed_v3_pivot]].

## 1. Drain the doc-model DLQ (re-enqueue to source)

The messages are reader-triggered doc-model builds that dead-lettered during the contention.
With the throttle live, redrive them back to the source queue so the single builder consumes them:

```bash
# SQS-native redrive (preferred — no custom script). Source = docsuri-docmodel-queue.
aws sqs start-message-move-task --region $REGION \
  --source-arn arn:aws:sqs:$REGION:$ACCT:docsuri-docmodel-dlq \
  --destination-arn arn:aws:sqs:$REGION:$ACCT:docsuri-docmodel-queue \
  --max-number-of-messages-per-second 1     # keep <=1/s so the single builder + arXiv budget hold
```

- If a message is a **poison record** (build fails deterministically, not from contention), it will
  bounce back to the DLQ after `maxReceiveCount`. Pull one and inspect before assuming the drain
  "didn't work": `aws sqs receive-message --queue-url .../docsuri-docmodel-dlq`.
- **PARSER_VERSION caveat**: if any of these are stale doc-models that a parser fix should self-heal,
  a re-run only heals when the cache key changed — bump `PARSER_VERSION` (@N) *before* re-enqueue or
  the cache-hit + dedup skips the rebuild for free. See [[project_docmodel_reembed_gap]].

## 2. Finish the native_html backfill

Re-enqueue only the **missing** papers (don't re-index the whole corpus — arXiv re-index is NOT
needed, [[project_external_backfill]]). The canonical runner is `migrate.py` (the worker
entrypoint), not the removed `ops/.../backfill_v4.py`.

```bash
# Bounded re-enqueue of papers lacking native_html. Run as an ECS run-task on the ingestion
# task-def (in-VPC — the worker self-migrates; do NOT run from a laptop against private RDS/OS).
aws ecs run-task --cluster docsuri --launch-type FARGATE --region $REGION \
  --task-definition docsuri-ingestion \
  --overrides '{"containerOverrides":[{"name":"worker","command":["python","migrate.py","--backfill-native-html","--bounded"]}]}' \
  --network-configuration '<same subnets/SG as the service>'
```

> Confirm the exact `migrate.py` flag against the current worker entrypoint before running —
> flag names drift. If there is no bounded native_html mode, gate on `DOCSURI_BACKFILL_START`
> for a one-shot window rather than an unbounded sweep.

## 3. Restore steady state (only after the drain settles)

1. Re-enable the daily harvest if it was frozen: `aws events enable-rule --name docsuri-arxiv-daily`
   (cron `0 6 * * ? *` = 15:00 KST -> enqueues `{"action":"schedule_tick"}`).
2. Confirm autoscale is back to the **code default `max_capacity=1`** (not 0 from a freeze). No CDK
   change should be needed — if live differs from code, `cdk deploy Docsuri-Ingestion` reconciles.

## 4. Verify

- DLQ depth -> **0** (step 0b re-run).
- `native_html/` object count -> matches corpus (~21k), step 0c.
- **Live search latency nominal** (no k-NN 2.0s timeouts) throughout — this is the canary the
  whole throttle exists to protect. Watch it during step 1–2; if it climbs, pause the move task
  (`aws sqs cancel-message-move-task`).

## Still a decision, not covered here — #344 queue separation

Whether reader-triggered doc-model builds get a **permanently separate queue** from bulk
backfill (vs. relying on the throttle + priority drain) is an open design call. The throttle is a
sufficient stopgap; a dedicated queue is the durable fix if backfills recur. Decide before the
next large pre-2026 history backfill.
