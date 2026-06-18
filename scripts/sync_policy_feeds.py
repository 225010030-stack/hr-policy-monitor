#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.policy_feed import (  # noqa: E402
    build_daily_digest,
    build_weekly_review,
    notify_digest,
    notify_weekly,
    sync_feeds,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync overseas payroll/benefits policy RSS feeds.")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--digest", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--date", help="Digest date YYYY-MM-DD")
    parser.add_argument("--max-items", type=int, default=500)
    args = parser.parse_args()

    if not any([args.sync, args.digest, args.weekly]):
        args.sync = True

    if args.sync:
        result = sync_feeds(max_items=args.max_items)
        print(json.dumps({"synced_at": result["synced_at"], "new_count": result["new_count"]}, ensure_ascii=False))

    if args.digest:
        day = datetime.strptime(args.date, "%Y-%m-%d") if args.date else None
        digest = build_daily_digest(day=day)
        print(json.dumps({"date": digest["date"], "top": len(digest["items"])}, ensure_ascii=False))
        if args.notify:
            print(json.dumps(notify_digest(digest), ensure_ascii=False))

    if args.weekly:
        review = build_weekly_review()
        print(json.dumps({"week": f"{review['week_start']}~{review['week_end']}", "items": review["total_items"]}, ensure_ascii=False))
        if args.notify:
            print(json.dumps(notify_weekly(review), ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
