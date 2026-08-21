#!/usr/bin/env python3
"""Fetch, validate, and update curated Korean Telegram public channels."""

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"


def fetch_channel_info(handle: str, timeout: float = 8.0) -> dict | None:
    """Fetch public channel metadata from Telegram web preview."""
    clean_handle = handle.lstrip("@").strip()
    url = f"https://t.me/s/{clean_handle}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception:
        # Fallback to direct t.me link
        try:
            req_direct = urllib.request.Request(
                f"https://t.me/{clean_handle}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req_direct, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    title_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    desc_m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    sub_m = re.search(r'<div\s+class=["\']tgme_page_extra["\']>\s*([^<]+)\s*</div>', content, re.I)

    if not title_m:
        return None

    title = html.unescape(title_m.group(1)).strip()
    if title in {"Telegram – a new era of messaging", "Telegram: Contact"} or title.startswith(
        "Telegram: Contact @"
    ):
        return None

    description = html.unescape(desc_m.group(1)).strip() if desc_m else ""
    extra = sub_m.group(1).strip() if sub_m else ""
    if not extra:
        return None

    return {
        "handle": clean_handle,
        "name": title,
        "description": description,
        "extra": extra,
        "url": f"https://t.me/{clean_handle}",
    }


def clean_description(desc: str, default: str) -> str:
    """Sanitize description for markdown table."""
    if not desc:
        return default
    # Remove excessive whitespace and line breaks
    desc = re.sub(r"\s+", " ", desc).strip()
    # If description is too long, truncate
    if len(desc) > 80:
        desc = desc[:77] + "..."
    return desc


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"[{today}] 한국어 텔레그램 채널 수집 및 검증 시작...")
    # Candidate channels by category to check and add if valid
    candidates = {
        "crypto": [
            ("bloomingbit", "블루밍비트", "공식", "한국경제신문 블록체인·가상자산 전문 미디어"),
            ("xangle_official", "쟁글 (Xangle) 공식", "공식", "가상자산 공시 및 온체인 데이터 플랫폼 쟁글"),
        ],
    }

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Collect existing handles
    existing_handles = set()
    for cat in data["categories"]:
        for entry in cat["entries"]:
            existing_handles.add(entry["handle"].casefold())

    added_count = 0
    updated_count = 0

    # 1. Update existing channels checked_at & info
    print("\n--- 1. 기존 등록 채널 검증 및 수집 ---")
    for cat in data["categories"]:
        for entry in cat["entries"]:
            info = fetch_channel_info(entry["handle"])
            if info:
                entry["checked_at"] = today
                updated_count += 1
                print(f"  [OK] @{entry['handle']} ({entry['name']})")
            else:
                print(f"  [WARN] @{entry['handle']} 접근 불가")
            time.sleep(0.3)

    # 2. Check and add candidate channels
    print("\n--- 2. 신규 한국어 채널 탐색 및 수집 ---")
    for cat in data["categories"]:
        slug = cat["slug"]
        if slug not in candidates:
            continue
        for handle, default_name, status, default_desc in candidates[slug]:
            if handle.casefold() in existing_handles:
                continue

            info = fetch_channel_info(handle)
            if info:
                name = info["name"] if info["name"] else default_name
                desc = clean_description(info["description"], default_desc)
                new_entry = {
                    "name": name,
                    "handle": info["handle"],
                    "url": info["url"],
                    "type": "채널",
                    "status": status,
                    "description": desc,
                    "checked_at": today,
                }
                cat["entries"].append(new_entry)
                existing_handles.add(handle.casefold())
                added_count += 1
                print(f"  [ADDED] + @{handle} -> {name} ({slug})")
            else:
                print(f"  [SKIP] @{handle} (미존재 또는 접근 불가)")
            time.sleep(0.3)

    data["updated_at"] = today

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] 기존 {updated_count}개 채널 확인, 신규 {added_count}개 채널 추가 저장됨.")


if __name__ == "__main__":
    main()
