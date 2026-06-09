#!/usr/bin/env bash
# run.sh — one-command launcher for the Sprint 1 walking-skeleton demo.
#
# Behaviour:
#   1. Detect `uv` (preferred) or fall back to `python -m venv` + pip.
#   2. Create / reuse a venv at `./.venv` (idempotent).
#   3. Install runtime + dev deps from pyproject.toml.
#   4. Print a one-line banner with the resolved mode (mock vs live).
#   5. Exec uvicorn on $HOST:$PORT (defaults: 0.0.0.0:8000).
#
# AGENTS.md §4.1 / §4.2: mode is determined by env vars only; no secrets
# are written to disk by this script.

set -euo pipefail

# --- Resolve script directory so the script works from anywhere ------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Load .env if present (do not require it) ------------------------------
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  . ./.env
  set +a
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# --- Determine LLM mode (matches container.mode_label) ---------------------
if [[ -n "${AWS_BEDROCK_REGION:-}" ]]; then
  MODE="live (Bedrock)"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  MODE="live (Claude)"
else
  MODE="mock"
fi

# --- Pick installer --------------------------------------------------------
USE_UV=0
if command -v uv >/dev/null 2>&1; then
  USE_UV=1
fi

VENV_DIR=".venv"

install_with_uv() {
  # `uv venv` is idempotent — it skips creation if the dir exists.
  if [[ ! -d "$VENV_DIR" ]]; then
    uv venv "$VENV_DIR" --python 3.11
  fi
  # `uv pip install -e .[dev]` resolves quickly even on warm runs.
  uv pip install --python "$VENV_DIR/bin/python" -e ".[dev]" >/dev/null
}

install_with_pip() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  . "$VENV_DIR/bin/activate"
  python -m pip install --upgrade pip >/dev/null
  pip install -e ".[dev]" >/dev/null
  deactivate
}

if [[ "$USE_UV" -eq 1 ]]; then
  install_with_uv
else
  install_with_pip
fi

# --- Best-effort browser open (silently skipped if no opener exists) -------
open_browser() {
  local url="$1"
  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    (sleep 1 && open "$url") >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 1 && xdg-open "$url") >/dev/null 2>&1 &
  fi
}

URL="http://localhost:${PORT}"

# Open the browser only when launched interactively (not under CI / smoke).
if [[ -t 1 && "${DEMO_NO_BROWSER:-0}" != "1" ]]; then
  open_browser "$URL"
fi

printf 'Demo ready at %s (mode: %s)\n' "$URL" "$MODE"

# --- Launch server ---------------------------------------------------------
if [[ "$USE_UV" -eq 1 ]]; then
  exec "$VENV_DIR/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
else
  exec "$VENV_DIR/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
