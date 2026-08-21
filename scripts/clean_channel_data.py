#!/usr/bin/env python3
"""Clean and finalize channels.json data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "channels.json"

NAME_DESC_MAP = {
    "teddynote": {
        "name": "테디노트",
        "description": "AI·딥러닝·머신러닝·데이터 분석 관련 튜토리얼 및 지식 공유",
        "status": "커뮤니티"
    },
    "promptengineeringkr": {
        "name": "프롬프트 엔지니어링 코리아",
        "description": "생성형 AI 모델(LLM) 프롬프트 및 최신 AI 동향",
        "status": "커뮤니티"
    },
    "clien_today": {
        "name": "클리앙 인기글",
        "description": "클리앙 커뮤니티 주요 인기 게시글 실시간 알림",
        "status": "커뮤니티"
    },
    "korea_it_news": {
        "name": "IT 뉴스 모아보기",
        "description": "국내외 IT·스타트업·빅테크 주요 뉴스 브리핑",
        "status": "커뮤니티"
    },
    "modulabs": {
        "name": "모두의연구소",
        "description": "AI 연구 커뮤니티 모두의연구소(ModuLabs) 공지 및 소식",
        "status": "공식"
    },
    "yonhapnewsalert": {
        "name": "연합뉴스 속보",
        "description": "국가기간뉴스통신사 연합뉴스 실시간 주요 속보 알림",
        "status": "공식"
    },
    "bbc_korean": {
        "name": "BBC News 코리아",
        "description": "BBC 코리아 공식 뉴스 및 글로벌 심층 보도",
        "status": "공식"
    },
    "korea_economy": {
        "name": "한국경제 뉴스",
        "description": "한국경제 주요 기사 및 시장 경제 속보 요약",
        "status": "커뮤니티"
    },
    "fmkorea_hotdeal": {
        "name": "에펨코리아 핫딜 알리미",
        "description": "에펨코리아 알뜰구매 게시판 추천 핫딜 실시간 알림",
        "status": "커뮤니티"
    },
    "quasarzone_hotdeal": {
        "name": "퀘이사존 지름·할인정보",
        "description": "퀘이사존 지름/할인정보 게시판 인기 특가 알림",
        "status": "커뮤니티"
    },
    "ppomppu_hotdeal": {
        "name": "뽐뿌 핫딜 알리미",
        "description": "뽐뿌 국내 뽐뿌게시판 실시간 핫딜 알림",
        "status": "커뮤니티"
    },
    "alrimbot": {
        "name": "공공알리미 (재난·속보)",
        "description": "재난문자 및 주요 공공기관 알림 서비스",
        "status": "커뮤니티"
    },
    "sh_research": {
        "name": "신한투자증권 리서치",
        "description": "신한투자증권 발간 리포트 및 금융시장 시황 자료",
        "status": "기관/회사"
    },
    "kiwoom_research": {
        "name": "키움증권 리서치",
        "description": "키움증권 리서치센터 투자전략 및 기업분석 보고서",
        "status": "기관/회사"
    },
    "samsung_research": {
        "name": "삼성증권 리서치",
        "description": "삼성증권 글로벌 투자정보 및 데일리 리서치",
        "status": "기관/회사"
    },
    "coinness_kr": {
        "name": "코인니스 실시간 속보",
        "description": "암호화폐 투자 정보 플랫폼 코인니스 실시간 코인 뉴스",
        "status": "공식"
    },
    "bloomingbit": {
        "name": "블루밍비트",
        "description": "한국경제신문 블록체인·가상자산 전문 미디어",
        "status": "공식"
    },
    "xangle_official": {
        "name": "쟁글 (Xangle) 공식",
        "description": "가상자산 공시 및 온체인 데이터 인텔리전스 플랫폼 쟁글",
        "status": "공식"
    },
    "bithumb_official": {
        "name": "빗썸 공식 채널",
        "description": "빗썸 가상자산 거래소 주요 공지 및 이벤트 안내",
        "status": "공식"
    },
}

# Handles to remove (foreign or invalid)
REMOVE_HANDLES = {"twealth"}


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
