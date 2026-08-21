#!/usr/bin/env python3
"""Validate directory data and check that Telegram public pages still exist."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
GENERIC_TELEGRAM_TITLES = {
    "Telegram – a new era of messaging",
    "Telegram: Contact",
}
TITLE_PATTERN = re.compile(
    r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)


def load_entries() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as file:
        data = json.load(file)

    if data.get("schema_version") != 1:
        raise ValueError("Unsupported or missing schema_version")

    entries: list[dict] = []
    for category in data.get("categories", []):
        if not category.get("slug") or not category.get("name"):
            raise ValueError("Every category needs slug and name")
        for entry in category.get("entries", []):
            entry = dict(entry)
            entry["category"] = category["slug"]
            entries.append(entry)
    return entries


def validate_entries(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_handles: set[str] = set()
    seen_urls: set[str] = set()
    required = {
        "name",
        "handle",
        "url",
        "type",
        "status",
        "description",
        "checked_at",
    }

    for entry in entries:
        missing = sorted(required - entry.keys())
        if missing:
            errors.append(f"{entry.get('name', '<unknown>')}: missing {', '.join(missing)}")
            continue

        handle_key = entry["handle"].casefold()
        url_key = entry["url"].casefold().rstrip("/")
        expected_url = f"https://t.me/{entry['handle']}".casefold()
        if handle_key in seen_handles:
            errors.append(f"Duplicate handle: @{entry['handle']}")
        if url_key in seen_urls:
            errors.append(f"Duplicate URL: {entry['url']}")
        if url_key != expected_url:
            errors.append(
                f"@{entry['handle']}: URL must be https://t.me/<handle>, got {entry['url']}"
            )
        if entry["type"] not in {"채널", "그룹", "봇"}:
            errors.append(f"@{entry['handle']}: unsupported type {entry['type']}")
        seen_handles.add(handle_key)
        seen_urls.add(url_key)
    return errors


def is_generic_contact_page(title: str) -> bool:
    return title in GENERIC_TELEGRAM_TITLES or title.startswith("Telegram: Contact @")


def fetch_page(url: str, timeout: float, retries: int) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "korea-telegram-channel-link-checker/1.0 (+GitHub Actions)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(512_000).decode("utf-8", errors="replace")
            match = TITLE_PATTERN.search(body)
            if not match:
                raise ValueError("og:title metadata not found")
            return html.unescape(match.group(1)).strip(), body
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Validate JSON without making network requests.",
    )
    args = parser.parse_args()

    try:
        entries = load_entries()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"DATA ERROR: {error}")
        return 1

    errors = validate_entries(entries)
    if errors:
        for error in errors:
            print(f"DATA ERROR: {error}")
        return 1

    print(f"Data validation passed for {len(entries)} entries.")
    if args.data_only:
        return 0

    failed: list[str] = []
    for index, entry in enumerate(entries, start=1):
        handle = entry["handle"]
        try:
            title, body = fetch_page(entry["url"], args.timeout, args.retries)
            if is_generic_contact_page(title):
                raise RuntimeError(f"generic Telegram page returned: {title}")
            if "tgme_page_extra" not in body:
                raise RuntimeError("public channel, group, or bot metadata not found")
            print(f"[{index:02}/{len(entries)}] OK   @{handle}")
        except RuntimeError as error:
            failed.append(handle)
            print(f"[{index:02}/{len(entries)}] FAIL @{handle}: {error}")
        if index != len(entries):
            time.sleep(args.delay)

    if failed:
        print(f"\nFailed links ({len(failed)}): " + ", ".join(f"@{item}" for item in failed))
        return 1
    print(f"\nAll {len(entries)} Telegram links are reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
