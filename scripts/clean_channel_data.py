#!/usr/bin/env python3
"""Clean and finalize channels.json data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"

NAME_DESC_MAP = {
    "bloomingbit": {
        "name": "블루밍비트",
        "description": "한국경제신문 블록체인·가상자산 전문 미디어",
        "status": "공식",
    },
    "xangle_official": {
        "name": "쟁글 (Xangle) 공식",
        "description": "가상자산 공시 및 온체인 데이터 인텔리전스 플랫폼 쟁글",
        "status": "공식",
    },
}

# Not public channels, invalid contact pages, or incorrectly classified accounts.
REMOVE_HANDLES = {
    "alrimbot",
    "bbc_korean",
    "bithumb_official",
    "clien_today",
    "coinness_kr",
    "fmkorea_hotdeal",
    "kiwoom_research",
    "korea_economy",
    "korea_it_news",
    "modulabs",
    "ppomppu_hotdeal",
    "promptengineeringkr",
    "quasarzone_hotdeal",
    "samsung_research",
    "sh_research",
    "teddynote",
    "twealth",
    "yonhapnewsalert",
}


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for cat in data["categories"]:
        filtered_entries = []
        for entry in cat["entries"]:
            handle = entry["handle"]
            if handle in REMOVE_HANDLES:
                continue

            if handle in NAME_DESC_MAP:
                mapping = NAME_DESC_MAP[handle]
                entry["name"] = mapping["name"]
                entry["description"] = mapping["description"]
                entry["status"] = mapping["status"]

            filtered_entries.append(entry)
        cat["entries"] = filtered_entries

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Data cleaned and saved successfully.")


if __name__ == "__main__":
    main()
