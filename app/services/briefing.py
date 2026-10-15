"""브리핑 조립 (섹션별 실패는 격리)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.clients.airkorea import AirKoreaClient, AirKoreaError, DustSummary
from app.clients.kma import KmaClient, KmaError, WeatherSummary
from app.clients.koreaexim import FxError, KoreaEximClient
from app.clients.newsrss import NewsError, NewsRssClient
from app.services.regions import resolve_region
from app.utils.text import chunk_text

logger = logging.getLogger(__name__)

SECTION_LABELS = {
    "weather": "날씨",
    "dust": "미세먼지",
    "fx": "환율",
    "news": "주요 뉴스",
}
ALL_SECTIONS = list(SECTION_LABELS.keys())


@dataclass
class BriefingClients:
    kma: KmaClient
    airkorea: AirKoreaClient
    koreaexim: KoreaEximClient
    news: NewsRssClient


def parse_sections(raw: str) -> list[str] | None:
    """'weather,dust,fx,news' → 검증된 섹션 목록. 잘못된 값이 있으면 None."""
    parts = [part.strip().lower() for part in raw.replace(" ", ",").split(",")]
    sections = [part for part in parts if part]
    if not sections:
        return None
    if any(section not in SECTION_LABELS for section in sections):
        return None
    return list(dict.fromkeys(sections))


def format_weather(summary: WeatherSummary) -> str:
    parts: list[str] = []
    if summary.sky or summary.precipitation:
        parts.append(summary.precipitation or summary.sky or "")
    if summary.max_temp is not None or summary.min_temp is not None:
        high = f"{summary.max_temp:.0f}" if summary.max_temp is not None else "-"
        low = f"{summary.min_temp:.0f}" if summary.min_temp is not None else "-"
        parts.append(f"최고 {high}° / 최저 {low}°")
    if summary.pop is not None:
        parts.append(f"강수 {summary.pop}%")
    body = " · ".join(part for part in parts if part)
    return f"날씨: {body}" if body else "날씨: 정보 없음"


def format_dust(summary: DustSummary) -> str:
    parts: list[str] = []
    if summary.pm10 is not None:
        parts.append(f"PM10 {summary.pm10:g} {summary.pm10_grade or ''}".strip())
    if summary.pm25 is not None:
        parts.append(f"PM2.5 {summary.pm25:g} {summary.pm25_grade or ''}".strip())
    body = " · ".join(parts)
    return f"미세먼지: {body}" if body else "미세먼지: 정보 없음"


def format_fx(rates: dict[str, float]) -> str:
    parts = [f"{unit} {value:,.2f}" for unit, value in rates.items()]
    return "환율: " + " · ".join(parts) if parts else "환율: 정보 없음"


def format_news(headlines: list[str]) -> str:
    lines = ["주요 뉴스"]
    lines.extend(f"· {headline}" for headline in headlines)
    return "\n".join(lines)


async def build_briefing(
    *,
    region_name: str,
    sections: list[str],
    clients: BriefingClients,
    now: datetime,
) -> list[str]:
    """브리핑 메시지 청크를 만든다. 섹션별 오류는 해당 섹션만 건너뛴다."""
    region = resolve_region(region_name)
    if region is None:
        region = resolve_region("서울")
        region_name = "서울"
    assert region is not None

    blocks: list[str] = [f"아침 브리핑 ({now:%m/%d}) — {region_name}"]

    for section in sections:
        label = SECTION_LABELS[section]
        try:
            if section == "weather":
                summary = await clients.kma.get_summary(region.nx, region.ny, now)
                blocks.append(format_weather(summary))
            elif section == "dust":
                dust = await clients.airkorea.get_dust(region.sido)
                blocks.append(format_dust(dust))
            elif section == "fx":
                rates = await clients.koreaexim.get_rates(now)
                ordered = {unit: rates[unit] for unit in rates}
                blocks.append(format_fx(ordered))
            elif section == "news":
                headlines = await clients.news.get_headlines(5)
                blocks.append(format_news(headlines))
        except (KmaError, AirKoreaError, FxError, NewsError):
            logger.warning("브리핑 섹션 실패: %s", section, exc_info=True)
            blocks.append(f"{label}: 일시적으로 조회할 수 없습니다")
        except httpx.HTTPError:
            logger.warning("브리핑 섹션 통신 실패: %s", section, exc_info=True)
            blocks.append(f"{label}: 일시적으로 조회할 수 없습니다")

    return chunk_text("\n\n".join(blocks))
