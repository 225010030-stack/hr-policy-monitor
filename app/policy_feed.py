#!/usr/bin/env python3
"""RSS policy feed sync, scoring, daily digest, and weekly review."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

try:
    import feedparser
except ImportError:  # pragma: no cover
    feedparser = None  # type: ignore

from app.notify import send_email, send_wecom_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
SOURCES_FILE = CONFIG_DIR / "policy_sources.json"
KEYWORDS_FILE = CONFIG_DIR / "policy_keywords.json"
FEED_FILE = DATA_DIR / "policy-feed.json"
DIGEST_FILE = DATA_DIR / "policy-digest.json"
WEEKLY_FILE = DATA_DIR / "policy-weekly.json"
USER_AGENT = "HR-Policy-Monitor/1.0"

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_dt(value: str) -> Optional[datetime]:
    txt = (value or "").strip()
    if not txt:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(txt.replace("Z", "+0000"), fmt)
            if dt.tzinfo is None:
                return dt
            return dt.astimezone().replace(tzinfo=None)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone().replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def _strip_html(text: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", txt).strip()


def _item_id(link: str, title: str, published: str) -> str:
    raw = f"{link}|{title}|{published}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sources() -> list[dict[str, Any]]:
    obj = load_json(SOURCES_FILE, {"sources": []})
    rows = list(obj.get("sources") or [])
    return [x for x in rows if x.get("enabled", True) is not False]


def load_keyword_config() -> dict[str, Any]:
    return load_json(KEYWORDS_FILE, {"high_weight": {}, "region_boost": {}})


def score_item(item: dict[str, Any], kw_cfg: dict[str, Any]) -> tuple[int, list[str]]:
    text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("summary") or ""),
            " ".join(item.get("tags") or []),
            str(item.get("source_name") or ""),
        ]
    ).lower()
    weights: dict[str, int] = kw_cfg.get("high_weight") or {}
    matched: list[str] = []
    score = 0
    for keyword, weight in weights.items():
        if keyword.lower() in text:
            matched.append(keyword)
            score += int(weight)
    region = str(item.get("region") or "").upper()
    region_boost = (kw_cfg.get("region_boost") or {}).get(region, 0)
    if region_boost:
        score += int(region_boost)
    return score, matched


def _fetch_url(url: str, timeout: int = 20) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _parse_feed_stdlib(url: str, timeout: int = 20) -> list[dict[str, str]]:
    raw = _fetch_url(url, timeout=timeout)
    root = ET.fromstring(raw)
    tag = root.tag.lower()
    items: list[dict[str, str]] = []

    if tag.endswith("feed"):
        for entry in root.findall("atom:entry", ATOM_NS):
            title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip()
            link_el = entry.find("atom:link[@rel='alternate']", ATOM_NS) or entry.find("atom:link", ATOM_NS)
            link = link_el.get("href", "") if link_el is not None else ""
            published = (
                entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
                or entry.findtext("atom:published", default="", namespaces=ATOM_NS)
                or ""
            ).strip()
            summary = (
                entry.findtext("atom:summary", default="", namespaces=ATOM_NS)
                or entry.findtext("atom:content", default="", namespaces=ATOM_NS)
                or ""
            ).strip()
            items.append({"title": title, "link": link, "published": published, "summary": _strip_html(summary)})
        return items

    for entry in root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        published = (entry.findtext("pubDate") or entry.findtext("date") or "").strip()
        summary = (entry.findtext("description") or entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or "").strip()
        items.append({"title": title, "link": link, "published": published, "summary": _strip_html(summary)})
    return items


def fetch_source_entries(source: dict[str, Any]) -> tuple[list[dict[str, str]], Optional[str]]:
    url = str(source.get("url") or "").strip()
    if not url:
        return [], "missing url"
    try:
        if feedparser is not None:
            raw = _fetch_url(url, timeout=20)
            parsed = feedparser.parse(raw, agent=USER_AGENT)
            if getattr(parsed, "bozo", False) and not parsed.entries:
                return [], str(getattr(parsed, "bozo_exception", "parse error"))
            rows: list[dict[str, str]] = []
            for entry in parsed.entries[:30]:
                published = (
                    getattr(entry, "published", "")
                    or getattr(entry, "updated", "")
                    or getattr(entry, "created", "")
                )
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                rows.append(
                    {
                        "title": str(getattr(entry, "title", "") or "").strip(),
                        "link": str(getattr(entry, "link", "") or "").strip(),
                        "published": str(published or "").strip(),
                        "summary": _strip_html(str(summary or "")),
                    }
                )
            return rows, None
        return _parse_feed_stdlib(url), None
    except Exception as exc:  # noqa: BLE001
        return [], str(exc)


def sync_feeds(max_items: int = 500) -> dict[str, Any]:
    sources = load_sources()
    kw_cfg = load_keyword_config()
    existing = load_json(FEED_FILE, {"items": []})
    by_id = {str(x.get("id")): x for x in (existing.get("items") or []) if x.get("id")}

    source_stats: list[dict[str, Any]] = []
    new_count = 0

    for src in sources:
        entries, err = fetch_source_entries(src)
        added = 0
        for entry in entries:
            if not entry.get("title"):
                continue
            published_at = _parse_dt(entry.get("published", ""))
            published_iso = published_at.isoformat(timespec="seconds") if published_at else _now_iso()
            item_id = _item_id(entry.get("link", ""), entry.get("title", ""), published_iso)
            if item_id in by_id:
                continue
            item = {
                "id": item_id,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": (entry.get("summary", "") or "")[:500],
                "published_at": published_iso,
                "fetched_at": _now_iso(),
                "source_id": src.get("id"),
                "source_name": src.get("name"),
                "region": src.get("region"),
                "category": src.get("category"),
                "tags": src.get("tags") or [],
            }
            score, matched = score_item(item, kw_cfg)
            item["score"] = score
            item["matched_keywords"] = matched
            by_id[item_id] = item
            added += 1
            new_count += 1
        source_stats.append(
            {
                "source_id": src.get("id"),
                "source_name": src.get("name"),
                "fetched": len(entries),
                "added": added,
                "error": err,
            }
        )

    items = sorted(by_id.values(), key=lambda x: x.get("published_at", ""), reverse=True)[:max_items]
    payload = {
        "synced_at": _now_iso(),
        "total": len(items),
        "new_count": new_count,
        "source_stats": source_stats,
        "items": items,
    }
    save_json(FEED_FILE, payload)
    return payload


def _day_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day)
    return start, start + timedelta(days=1)


def items_for_day(items: list[dict[str, Any]], day: datetime) -> list[dict[str, Any]]:
    start, end = _day_bounds(day)
    scoped: list[dict[str, Any]] = []
    for item in items:
        dt = _parse_dt(str(item.get("published_at") or item.get("fetched_at") or ""))
        if dt is None:
            continue
        if start <= dt < end:
            scoped.append(item)
    return scoped


def build_daily_digest(day: Optional[datetime] = None, top_n: int = 5) -> dict[str, Any]:
    day = day or (datetime.now() - timedelta(days=1))
    feed = load_json(FEED_FILE, {"items": []})
    items = items_for_day(list(feed.get("items") or []), day)
    ranked = sorted(items, key=lambda x: (x.get("score", 0), x.get("published_at", "")), reverse=True)
    top = ranked[:top_n]
    digest = {
        "date": day.strftime("%Y-%m-%d"),
        "generated_at": _now_iso(),
        "total_candidates": len(items),
        "top_n": top_n,
        "items": top,
        "summary_text": format_digest_text(top, day.strftime("%Y-%m-%d")),
    }
    history = load_json(DIGEST_FILE, {"digests": []})
    digests = [d for d in (history.get("digests") or []) if d.get("date") != digest["date"]]
    digests.append(digest)
    digests.sort(key=lambda x: x.get("date", ""), reverse=True)
    save_json(DIGEST_FILE, {"digests": digests[:60]})
    return digest


def build_weekly_review(week_end: Optional[datetime] = None, top_n: int = 15) -> dict[str, Any]:
    week_end = week_end or datetime.now()
    week_start = week_end - timedelta(days=7)
    feed = load_json(FEED_FILE, {"items": []})
    scoped: list[dict[str, Any]] = []
    for item in feed.get("items") or []:
        dt = _parse_dt(str(item.get("published_at") or ""))
        if dt is None:
            continue
        if week_start <= dt <= week_end:
            scoped.append(item)

    ranked = sorted(scoped, key=lambda x: (x.get("score", 0), x.get("published_at", "")), reverse=True)
    by_region: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in scoped:
        by_region[str(item.get("region") or "OTHER")] = by_region.get(str(item.get("region") or "OTHER"), 0) + 1
        by_category[str(item.get("category") or "other")] = by_category.get(str(item.get("category") or "other"), 0) + 1

    review = {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "generated_at": _now_iso(),
        "total_items": len(scoped),
        "high_score_items": [x for x in ranked if int(x.get("score") or 0) >= 5][:top_n],
        "top_items": ranked[:top_n],
        "by_region": by_region,
        "by_category": by_category,
        "action_prompts": build_weekly_action_prompts(ranked[:top_n]),
        "summary_text": format_weekly_text(ranked[:top_n], week_start, week_end, by_region, by_category),
    }
    history = load_json(WEEKLY_FILE, {"reviews": []})
    reviews = [r for r in (history.get("reviews") or []) if r.get("week_end") != review["week_end"]]
    reviews.append(review)
    reviews.sort(key=lambda x: x.get("week_end", ""), reverse=True)
    save_json(WEEKLY_FILE, {"reviews": reviews[:26]})
    return review


def build_weekly_action_prompts(items: list[dict[str, Any]]) -> list[str]:
    prompts: list[str] = []
    cats = {str(x.get("category") or "") for x in items}
    if "leave" in cats:
        prompts.append("核对各国/各州 leave accrual、timecard 与 Prepayroll checklist 是否需要更新。")
    if "benefits" in cats:
        prompts.append("与 Benefits COE 确认 open enrollment / 计划变更是否影响分摊或提单字段。")
    if "tax" in cats or "compensation" in cats:
        prompts.append("检查 ADP/Workday 税率、预扣、最低工资相关配置与本期 payroll cutoff。")
    if not prompts:
        prompts.append("本周信号较少；维持现有 SOP，下周继续监控。")
    return prompts


def format_digest_text(items: list[dict[str, Any]], day: str) -> str:
    lines = [f"【薪酬福利政策早报】{day}", f"共筛选 {len(items)} 条可能相关：", ""]
    for idx, item in enumerate(items, 1):
        lines.append(f"{idx}. [{item.get('region')}|{item.get('score')}分] {item.get('title')}")
        if item.get("link"):
            lines.append(f"   {item.get('link')}")
    if not items:
        lines.append("（昨日暂无高分条目，可查看资讯墙全量列表。）")
    return "\n".join(lines)


def format_weekly_text(
    items: list[dict[str, Any]],
    week_start: datetime,
    week_end: datetime,
    by_region: dict[str, int],
    by_category: dict[str, int],
) -> str:
    lines = [
        f"【薪酬福利政策周报】{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}",
        f"本周条目：{sum(by_region.values())} | 区域：{', '.join(f'{k}:{v}' for k, v in sorted(by_region.items()))}",
        f"类别：{', '.join(f'{k}:{v}' for k, v in sorted(by_category.items()))}",
        "",
        "重点 Top5：",
    ]
    for idx, item in enumerate(items[:5], 1):
        lines.append(f"{idx}. [{item.get('region')}|{item.get('score')}分] {item.get('title')}")
        if item.get("link"):
            lines.append(f"   {item.get('link')}")
    lines.extend(["", "建议复盘："])
    for prompt in build_weekly_action_prompts(items):
        lines.append(f"- {prompt}")
    return "\n".join(lines)


def notify_digest(digest: dict[str, Any]) -> dict[str, Any]:
    text = str(digest.get("summary_text") or "")
    day = str(digest.get("date") or "")
    wecom_users = [x.strip() for x in os.getenv("POLICY_DIGEST_WECOM_USERS", "").split(",") if x.strip()]
    email_to = [x.strip() for x in os.getenv("POLICY_DIGEST_EMAIL_TO", "").split(",") if x.strip()]
    return {
        "wecom": send_wecom_text(text, wecom_users) if wecom_users else {"ok": False, "skipped": True},
        "email": send_email(f"薪酬福利政策早报 {day}", text, email_to) if email_to else {"ok": False, "skipped": True},
    }


def notify_weekly(review: dict[str, Any]) -> dict[str, Any]:
    text = str(review.get("summary_text") or "")
    subject = f"薪酬福利政策周报 {review.get('week_start')} ~ {review.get('week_end')}"
    wecom_users = [x.strip() for x in os.getenv("POLICY_DIGEST_WECOM_USERS", "").split(",") if x.strip()]
    email_to = [x.strip() for x in os.getenv("POLICY_DIGEST_EMAIL_TO", "").split(",") if x.strip()]
    return {
        "wecom": send_wecom_text(text, wecom_users) if wecom_users else {"ok": False, "skipped": True},
        "email": send_email(subject, text, email_to) if email_to else {"ok": False, "skipped": True},
    }


def get_feed(
    limit: int = 50,
    region: Optional[str] = None,
    category: Optional[str] = None,
    min_score: int = 0,
) -> dict[str, Any]:
    feed = load_json(FEED_FILE, {"items": [], "synced_at": None})
    items = list(feed.get("items") or [])
    if region:
        r = region.strip().upper()
        items = [x for x in items if str(x.get("region", "")).upper() == r]
    if category:
        c = category.strip().lower()
        items = [x for x in items if str(x.get("category", "")).lower() == c]
    if min_score > 0:
        items = [x for x in items if int(x.get("score") or 0) >= min_score]
    return {"ok": True, "synced_at": feed.get("synced_at"), "total": len(items), "items": items[:limit]}


def get_latest_digest(date: Optional[str] = None) -> dict[str, Any]:
    digests = list(load_json(DIGEST_FILE, {"digests": []}).get("digests") or [])
    if not digests:
        return {"ok": True, "digest": None}
    if date:
        for d in digests:
            if d.get("date") == date:
                return {"ok": True, "digest": d}
        return {"ok": True, "digest": None}
    return {"ok": True, "digest": digests[0]}


def get_latest_weekly() -> dict[str, Any]:
    reviews = list(load_json(WEEKLY_FILE, {"reviews": []}).get("reviews") or [])
    if not reviews:
        return {"ok": True, "review": None}
    return {"ok": True, "review": reviews[0]}
