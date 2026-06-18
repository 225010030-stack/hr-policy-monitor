#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI(title="HR Policy Monitor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_token(x_token: Optional[str]) -> None:
    if API_TOKEN and x_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "hr-policy-monitor"}


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
