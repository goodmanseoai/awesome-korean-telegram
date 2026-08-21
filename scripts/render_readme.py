#!/usr/bin/env python3
"""Render the channel tables in README.md from data/channels.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
README_PATH = ROOT / "README.md"

TOC_START = "<!-- TOC:START -->"
TOC_END = "<!-- TOC:END -->"
CHANNELS_START = "<!-- CHANNELS:START -->"
CHANNELS_END = "<!-- CHANNELS:END -->"

CATEGORY_ICONS = {
    "tech-ai": "💻",
    "news-knowledge": "📰",
    "life": "🛍️",
    "careers": "💼",
    "real-estate": "🏠",
    "finance": "📈",
    "crypto": "🪙",
    "telegram-tools": "🤖",
    "health": "🩺",
    "personal-misc": "👤",
    "overseas-korean": "🌏",
}

TYPE_ICONS = {"채널": "📢", "그룹": "👥", "봇": "🤖"}
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
BARE_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|me|kr|co)(?:/\S*)?", re.I
)
CUT_MARKER_RE = re.compile(
    r"(?:📢\s*chat|🎈\s*x\s*:|🐥\s*유튜브|✏️\s*공지방|🚨|💁|📞|"
    r"채널문의|homepage\s*:|유튜브\s*:|telegram\s*:|twitter\s*:|"
    r"링크트리\s*:|채팅방\s*:)",
    re.I,
)


def load_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def replace_section(text: str, start: str, end: str, body: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"README marker pair is missing or duplicated: {start}, {end}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{body.rstrip()}\n{end}{after}"


def render_toc(categories: list[dict]) -> str:
    lines = ["| 카테고리 | 수록 | 카테고리 | 수록 |", "| --- | ---: | --- | ---: |"]
    cells = [
        (
            f"[{CATEGORY_ICONS.get(category['slug'], '📂')} "
            f"{category['name']}](#{category['slug']})",
            f"{len(category['entries']):,}개",
        )
        for category in categories
    ]
    for index in range(0, len(cells), 2):
        left = cells[index]
        right = cells[index + 1] if index + 1 < len(cells) else ("", "")
        lines.append(f"| {left[0]} | {left[1]} | {right[0]} | {right[1]} |")
    return "\n".join(lines)


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def display_description(value: str) -> str:
    if value.startswith("You can view and join") or value.startswith("You can contact"):
        return "공개 텔레그램 채널"
    marker = CUT_MARKER_RE.search(value)
    if marker and marker.start() >= 12:
        value = value[: marker.start()]
    value = URL_RE.sub("", value)
    value = EMAIL_RE.sub("", value)
    value = BARE_DOMAIN_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip(" -·|📢📌👉")
    if len(value) > 88:
        value = value[:87].rstrip() + "…"
    return value or "공개 텔레그램 채널"


def format_participants(entry: dict) -> str:
    value = entry.get("participants")
    return f"{value:,}" if isinstance(value, int) else "—"


def render_channels(categories: list[dict]) -> str:
    sections: list[str] = []
    for category in categories:
        entries = sorted(
            category["entries"],
            key=lambda entry: (
                -entry["participants"]
                if isinstance(entry.get("participants"), int)
                else float("inf"),
                entry["name"].casefold(),
            ),
        )
        icon = CATEGORY_ICONS.get(category["slug"], "📂")
        lines = [
            f"<a id=\"{category['slug']}\"></a>",
            "<details>",
            f"<summary><strong>{icon} {category['name']}</strong> "
            f"<sub>{len(entries):,}개</sub></summary>",
            "",
            f"> {category['description']} · 참가자 수 내림차순",
        ]
        if category.get("notice"):
            lines.extend(["", f"> ⚠️ {category['notice']}"])
        lines.extend(
            [
                "",
                "| 채널 | 운영 | 구독자·멤버 | 소개 |",
                "| --- | :---: | ---: | --- |",
            ]
        )
        for entry in entries:
            name = escape_cell(entry["name"])
            description = escape_cell(display_description(entry["description"]))
            type_icon = TYPE_ICONS.get(entry["type"], "📢")
            channel = (
                f"{type_icon} [{name}]({entry['url']})<br>"
                f"<sub><code>@{entry['handle']}</code> · {entry['type']}</sub>"
            )
            lines.append(
                f"| {channel} | {entry['status']} | "
                f"{format_participants(entry)} | {description} |"
            )
        lines.extend(["", "</details>"])
        sections.append("\n".join(lines))
    total = sum(len(category["entries"]) for category in categories)
    latest = max(
        entry["checked_at"]
        for category in categories
        for entry in category["entries"]
    )
    summary = (
        f"> **{total:,}개** 공개 채널·그룹·봇 · "
        f"**{len(categories)}개** 카테고리 · **{latest}** 점검\n>\n"
        "> 아래 카테고리를 펼쳐 보세요. 브라우저의 페이지 찾기로 채널명이나 `@아이디`를 검색할 수 있습니다."
    )
    return summary + "\n\n" + "\n\n".join(sections)


def render(readme: str, data: dict) -> str:
    categories = data["categories"]
    rendered = replace_section(readme, TOC_START, TOC_END, render_toc(categories))
    return replace_section(
        rendered,
        CHANNELS_START,
        CHANNELS_END,
        render_channels(categories),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when README.md does not match the generated output.",
    )
    args = parser.parse_args()

    data = load_data()
    current = README_PATH.read_text(encoding="utf-8")
    expected = render(current, data)

    if args.check:
        if current != expected:
            print("README.md is out of date. Run: python scripts/render_readme.py")
            return 1
        print("README.md is up to date.")
        return 0

    README_PATH.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Rendered {README_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
