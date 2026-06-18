#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from app.knot_router import handle_knot_webhook
from app.bot_format import bot_payload, format_digest_brief, format_feed_brief, format_weekly_brief
from app.policy_feed import (
    build_daily_digest,
    build_weekly_review,
    get_feed,
    get_latest_digest,
    get_latest_weekly,
    notify_digest,
    notify_weekly,
    sync_feeds,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
load_dotenv(ROOT / ".env")

API_TOKEN = os.getenv("MONITOR_API_TOKEN", "").strip()
KNOT_BOT_TOKEN = os.getenv("KNOT_BOT_TOKEN", API_TOKEN).strip()
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
SERVICE_VERSION = "1.2.0"

app = FastAPI(title="HR Policy Monitor", version=SERVICE_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebhookResponse(BaseModel):
    ok: bool
    action: Optional[str] = None
    message: str
    data: Optional[dict[str, Any]] = None


def _check_token(x_token: Optional[str]) -> None:
    if API_TOKEN and x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


def _check_knot_token(x_token: Optional[str]) -> None:
    if KNOT_BOT_TOKEN and x_token != KNOT_BOT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bot token")


@app.get("/api/health")
def health() -> dict[str, Any]:
    feed = get_feed(limit=1)
    return {
        "ok": True,
        "service": "hr-policy-monitor",
        "version": SERVICE_VERSION,
        "synced_at": feed.get("synced_at"),
        "feed_total": feed.get("total"),
        "public_base_url": PUBLIC_BASE_URL or None,
    }


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    """Future webpage / bot integration: discover endpoints without reading source."""
    base = PUBLIC_BASE_URL or "http://127.0.0.1:18888"
    return {
        "ok": True,
        "service": "hr-policy-monitor",
        "version": SERVICE_VERSION,
        "public_base_url": base,
        "endpoints": {
            "health": f"{base}/api/health",
            "feed_json": f"{base}/api/policy-feed?limit=50",
            "digest_json": f"{base}/api/policy-feed/digest",
            "weekly_json": f"{base}/api/policy-feed/weekly",
            "bot_digest_text": f"{base}/api/bot/digest",
            "bot_weekly_text": f"{base}/api/bot/weekly",
            "bot_feed_text": f"{base}/api/bot/feed",
            "knot_webhook": f"{base}/api/webhook/knotbot",
            "web_ui": f"{base}/index.html",
        },
        "knot_commands": list((Path(__file__).resolve().parents[1] / "config" / "knot-command-map.json").exists() and ["政策帮助", "政策早报", "政策周报", "美国政策", "加拿大政策", "英国政策", "最新政策"] or []),
        "integration_note": "Knot 接入见 docs/KNOT_BOT_接入步骤.md",
    }


@app.post("/api/webhook/knotbot")
def webhook_knotbot(
    payload: dict[str, Any],
    x_bot_token: Optional[str] = Header(default=None, alias="X-Bot-Token"),
) -> WebhookResponse:
    """Knot Client 工具入口，契约与 bot-gateway /api/webhook/knotbot 一致。"""
    _check_knot_token(x_bot_token)
    result = handle_knot_webhook(payload)
    return WebhookResponse(**result)


@app.get("/api/bot/digest")
def bot_digest(format: str = Query(default="json")) -> Any:
    text = format_digest_brief()
    if format == "text":
        return PlainTextResponse(text)
    return bot_payload("digest", text)


@app.get("/api/bot/weekly")
def bot_weekly(format: str = Query(default="json")) -> Any:
    text = format_weekly_brief()
    if format == "text":
        return PlainTextResponse(text)
    return bot_payload("weekly", text)


@app.get("/api/bot/feed")
def bot_feed(
    limit: int = Query(default=10, ge=1, le=30),
    region: Optional[str] = Query(default=None),
    min_score: int = Query(default=3, ge=0),
    format: str = Query(default="json"),
) -> Any:
    text = format_feed_brief(limit=limit, region=region, min_score=min_score)
    if format == "text":
        return PlainTextResponse(text)
    return bot_payload("feed", text, {"limit": limit, "region": region, "min_score": min_score})


@app.get("/api/policy-feed")
def policy_feed_list(
    limit: int = Query(default=50, ge=1, le=200),
    region: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    min_score: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return get_feed(limit=limit, region=region, category=category, min_score=min_score)


@app.get("/api/policy-feed/digest")
def policy_feed_digest(date: Optional[str] = Query(default=None)) -> dict[str, Any]:
    return get_latest_digest(date=date)


@app.get("/api/policy-feed/weekly")
def policy_feed_weekly() -> dict[str, Any]:
    return get_latest_weekly()


@app.post("/api/policy-feed/sync")
def policy_feed_sync(x_monitor_token: Optional[str] = Header(default=None, alias="X-Monitor-Token")) -> dict[str, Any]:
    _check_token(x_monitor_token)
    result = sync_feeds()
    return {"ok": True, **result}


@app.post("/api/policy-feed/digest/run")
def policy_feed_digest_run(
    notify: bool = Query(default=False),
    x_monitor_token: Optional[str] = Header(default=None, alias="X-Monitor-Token"),
) -> dict[str, Any]:
    _check_token(x_monitor_token)
    digest = build_daily_digest()
    payload: dict[str, Any] = {"ok": True, "digest": digest}
    if notify:
        payload["notify"] = notify_digest(digest)
    return payload


@app.post("/api/policy-feed/weekly/run")
def policy_feed_weekly_run(
    notify: bool = Query(default=False),
    x_monitor_token: Optional[str] = Header(default=None, alias="X-Monitor-Token"),
) -> dict[str, Any]:
    _check_token(x_monitor_token)
    review = build_weekly_review()
    payload: dict[str, Any] = {"ok": True, "review": review}
    if notify:
        payload["notify"] = notify_weekly(review)
    return payload


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/index.html")


if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
