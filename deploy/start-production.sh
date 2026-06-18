#!/usr/bin/env bash
# 生产：前台运行（供 LaunchAgent 或 systemd 托管）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PORT="${PORT:-18888}"
HOST="${HOST:-0.0.0.0}"
WORKERS="${WORKERS:-1}"

mkdir -p "$ROOT/data" "$ROOT/logs"

if ! python3 -c "import feedparser, fastapi" 2>/dev/null; then
  python3 -m pip install -r requirements.txt
fi

echo "HR Policy Monitor (production) http://${HOST}:${PORT}"
exec python3 -m uvicorn app.server:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
