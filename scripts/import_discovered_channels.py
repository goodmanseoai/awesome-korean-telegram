#!/usr/bin/env python3
"""Import reviewed discovery candidates into the canonical channel data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
DEFAULT_CANDIDATES = ROOT / "data" / ".work" / "accepted-candidates.json"

CATEGORY_METADATA = {
    "business-marketing": {
        "name": "비즈니스 · 마케팅",
        "description": "창업, 사업, 마케팅과 브랜딩 정보",
    },
    "culture-hobbies": {
        "name": "문화 · 취미",
        "description": "문화, 예술, 여행, 스포츠와 취미 정보",
    },
    "health": {
        "name": "건강 · 의료",
        "description": "건강, 의료, 제약과 바이오 관련 정보",
        "notice": "건강·의료 정보는 일반적인 참고 자료입니다. 진단이나 치료는 의료 전문가와 상담하세요.",
    },
    "personal-misc": {
        "name": "개인 · 기타",
        "description": "개인이 운영하는 공개 채널과 기타 공개 커뮤니티",
    },
    "overseas-korean": {
        "name": "해외 한인사회",
        "description": "해외 한인과 교민사회를 위한 공개 정보",
    },
    "society": {
        "name": "사회 · 정책",
        "description": "사회, 정책, 법률과 시사 정보",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    candidates = json.loads(args.input.read_text(encoding="utf-8"))
    categories = {category["slug"]: category for category in data["categories"]}
    needed_categories = {candidate["category"] for candidate in candidates}
    existing = {
        entry["handle"].casefold()
        for category in data["categories"]
        for entry in category["entries"]
    }

    for slug, metadata in CATEGORY_METADATA.items():
        if slug in needed_categories and slug not in categories:
            category = {
                "slug": slug,
                "name": metadata["name"],
                "description": metadata["description"],
                "entries": [],
            }
            if metadata.get("notice"):
                category["notice"] = metadata["notice"]
            data["categories"].append(category)
            categories[slug] = category

    added = 0
    skipped = 0
    for candidate in candidates:
        key = candidate["handle"].casefold()
        if key in existing:
            skipped += 1
            continue
        slug = candidate["category"]
        if slug not in categories:
            raise ValueError(f"Unknown category slug: {slug}")
        entry = {
            field: candidate[field]
            for field in (
                "name",
                "handle",
                "url",
                "type",
                "status",
                "description",
                "checked_at",
            )
        }
        categories[slug]["entries"].append(entry)
        existing.add(key)
        added += 1

    for category in data["categories"]:
        category["entries"].sort(key=lambda item: item["name"].casefold())
    data["categories"] = [
        category
        for category in data["categories"]
        if category["entries"] or category["slug"] not in CATEGORY_METADATA
    ]

    print(f"Import preview: add={added}, skip_existing={skipped}")
    if not args.apply:
        print("Dry run only. Pass --apply to update data/channels.json.")
        return 0

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
