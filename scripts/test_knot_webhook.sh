#!/usr/bin/env bash
# 模拟 Knot Client 工具回调，联调 /api/webhook/knotbot
set -euo pipefail
BASE="${1:-http://127.0.0.1:18888}"
TOKEN="${KNOT_BOT_TOKEN:-${MONITOR_API_TOKEN:-test-token-123}}"

hdr=(-H "Content-Type: application/json")
if [[ -n "$TOKEN" ]]; then
  hdr+=(-H "X-Bot-Token: $TOKEN")
fi

run() {
  local label="$1" text="$2"
  echo "==== $label ($text) ===="
  curl -s -X POST "$BASE/api/webhook/knotbot" "${hdr[@]}" -d "{\"text\":\"$text\"}" | python3 -m json.tool
  echo
}

echo "Knot webhook test BASE=$BASE"
echo

run "帮助" "政策帮助"
run "早报" "政策早报"
run "周报" "政策周报"
run "美国" "美国政策"
run "未识别" "随便问问"
