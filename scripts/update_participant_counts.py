#!/usr/bin/env python3
"""Refresh public Telegram subscriber/member counts in channels.json."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
USER_AGENT = "awesome-korean-telegram-counts/1.0 (+GitHub public directory)"
EXTRA_RE = re.compile(
    r'<div\s+class=["\']tgme_page_extra["\']>\s*([^<]+)', re.I
)
COUNT_RE = re.compile(
    r"([0-9][0-9\s.,]*)\s+(subscribers|members)", re.I
)


def fetch_extra(handle: str, timeout: float, retries: int) -> str:
    request = urllib.request.Request(
        f"https://t.me/{handle}",
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(512_000).decode("utf-8", errors="replace")
            match = EXTRA_RE.search(body)
            if match:
                return html.unescape(match.group(1)).strip()
            last_error = RuntimeError("participant metadata not found")
            if attempt < retries:
                time.sleep(2.0 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.0 + attempt)
    raise RuntimeError(str(last_error))


def parse_count(extra: str) -> tuple[int | None, str | None]:
    match = COUNT_RE.search(extra)
    if not match:
        return None, None
    digits = re.sub(r"\D", "", match.group(1))
    if not digits:
        return None, None
    return int(digits), match.group(2).casefold()


def fetch_entry(entry: dict, timeout: float, retries: int) -> dict:
    handle = entry["handle"]
    if entry["type"] == "봇":
        return {"handle": handle, "participants": None, "kind": None, "bot": True}
    try:
        extra = fetch_extra(handle, timeout, retries)
        participants, kind = parse_count(extra)
        if participants is None:
            raise RuntimeError("subscriber/member count not found")
        return {
            "handle": handle,
            "participants": participants,
            "kind": kind,
            "bot": False,
            "error": None,
        }
    except RuntimeError as error:
        return {
            "handle": handle,
            "participants": None,
            "kind": None,
            "bot": False,
            "error": str(error),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only fetch non-bot entries without a saved participant count.",
    )
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entries = [
        entry for category in data["categories"] for entry in category["entries"]
    ]
    fetch_entries = [
        entry
        for entry in entries
        if not args.missing_only
        or (
            entry["type"] != "봇"
            and not isinstance(entry.get("participants"), int)
        )
    ]
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_entry, entry, args.timeout, args.retries): entry
            for entry in fetch_entries
        }
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results[result["handle"].casefold()] = result
            if index % 50 == 0 or index == len(futures):
                counted = sum(
                    item.get("participants") is not None for item in results.values()
                )
                print(
                    f"Progress {index}/{len(futures)} with_count={counted}", flush=True
                )

    today = datetime.now().astimezone().date().isoformat()
    counted = 0
    groups = 0
    bots = 0
    failures = 0
    for entry in entries:
        result = results.get(entry["handle"].casefold())
        if result is None:
            if entry["type"] == "봇":
                bots += 1
            elif isinstance(entry.get("participants"), int):
                counted += 1
                if entry.get("participant_kind") == "members":
                    groups += 1
            continue
        if result.get("bot"):
            entry["participants"] = None
            entry["participant_kind"] = None
            bots += 1
            continue
        if result.get("error"):
            failures += 1
            continue
        entry["participants"] = result["participants"]
        entry["participant_kind"] = result["kind"]
        entry["checked_at"] = today
        if result["participants"] is not None:
            counted += 1
        if result["kind"] == "members":
            entry["type"] = "그룹"
            groups += 1
        elif result["kind"] == "subscribers":
            entry["type"] = "채널"

    print(
        f"Summary total={len(entries)} counted={counted} groups={groups} "
        f"bots={bots} failures={failures}"
    )
    if not args.apply:
        print("Dry run only. Pass --apply to update data/channels.json.")
        return 0 if failures == 0 else 1

    data["updated_at"] = today
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {DATA_PATH}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
