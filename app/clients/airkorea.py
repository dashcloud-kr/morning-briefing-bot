"""에어코리아 대기오염정보 클라이언트."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc"
RETRY_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2.0


class AirKoreaError(RuntimeError):
    """에어코리아 API 오류."""


@dataclass(frozen=True)
class DustSummary:
    pm10: float | None
    pm10_grade: str | None
    pm25: float | None
    pm25_grade: str | None


def pm10_grade(value: float) -> str:
    if value <= 30:
        return "좋음"
    if value <= 80:
        return "보통"
    if value <= 150:
        return "나쁨"
    return "매우나쁨"


def pm25_grade(value: float) -> str:
    if value <= 15:
        return "좋음"
    if value <= 35:
        return "보통"
    if value <= 75:
        return "나쁨"
    return "매우나쁨"


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)


class AirKoreaClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def get_dust(self, sido: str) -> DustSummary:
        last_error: Exception | None = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = await self._http.get(
                    f"{BASE_URL}/getCtprvnRltmMesureDnsty",
                    params={
                        "serviceKey": self._api_key,
                        "returnType": "json",
                        "numOfRows": 100,
                        "pageNo": 1,
                        "sidoName": sido,
                        "ver": "1.0",
                    },
                )
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:  # 에어코리아는 간헐적으로 느리다
                last_error = exc
                if attempt < RETRY_ATTEMPTS:
                    logger.warning("에어코리아 재시도 (%d/%d)", attempt, RETRY_ATTEMPTS)
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        else:
            assert last_error is not None
            raise last_error

        payload = response.json()

        header = payload.get("response", {}).get("header", {})
        code = str(header.get("resultCode", ""))
        if code != "00":
            raise AirKoreaError(f"에어코리아 오류 {code}: {header.get('resultMsg', '')}")

        items = payload.get("response", {}).get("body", {}).get("items", [])
        pm10_values = _numeric([item.get("pm10Value") for item in items])
        pm25_values = _numeric([item.get("pm25Value") for item in items])

        pm10 = _average(pm10_values)
        pm25 = _average(pm25_values)
        return DustSummary(
            pm10=pm10,
            pm10_grade=pm10_grade(pm10) if pm10 is not None else None,
            pm25=pm25,
            pm25_grade=pm25_grade(pm25) if pm25 is not None else None,
        )


def _numeric(values: list[Any]) -> list[float]:
    numbers: list[float] = []
    for value in values:
        try:
            numbers.append(float(str(value).strip()))
        except (TypeError, ValueError):
            continue
    return numbers
