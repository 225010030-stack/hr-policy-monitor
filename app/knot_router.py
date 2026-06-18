"""Knot Bot webhook router — same contract as bot-gateway /api/webhook/knotbot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.bot_format import format_digest_brief, format_feed_brief, format_weekly_brief
from app.policy_feed import get_feed, sync_feeds

ROOT = Path(__file__).resolve().parents[1]
COMMAND_MAP_FILE = ROOT / "config" / "knot-command-map.json"

HELP_TEXT = """【薪酬福利政策助手 · 可用指令】

政策帮助          显示本菜单
政策早报          昨日 Top5 可能相关（leave/benefit/payroll）
政策周报          本周复盘 + SOP 提示
美国政策          US 高分资讯（≥5 分）
加拿大政策        CA 高分资讯
英国政策          UK 高分资讯
最新政策          全区域近期资讯（≥3 分）

说明：数据来自 RSS + GitHub Actions 同步，非实时立法解读；重要变更请点链接核对原文。"""


def load_command_map() -> dict[str, str]:
    if not COMMAND_MAP_FILE.exists():
        return {}
    obj = json.loads(COMMAND_MAP_FILE.read_text(encoding="utf-8"))
    return dict(obj.get("commands") or {})


def parse_text_from_payload(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("text"),
        payload.get("content"),
        payload.get("query"),
        payload.get("message"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in ["text", "content", "query", "message"]:
            c = nested.get(key)
            if isinstance(c, str) and c.strip():
                return c.strip()
    return ""


def resolve_action_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower().strip()
    cmd_map = load_command_map()
    for keyword in sorted(cmd_map.keys(), key=len, reverse=True):
        if keyword.lower() in lowered:
            return cmd_map[keyword]
    return None


def execute_action(action: str) -> tuple[bool, str, dict[str, Any]]:
    if action == "policy_help":
        return True, HELP_TEXT, {"kind": "help"}

    if action == "policy_digest":
        text = format_digest_brief()
        return True, text, {"kind": "digest"}

    if action == "policy_weekly":
        text = format_weekly_brief()
        return True, text, {"kind": "weekly"}

    if action == "policy_feed_us":
        text = format_feed_brief(limit=10, region="US", min_score=5)
        feed = get_feed(limit=1, region="US", min_score=5)
        return True, text, {"kind": "feed", "region": "US", "synced_at": feed.get("synced_at")}

    if action == "policy_feed_ca":
        text = format_feed_brief(limit=10, region="CA", min_score=5)
        feed = get_feed(limit=1, region="CA", min_score=5)
        return True, text, {"kind": "feed", "region": "CA", "synced_at": feed.get("synced_at")}

    if action == "policy_feed_uk":
        text = format_feed_brief(limit=10, region="UK", min_score=5)
        feed = get_feed(limit=1, region="UK", min_score=5)
        return True, text, {"kind": "feed", "region": "UK", "synced_at": feed.get("synced_at")}

    if action == "policy_feed_all":
        text = format_feed_brief(limit=10, region=None, min_score=3)
        feed = get_feed(limit=1, min_score=3)
        return True, text, {"kind": "feed", "region": "ALL", "synced_at": feed.get("synced_at")}

    if action == "policy_sync":
        result = sync_feeds()
        msg = f"RSS 同步完成 · 新增 {result.get('new_count', 0)} 条 · 共 {result.get('total', 0)} 条"
        return True, msg, {"kind": "sync", **{k: result.get(k) for k in ("synced_at", "new_count", "total")}}

    return False, f"未知动作: {action}", {}


def handle_knot_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    text = parse_text_from_payload(payload)
    action = resolve_action_from_text(text)
    if not action:
        return {
            "ok": False,
            "action": None,
            "message": (
                "未识别指令。可用：政策帮助、政策早报、政策周报、美国政策、加拿大政策、英国政策、最新政策"
            ),
            "data": {"input": text},
        }

    ok, message, data = execute_action(action)
    return {
        "ok": ok,
        "action": action,
        "message": message,
        "data": data,
    }
