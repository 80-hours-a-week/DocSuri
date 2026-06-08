#!/usr/bin/env bash
# smoke.sh — minimal end-to-end smoke test against a running demo server.
#
# Assumes the server is up at $BASE_URL (default http://localhost:8000).
# Hits the four walking-skeleton endpoints in user-journey order and
# prints PASS / FAIL per step. Exits non-zero on the first failure.
#
# Usage:
#   ./scripts/smoke.sh                 # against localhost:8000
#   BASE_URL=http://host:9000 ./...    # against a custom host/port

set -u  # -e is *not* set; we want to report each step's status individually.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

BASE_URL="${BASE_URL:-http://localhost:8000}"
SEED_FILE="${SEED_FILE:-$DEMO_DIR/seed/sample-paper.json}"

PASS=0
FAIL=0
FIRST_FAIL_STEP=""

# --- Helpers ---------------------------------------------------------------
report() {
  local step="$1" code="$2" expected="$3"
  if [[ "$code" == "$expected" ]]; then
    printf 'PASS  %-22s HTTP %s\n' "$step" "$code"
    PASS=$((PASS + 1))
  else
    printf 'FAIL  %-22s HTTP %s (expected %s)\n' "$step" "$code" "$expected"
    FAIL=$((FAIL + 1))
    [[ -z "$FIRST_FAIL_STEP" ]] && FIRST_FAIL_STEP="$step"
  fi
}

# Curl with status capture into BODY/CODE globals.
http() {
  local method="$1" path="$2" data="${3:-}"
  local tmp
  tmp="$(mktemp)"
  if [[ -n "$data" ]]; then
    CODE=$(curl -sS -o "$tmp" -w '%{http_code}' \
      -X "$method" \
      -H 'Content-Type: application/json' \
      -d "$data" \
      "$BASE_URL$path" 2>/dev/null || echo "000")
  else
    CODE=$(curl -sS -o "$tmp" -w '%{http_code}' \
      -X "$method" \
      "$BASE_URL$path" 2>/dev/null || echo "000")
  fi
  BODY="$(cat "$tmp")"
  rm -f "$tmp"
}

require_seed() {
  if [[ ! -f "$SEED_FILE" ]]; then
    printf 'FAIL  seed-file missing  %s\n' "$SEED_FILE"
    exit 2
  fi
}

# --- Steps -----------------------------------------------------------------

require_seed

# 1. /api/health
http GET /api/health
report "health" "$CODE" "200"

# 2. /api/search  (POST query "attention", limit 3)
http POST /api/search '{"query":"attention","limit":3}'
# Search is a 200 on success; even 0 results is a 200.
report "search" "$CODE" "200"

# 3. /api/ingest (POST the seed PaperSummary)
SEED_JSON="$(cat "$SEED_FILE")"
http POST /api/ingest "$SEED_JSON"
# Accept either 200 (sync ingest) or 202 (background task).
if [[ "$CODE" == "200" || "$CODE" == "202" ]]; then
  printf 'PASS  %-22s HTTP %s\n' "ingest" "$CODE"
  PASS=$((PASS + 1))
else
  printf 'FAIL  %-22s HTTP %s (expected 200/202)\n' "ingest" "$CODE"
  FAIL=$((FAIL + 1))
  [[ -z "$FIRST_FAIL_STEP" ]] && FIRST_FAIL_STEP="ingest"
fi

# 4. /api/papers/{id}  — poll until the in-memory store has it (max 10s).
PAPER_ID="1706.03762"
PAPER_OK=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  http GET "/api/papers/$PAPER_ID"
  if [[ "$CODE" == "200" ]]; then
    PAPER_OK=1
    break
  fi
  sleep 1
done
if [[ "$PAPER_OK" == "1" ]]; then
  printf 'PASS  %-22s HTTP %s\n' "papers/$PAPER_ID" "$CODE"
  PASS=$((PASS + 1))
else
  printf 'FAIL  %-22s HTTP %s (expected 200 within 10s)\n' "papers/$PAPER_ID" "$CODE"
  FAIL=$((FAIL + 1))
  [[ -z "$FIRST_FAIL_STEP" ]] && FIRST_FAIL_STEP="papers/$PAPER_ID"
fi

# 5. /api/summary
http POST /api/summary "{\"paper_id\":\"$PAPER_ID\",\"length\":\"paragraph\",\"perspective\":\"contribution\"}"
report "summary" "$CODE" "200"

# 6. /api/translate
http POST /api/translate "{\"paper_id\":\"$PAPER_ID\",\"text\":\"The Transformer is based solely on attention mechanisms.\",\"section_id\":\"abstract\"}"
report "translate" "$CODE" "200"

# --- Summary ---------------------------------------------------------------
echo
echo "----- smoke summary -----"
printf 'pass=%d  fail=%d\n' "$PASS" "$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  printf 'first failure: %s\n' "$FIRST_FAIL_STEP"
  exit 1
fi
echo "ALL PASS"
exit 0
