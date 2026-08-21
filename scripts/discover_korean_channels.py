#!/usr/bin/env python3
"""Discover and validate Korean-language public Telegram channels.

The script crawls the public Korean-language index on Telegram Register,
optionally merges extra seed handles, validates every handle against Telegram's
public preview, and writes review artifacts under data/.work/ (gitignored).
It never reads Telegram messages through a user account and never handles
private invite links, phone numbers, or Telegram login credentials.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"
WORK_DIR = ROOT / "data" / ".work"
REGISTER_START = "https://tgregister.com/browse/language/kor"
USER_AGENT = "awesome-korean-telegram-discovery/1.0 (+GitHub public directory)"

CHANNEL_LINK_RE = re.compile(r'href="/channel/([A-Za-z0-9_]{5,})"', re.I)
NEXT_LINK_RE = re.compile(
    r'href="(/browse/language/kor/from/[A-Za-z0-9_-]+)"', re.I
)
TITLE_RE = re.compile(
    r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']*)["\']',
    re.I,
)
DESCRIPTION_RE = re.compile(
    r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']*)["\']',
    re.I,
)
EXTRA_RE = re.compile(r'<div\s+class=["\']tgme_page_extra["\']>\s*([^<]+)', re.I)
DATETIME_RE = re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.I)

HARD_BLOCK_TERMS = {
    "19금",
    "adult",
    "바카라",
    "카지노",
    "조건만남",
    "도박",
    "먹튀",
    "마약",
    "대마",
    "누드",
    "nude",
    "porn",
    "sex",
    "야동",
    "토토",
    "betting",
    "gambling",
    "계정판매",
    "계정 판매",
    "카톡 인증",
    "카톡인증",
    "해외카톡",
    "텔레그램 계정 판매",
    "개인정보 판매",
    "신상정보",
    "블랙리스트",
    "사기피해 공유",
    "법무부 감독관리국",
    "수익으로 증명",
    "바이낸스선물",
    "선물심볼",
}

PIRACY_TERMS = {
    "공공재방",
    "뉴토끼",
    "마나토끼",
    "무료 영화",
    "영화 공유",
    "웹툰 공유",
    "유료자료",
    "전자책 공유",
    "토렌트",
    "pdf 공유",
    "수능 링크",
    "공공재",
    "자료 분류채널",
    "링크모음",
    "블랙툰",
    "blacktoon",
    "newtoki",
    "manatoki",
}

HIGH_RISK_PROMO_TERMS = {
    "수익보장",
    "원금보장",
    "리딩방",
    "코인 시그널",
    "선물 리딩",
    "무료 리딩",
    "에어드랍",
    "airdrop",
    "airdr0p",
    "bounty",
    "레퍼럴",
}

LEGITIMACY_TERMS = {
    "공식",
    "뉴스",
    "리서치",
    "연구",
    "언론",
    "미디어",
    "증권",
    "보고서",
}

PERSONAL_TERMS = {
    "개인 채널",
    "개인적인 견해",
    "대표",
    "애널리스트",
    "연구원",
    "교수",
    "작가",
    "기자",
    "변호사",
    "의사",
    "개발자",
    "운영자",
    "소장",
}

CATEGORY_RULES = [
    ("careers", {"채용", "취업", "커리어", "일자리", "구인", "인턴"}),
    ("real-estate", {"부동산", "아파트", "청약", "주택", "재개발", "재건축"}),
    ("health", {"건강", "의료", "의학", "제약", "바이오", "병원", "의사", "헬스", "운동"}),
    ("crypto", {"가상자산", "디지털자산", "블록체인", "비트코인", "이더리움", "업비트", "빗썸", "크립토", "디파이", "디센터", "web3", "crypto", "코인"}),
    ("finance", {"증권", "주식", "투자", "리서치", "경제", "금융", "시장", "애널리스트", "etf", "채권", "코스피", "기업분석", "공시", "리츠", "자산", "매매", "차트", "증시", "기업", "산업", "전략", "주주", "invest", "stock", "stocks", "ir"}),
    ("tech-ai", {"ai", "인공지능", "개발", "개발자", "it", "테크", "반도체", "소프트웨어", "데이터", "코딩", "보안"}),
    ("business-marketing", {"마케팅", "브랜딩", "스타트업", "창업", "사업", "비즈니스", "세일즈", "광고"}),
    ("culture-hobbies", {"문화", "영화", "음악", "미술", "사진", "여행", "맛집", "취미", "스포츠", "게임", "공연"}),
    ("overseas-korean", {"한인", "교민", "호주", "미국", "캐나다", "일본", "베트남", "캄보디아", "해외생활"}),
    ("society", {"정치", "사회", "정책", "법률", "시사", "국회", "정부"}),
    ("life", {"핫딜", "할인", "쇼핑", "날씨", "미세먼지", "생활", "육아", "요리", "반려", "패션", "뷰티"}),
    ("news-knowledge", {"뉴스", "언론", "속보", "브리핑", "지식", "인문", "과학", "교육", "공부", "영어", "책", "수능", "시험"}),
]


def fetch_text(url: str, timeout: float = 20.0, retries: int = 2) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7"},
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(1_500_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.0 + attempt)
    raise RuntimeError(str(last_error))


def crawl_register(max_pages: int, delay: float) -> tuple[set[str], list[str]]:
    handles: set[str] = set()
    visited: list[str] = []
    url: str | None = REGISTER_START
    while url and len(visited) < max_pages:
        try:
            body = fetch_text(url)
        except RuntimeError as error:
            print(
                f"REGISTER stopped_after={len(visited)} url={url} error={error}",
                flush=True,
            )
            break
        visited.append(url)
        handles.update(match.group(1) for match in CHANNEL_LINK_RE.finditer(body))
        next_match = NEXT_LINK_RE.search(body)
        url = urllib.parse.urljoin(REGISTER_START, next_match.group(1)) if next_match else None
        if len(visited) == 1 or len(visited) % 10 == 0 or not url:
            print(
                f"REGISTER pages={len(visited)} unique_handles={len(handles)}",
                flush=True,
            )
        if url:
            time.sleep(delay)
    return handles, visited


def load_existing_handles() -> set[str]:
    with DATA_PATH.open(encoding="utf-8") as file:
        data = json.load(file)
    return {
        entry["handle"].casefold()
        for category in data["categories"]
        for entry in category["entries"]
    }


def load_seed_handles(paths: list[Path]) -> set[str]:
    handles: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        handles.update(
            match.group(1)
            for match in re.finditer(
                r"(?:https?://t\.me/(?:s/)?|@)([A-Za-z0-9_]{5,})", content
            )
        )
    return handles


def iter_string_values(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_string_values(child)


def load_apify_dataset_handles(dataset_ids: list[str]) -> set[str]:
    if not dataset_ids:
        return set()
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        raise RuntimeError("APIFY_TOKEN is required with --apify-dataset-id")
    handles: set[str] = set()
    for dataset_id in dataset_ids:
        url = (
            f"https://api.apify.com/v2/datasets/{dataset_id}/items"
            "?clean=true&format=json&limit=1000"
        )
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            items = json.loads(response.read().decode("utf-8"))
        before = len(handles)
        for text in iter_string_values(items):
            handles.update(
                match.group(1)
                for match in re.finditer(
                    r"(?:https?://t\.me/(?:s/)?|/channel/|@)([A-Za-z0-9_]{5,})",
                    text,
                )
            )
        print(
            f"APIFY dataset={dataset_id} items={len(items)} new_handles={len(handles) - before}",
            flush=True,
        )
    return handles


def load_github_code_handles(queries: list[str], max_pages: int) -> set[str]:
    if not queries:
        return set()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required with --github-query")
    handles: set[str] = set()
    for query in queries:
        query_added = 0
        for page in range(1, max_pages + 1):
            params = urllib.parse.urlencode(
                {"q": query, "per_page": 100, "page": page}
            )
            request = urllib.request.Request(
                f"https://api.github.com/search/code?{params}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.text-match+json",
                    "User-Agent": USER_AGENT,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                if error.code in {403, 422}:
                    print(
                        f"GITHUB query={query!r} stopped page={page} status={error.code}",
                        flush=True,
                    )
                    break
                raise
            items = payload.get("items", [])
            before = len(handles)
            for item in items:
                for match in item.get("text_matches", []):
                    fragment = match.get("fragment", "")
                    handles.update(
                        found.group(1)
                        for found in re.finditer(
                            r"(?:https?://t\.me/(?:s/)?|@)([A-Za-z0-9_]{5,})",
                            fragment,
                        )
                    )
            query_added += len(handles) - before
            if len(items) < 100:
                break
            time.sleep(2.2)
        print(
            f"GITHUB query={query!r} new_handles={query_added}", flush=True
        )
    return handles


def parse_subscribers(extra: str) -> int | None:
    match = re.search(r"([0-9][0-9\s.,]*)\s+(?:subscribers|members)", extra, re.I)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def clean_description(value: str, maximum: int = 140) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= maximum else value[: maximum - 1].rstrip() + "…"


def contains_term(text: str, term: str) -> bool:
    lowered_term = term.casefold()
    if re.fullmatch(r"[a-z0-9+#.-]+", lowered_term):
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(lowered_term)}(?![a-z0-9])",
                text,
            )
        )
    return lowered_term in text


def contains_any(text: str, terms: set[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def classify_category(text: str) -> str:
    lowered = text.casefold()
    scores = [
        (sum(1 for term in terms if contains_term(lowered, term)), -index, slug)
        for index, (slug, terms) in enumerate(CATEGORY_RULES)
    ]
    score, _, slug = max(scores)
    return slug if score > 0 else "personal-misc"


def classify_status(text: str) -> str:
    lowered = text.casefold()
    if "공식" in lowered or "official" in lowered:
        return "공식"
    if any(term.casefold() in lowered for term in PERSONAL_TERMS):
        return "개인"
    return "커뮤니티"


def rejection_reason(
    handle: str, title: str, description: str, subscribers: int | None
) -> str | None:
    combined = f"{handle} {title} {description}".casefold()
    hangul_count = len(re.findall(r"[가-힣]", combined))
    if hangul_count < 3:
        return "insufficient-korean"
    if subscribers is None:
        return "missing-channel-subscriber-metadata"
    if subscribers is not None and subscribers < 100:
        return "under-100-subscribers"
    if contains_any(combined, HARD_BLOCK_TERMS):
        return "unsafe-content"
    if contains_any(combined, PIRACY_TERMS):
        return "piracy-risk"
    if contains_any(combined, HIGH_RISK_PROMO_TERMS):
        return "high-risk-promotion"
    crypto_terms = dict(CATEGORY_RULES)["crypto"]
    if contains_any(combined, crypto_terms) and not contains_any(
        combined, LEGITIMACY_TERMS
    ):
        return "unverified-crypto"
    return None


def validate_handle(handle: str) -> dict:
    try:
        body = fetch_text(f"https://t.me/{handle}", timeout=15.0, retries=1)
    except RuntimeError as error:
        return {"handle": handle, "accepted": False, "reason": f"fetch-error:{error}"}

    title_match = TITLE_RE.search(body)
    description_match = DESCRIPTION_RE.search(body)
    extra_match = EXTRA_RE.search(body)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""
    description = (
        html.unescape(description_match.group(1)).strip() if description_match else ""
    )
    extra = html.unescape(extra_match.group(1)).strip() if extra_match else ""
    if not title or title.startswith("Telegram: Contact") or not extra_match:
        return {"handle": handle, "accepted": False, "reason": "not-public-channel"}

    subscribers = parse_subscribers(extra)
    reason = rejection_reason(handle, title, description, subscribers)
    combined = f"{handle} {title} {description}"
    last_dates = DATETIME_RE.findall(body)
    record = {
        "name": clean_description(title, 80),
        "handle": handle,
        "url": f"https://t.me/{handle}",
        "type": "채널",
        "status": classify_status(combined),
        "description": clean_description(description) or "한국어 공개 텔레그램 채널",
        "checked_at": datetime.now(timezone.utc).astimezone().date().isoformat(),
        "category": classify_category(combined),
        "subscribers": subscribers,
        "source": "tgregister-language-kor",
        "last_post_at": last_dates[-1] if last_dates else None,
        "accepted": reason is None,
        "reason": reason,
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--crawl-delay", type=float, default=0.35)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed-file", type=Path, action="append", default=[])
    parser.add_argument("--apify-dataset-id", action="append", default=[])
    parser.add_argument("--github-query", action="append", default=[])
    parser.add_argument("--github-max-pages", type=int, default=10)
    args = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    register_handles, visited = crawl_register(args.max_pages, args.crawl_delay)
    seed_handles = load_seed_handles(args.seed_file)
    apify_handles = load_apify_dataset_handles(args.apify_dataset_id)
    github_handles = load_github_code_handles(
        args.github_query, args.github_max_pages
    )
    existing = load_existing_handles()
    candidate_map: dict[str, str] = {}
    for handle in register_handles | seed_handles | apify_handles | github_handles:
        candidate_map.setdefault(handle.casefold(), handle)
    candidates = sorted(
        handle
        for key, handle in candidate_map.items()
        if key not in existing
    )
    print(
        f"VALIDATION candidates={len(candidates)} existing_excluded={len(existing)} workers={args.workers}",
        flush=True,
    )

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(validate_handle, handle): handle for handle in candidates}
        for index, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if index % 100 == 0 or index == len(futures):
                accepted = sum(1 for item in results if item.get("accepted"))
                print(
                    f"VALIDATION progress={index}/{len(futures)} accepted={accepted}",
                    flush=True,
                )

    accepted = sorted(
        (item for item in results if item.get("accepted")),
        key=lambda item: (item["category"], -(item.get("subscribers") or 0), item["handle"].casefold()),
    )
    rejected = sorted(
        (item for item in results if not item.get("accepted")),
        key=lambda item: (str(item.get("reason")), item["handle"].casefold()),
    )
    reason_counts: dict[str, int] = {}
    for item in rejected:
        reason = str(item.get("reason"))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "register_pages": len(visited),
        "register_handles": len(register_handles),
        "seed_handles": len(seed_handles),
        "apify_handles": len(apify_handles),
        "github_handles": len(github_handles),
        "existing_handles": len(existing),
        "validated_candidates": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "rejection_reasons": reason_counts,
        "accepted": accepted,
        "rejected": rejected,
    }
    report_path = WORK_DIR / "discovery-report.json"
    accepted_path = WORK_DIR / "accepted-candidates.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    accepted_path.write_text(
        json.dumps(accepted, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"RESULT accepted={len(accepted)} rejected={len(rejected)}")
    print(f"REPORT {report_path}")
    print(f"ACCEPTED {accepted_path}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
