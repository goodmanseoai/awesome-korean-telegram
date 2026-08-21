#!/usr/bin/env python3
"""Render the channel tables in README.md from data/channels.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
README_PATH = ROOT / "README.md"

TOC_START = "<!-- TOC:START -->"
TOC_END = "<!-- TOC:END -->"
CHANNELS_START = "<!-- CHANNELS:START -->"
CHANNELS_END = "<!-- CHANNELS:END -->"


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
    lines = []
    for category in categories:
        lines.append(f"- [{category['name']}](#{category['slug']})")
    return "\n".join(lines)


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_channels(categories: list[dict]) -> str:
    sections: list[str] = []
    for category in categories:
        entries = category["entries"]
        lines = [
            f"<a id=\"{category['slug']}\"></a>",
            f"### {category['name']} ({len(entries)})",
            "",
            category["description"],
        ]
        if category.get("notice"):
            lines.extend(["", f"> ⚠️ {category['notice']}"])
        lines.extend(
            [
                "",
                "| 이름 | 유형 | 운영 구분 | 설명 | 확인일 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for entry in entries:
            name = escape_cell(entry["name"])
            description = escape_cell(entry["description"])
            lines.append(
                f"| [{name}]({entry['url']}) `@{entry['handle']}` "
                f"| {entry['type']} | {entry['status']} | {description} "
                f"| {entry['checked_at']} |"
            )
        sections.append("\n".join(lines))
    total = sum(len(category["entries"]) for category in categories)
    summary = f"현재 **{total}개**의 공개 채널·봇을 수록하고 있습니다."
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

