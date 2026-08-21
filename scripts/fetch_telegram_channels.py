#!/usr/bin/env python3
"""Fetch and inspect Telegram public channel metadata."""

import json
import re
import urllib.request
import html
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"


def fetch_channel_info(handle: str, timeout: float = 10.0) -> dict | None:
    """Fetch public channel metadata from Telegram web preview."""
    url = f"https://t.me/s/{handle}"
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
    except Exception as e:
        return None

    # Check if channel exists / not generic
    title_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    desc_m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']*)["\']', content, re.I)
    img_m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']*)["\']', content, re.I)

    # Subscribers extra info
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
        "handle": handle,
        "name": title,
        "description": description,
        "extra": extra,
        "url": f"https://t.me/{handle}",
        "image": img_m.group(1) if img_m else None,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    test_handles = ["GeekNewsHada", "FastStockNews", "tokenpost_kr", "hotdeal_kr"]
    for h in test_handles:
        info = fetch_channel_info(h)
        print(f"Handle: @{h}")
        if info:
            print(f"  Name: {info['name']}")
            print(f"  Extra: {info['extra']}")
            print(f"  Desc: {info['description'][:80]}...")
        else:
            print("  Failed or not found")
        time.sleep(0.5)
