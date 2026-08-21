#!/usr/bin/env python3
"""Export channels.json to CSV format with UTF-8 BOM."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
CSV_PATH = ROOT / "data" / "channels.csv"


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for cat in data.get("categories", []):
        cat_name = cat["name"]
        cat_slug = cat["slug"]
        for entry in cat.get("entries", []):
            rows.append({
                "카테고리": cat_name,
                "슬러그": cat_slug,
                "채널명": entry.get("name", ""),
                "핸들": f"@{entry.get('handle', '')}",
                "URL": entry.get("url", ""),
                "유형": entry.get("type", ""),
                "운영구분": entry.get("status", ""),
                "설명": entry.get("description", ""),
                "확인일자": entry.get("checked_at", ""),
            })

    fieldnames = ["카테고리", "슬러그", "채널명", "핸들", "URL", "유형", "운영구분", "설명", "확인일자"]

    # Write CSV with UTF-8 BOM for Excel compatibility
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} channels to {CSV_PATH}")


if __name__ == "__main__":
    main()
