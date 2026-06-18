#!/usr/bin/env bash
# 接入前自检：API、Bot 文本、数据文件
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${1:-http://127.0.0.1:18888}"

echo "== HR Policy Monitor verify =="
echo "BASE=$BASE"
echo

check() {
  local name="$1" url="$2"
  code=$(curl -s -o /tmp/hr_monitor_check.json -w "%{http_code}" "$url" || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "OK  $name ($code)"
  else
    echo "FAIL $name ($code) $url"
    exit 1
  fi
}

check "health" "$BASE/api/health"
check "meta" "$BASE/api/meta"
check "feed" "$BASE/api/policy-feed?limit=3"
check "digest" "$BASE/api/policy-feed/digest"
check "weekly" "$BASE/api/policy-feed/weekly"
check "bot_digest" "$BASE/api/bot/digest"
check "bot_weekly" "$BASE/api/bot/weekly"
check "bot_feed" "$BASE/api/bot/feed?limit=3"

if [[ -n "${KNOT_BOT_TOKEN:-${MONITOR_API_TOKEN:-}}" ]]; then
  hdr=(-H "Content-Type: application/json" -H "X-Bot-Token: ${KNOT_BOT_TOKEN:-$MONITOR_API_TOKEN}")
  code=$(curl -s -o /tmp/hr_knot.json -w "%{http_code}" -X POST "$BASE/api/webhook/knotbot" "${hdr[@]}" -d '{"text":"政策帮助"}' || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "OK  knot_webhook ($code)"
  else
    echo "FAIL knot_webhook ($code) — 检查 KNOT_BOT_TOKEN"
    exit 1
  fi
else
  echo "SKIP knot_webhook (set KNOT_BOT_TOKEN to test)"
fi

echo
echo "Sample bot digest:"
curl -s "$BASE/api/bot/digest?format=text" | head -8
echo
echo "Data files:"
for f in policy-feed.json policy-digest.json policy-weekly.json; do
  if [[ -f "$ROOT/data/$f" ]]; then
    echo "  OK  data/$f"
  else
    echo "  MISS data/$f"
  fi
done
echo
echo "All checks passed."
