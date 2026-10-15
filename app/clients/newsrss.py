"""구글 뉴스 RSS 헤드라인 클라이언트."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

NEWS_RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
USER_AGENT = "Mozilla/5.0 (compatible; dashcloud-briefing-bot/1.0)"


class NewsError(RuntimeError):
    """뉴스 RSS 오류."""


class NewsRssClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def get_headlines(self, limit: int = 5) -> list[str]:
        response = await self._http.get(NEWS_RSS_URL, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise NewsError("뉴스 RSS 파싱 실패") from exc

        headlines: list[str] = []
        for element in root.iter("item"):
            title = (element.findtext("title") or "").strip()
            if not title:
                continue
            headlines.append(title)
            if len(headlines) >= limit:
                break
        if not headlines:
            raise NewsError("뉴스 헤드라인이 없습니다")
        return headlines
