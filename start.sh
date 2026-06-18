#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PORT="${PORT:-18888}"
mkdir -p "$ROOT/data" "$ROOT/logs"

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
      sleep 1
    fi
  fi
}

kill_port "$PORT"

if ! python3 -c "import feedparser" 2>/dev/null; then
  python3 -m pip install -r requirements.txt
fi

echo "Starting HR Policy Monitor on http://127.0.0.1:${PORT}"
echo "Verify: bash scripts/verify_service.sh"
exec python3 -m uvicorn app.server:app --host 0.0.0.0 --port "$PORT" --reload
