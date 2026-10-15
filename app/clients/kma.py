"""기상청 단기예보 클라이언트."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

RELEASE_TIMES = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
RELEASE_BUFFER_MINUTES = 15

SKY_LABELS = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY_LABELS = {"0": None, "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}


class KmaError(RuntimeError):
    """기상청 API 오류."""


@dataclass(frozen=True)
class WeatherSummary:
    max_temp: float | None
    min_temp: float | None
    pop: int | None  # 강수확률 %
    sky: str | None  # 맑음/구름많음/흐림
    precipitation: str | None  # 비/눈 등


def latest_bases(now: datetime, steps: int = 4) -> list[tuple[str, str]]:
    """최신 발표 시각부터 과거 순으로 (base_date, base_time) 후보를 만든다.

    발표 후 약 15분 뒤부터 조회 가능하므로 여유를 두고 계산한다.
    """
    reference = now - timedelta(minutes=RELEASE_BUFFER_MINUTES)
    releases: list[datetime] = []
    for day_offset in (2, 1, 0):
        day = (reference - timedelta(days=day_offset)).date()
        for release in RELEASE_TIMES:
            hour, minute = int(release[:2]), int(release[2:])
            releases.append(
                datetime.combine(day, time(hour, minute), tzinfo=reference.tzinfo)
            )
    available = [r for r in releases if r <= reference]
    return [
        (r.strftime("%Y%m%d"), r.strftime("%H%M")) for r in reversed(available[-steps:])
    ]


class KmaClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def _fetch(
        self, nx: int, ny: int, base_date: str, base_time: str
    ) -> list[dict[str, Any]]:
        response = await self._http.get(
            f"{BASE_URL}/getVilageFcst",
            params={
                "serviceKey": self._api_key,
                "dataType": "JSON",
                "numOfRows": 1000,
                "pageNo": 1,
                "base_date": base_date,
                "base_time": base_time,
                "nx": nx,
                "ny": ny,
            },
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise KmaError("기상청 응답이 JSON이 아닙니다") from exc

        header = payload.get("response", {}).get("header", {})
        code = str(header.get("resultCode", ""))
        if code == "03":  # NO_DATA — 아직 전파되지 않은 발표분
            return []
        if code != "00":
            raise KmaError(f"기상청 오류 {code}: {header.get('resultMsg', '')}")

        items = payload.get("response", {}).get("body", {}).get("items", {})
        return list(items.get("item", []))

    async def get_summary(self, nx: int, ny: int, now: datetime) -> WeatherSummary:
        rows: list[dict[str, Any]] = []
        for base_date, base_time in latest_bases(now):
            rows = await self._fetch(nx, ny, base_date, base_time)
            if rows:
                break
        if not rows:
            raise KmaError("단기예보 데이터가 없습니다")

        today = now.strftime("%Y%m%d")
        today_rows = [row for row in rows if str(row.get("fcstDate")) == today]

        def first_value(category: str) -> str | None:
            for row in today_rows:
                if row.get("category") == category:
                    return str(row.get("fcstValue"))
            return None

        max_temp = _to_float(first_value("TMX"))
        min_temp = _to_float(first_value("TMN"))

        pop_values = [
            _to_float(row.get("fcstValue"))
            for row in today_rows
            if row.get("category") == "POP"
        ]
        pops = [value for value in pop_values if value is not None]
        pop = int(max(pops)) if pops else None

        sky_code = _daytime_value(today_rows, "SKY")
        pty_code = _daytime_value(today_rows, "PTY")

        return WeatherSummary(
            max_temp=max_temp,
            min_temp=min_temp,
            pop=pop,
            sky=SKY_LABELS.get(sky_code or ""),
            precipitation=PTY_LABELS.get(pty_code or "0"),
        )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _daytime_value(rows: list[dict[str, Any]], category: str) -> str | None:
    """낮 시간대(11~15시) 대표값을 고른다."""
    for hour in ("1200", "1500", "1100", "0900"):
        for row in rows:
            if row.get("category") == category and str(row.get("fcstTime")) == hour:
                return str(row.get("fcstValue"))
    for row in rows:
        if row.get("category") == category:
            return str(row.get("fcstValue"))
    return None
