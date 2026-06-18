#!/usr/bin/env python3
"""Plain-text and compact responses for chat bots (Knot / 企微 / webhook)."""

from __future__ import annotations

from typing import Any, Optional

from app.policy_feed import get_feed, get_latest_digest, get_latest_weekly


def format_feed_brief(limit: int = 10, region: Optional[str] = None, min_score: int = 3) -> str:
    data = get_feed(limit=limit, region=region, min_score=min_score)
    items = data.get("items") or []
    lines = [f"【政策资讯】共 {data.get('total', 0)} 条 · 同步 {data.get('synced_at') or '—'}", ""]
    if not items:
        lines.append("暂无匹配条目。")
        return "\n".join(lines)
    for idx, item in enumerate(items[:limit], 1):
        lines.append(f"{idx}. [{item.get('region')}|{item.get('score')}分] {item.get('title')}")
        if item.get("link"):
            lines.append(f"   {item.get('link')}")
    return "\n".join(lines)


def format_digest_brief() -> str:
    data = get_latest_digest()
    digest = data.get("digest")
    if not digest:
        return "尚无每日早报。请等待 GitHub Actions 或运行 scripts/sync_policy_feeds.py --digest"
    text = str(digest.get("summary_text") or "").strip()
    if text:
        return text
    items = digest.get("items") or []
    lines = [f"【薪酬福利政策早报】{digest.get('date')}", ""]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.get('region')}|{item.get('score')}分] {item.get('title')}")
        if item.get("link"):
            lines.append(f"   {item.get('link')}")
    return "\n".join(lines)


def format_weekly_brief() -> str:
    data = get_latest_weekly()
    review = data.get("review")
    if not review:
        return "尚无每周复盘。请等待周一 Actions 或运行 scripts/sync_policy_feeds.py --weekly"
    text = str(review.get("summary_text") or "").strip()
    return text or f"周报 {review.get('week_start')} ~ {review.get('week_end')} · {review.get('total_items')} 条"


def bot_payload(kind: str, text: str, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": True, "kind": kind, "text": text}
    if extra:
        payload.update(extra)
    return payload
