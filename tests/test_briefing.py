"""지역 매핑·브리핑 조립 테스트."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.clients.airkorea import AirKoreaError, DustSummary
from app.clients.kma import KmaError, WeatherSummary
from app.services.briefing import (
    ALL_SECTIONS,
    BriefingClients,
    build_briefing,
    format_dust,
    format_fx,
    format_news,
    format_weather,
    parse_sections,
)
from app.services.regions import REGIONS, resolve_region

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 10, 15, 7, 30, tzinfo=KST)


def test_지역_매핑():
    seoul = resolve_region("서울")
    assert seoul is not None
    assert seoul.nx == 60
    assert seoul.ny == 127
    assert seoul.sido == "서울"

    assert resolve_region("제주") is not None
    assert resolve_region("  수원 ") is not None
    assert resolve_region("평양") is None
    assert len(REGIONS) >= 15


def test_섹션_파싱():
    assert parse_sections("weather,dust") == ["weather", "dust"]
    assert parse_sections("날씨") is None
    assert parse_sections("weather,unknown") is None
    assert parse_sections("weather, weather") == ["weather"]
    assert parse_sections("") is None


def test_포맷_함수():
    weather = format_weather(WeatherSummary(24.0, 13.0, 60, "맑음", None))
    assert weather == "날씨: 맑음 · 최고 24° / 최저 13° · 강수 60%"

    weather_none = format_weather(WeatherSummary(None, None, None, None, None))
    assert "정보 없음" in weather_none

    dust = format_dust(DustSummary(20.0, "좋음", 11.0, "좋음"))
    assert dust == "미세먼지: PM10 20 좋음 · PM2.5 11 좋음"

    fx = format_fx({"USD": 1340.5, "JPY(100)": 951.05})
    assert fx == "환율: USD 1,340.50 · JPY(100) 951.05"

    news = format_news(["헤드라인1", "헤드라인2"])
    assert news == "주요 뉴스\n· 헤드라인1\n· 헤드라인2"


class StubKma:
    async def get_summary(self, nx, ny, now):
        return WeatherSummary(24.0, 13.0, 60, "맑음", None)


class StubDust:
    async def get_dust(self, sido):
        return DustSummary(20.0, "좋음", 11.0, "좋음")


class StubFx:
    async def get_rates(self, now):
        return {"USD": 1340.5}


class StubNews:
    async def get_headlines(self, limit=5):
        return ["헤드라인1", "헤드라인2"]


class FailingKma:
    async def get_summary(self, nx, ny, now):
        raise KmaError("boom")


def clients(kma=None) -> BriefingClients:
    return BriefingClients(
        kma=kma or StubKma(),
        airkorea=StubDust(),
        koreaexim=StubFx(),
        news=StubNews(),
    )


async def test_브리핑_전체_섹션():
    chunks = await build_briefing(
        region_name="서울",
        sections=ALL_SECTIONS,
        clients=clients(),
        now=NOW,
    )
    text = "\n".join(chunks)
    assert "아침 브리핑 (10/15) — 서울" in text
    assert "날씨: 맑음" in text
    assert "미세먼지: PM10 20 좋음" in text
    assert "환율: USD 1,340.50" in text
    assert "주요 뉴스" in text
    assert "· 헤드라인1" in text


async def test_섹션_일부만():
    chunks = await build_briefing(
        region_name="부산",
        sections=["weather", "news"],
        clients=clients(),
        now=NOW,
    )
    text = "\n".join(chunks)
    assert "날씨" in text
    assert "미세먼지" not in text
    assert "환율" not in text


async def test_섹션_실패는_격리():
    chunks = await build_briefing(
        region_name="서울",
        sections=["weather", "fx"],
        clients=clients(kma=FailingKma()),
        now=NOW,
    )
    text = "\n".join(chunks)
    assert "날씨: 일시적으로 조회할 수 없습니다" in text
    assert "환율: USD 1,340.50" in text  # 다른 섹션은 정상


async def test_알수없는_지역은_서울로():
    chunks = await build_briefing(
        region_name="없는지역",
        sections=["weather"],
        clients=clients(),
        now=NOW,
    )
    assert "서울" in chunks[0]


class FailingDust:
    async def get_dust(self, sido):
        raise AirKoreaError("boom")


async def test_미세먼지_실패_격리():
    briefing_clients = clients()
    briefing_clients.airkorea = FailingDust()
    chunks = await build_briefing(
        region_name="서울",
        sections=["dust"],
        clients=briefing_clients,
        now=NOW,
    )
    assert "미세먼지: 일시적으로 조회할 수 없습니다" in chunks[0]
