"""한국수출입은행 환율 클라이언트."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"

DISPLAY_ORDER = ["USD", "JPY(100)", "EUR", "CNY"]
LOOKBACK_DAYS = 6


class FxError(RuntimeError):
    """환율 API 오류."""


class KoreaEximClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def _fetch(self, searchdate: str) -> list[dict[str, Any]]:
        response = await self._http.get(
            BASE_URL,
            params={"authkey": self._api_key, "searchdate": searchdate, "data": "AP01"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise FxError("환율 API 응답 형식이 올바르지 않습니다")
        return payload

    async def get_rates(self, now: datetime) -> dict[str, float]:
        """영업일 기준 최신 환율 (매매기준율). 주말·11시 이전은 이전 영업일로 폴백."""
        rows: list[dict[str, Any]] = []
        for offset in range(LOOKBACK_DAYS):
            searchdate = (now - timedelta(days=offset)).strftime("%Y%m%d")
            rows = await self._fetch(searchdate)
            if rows:
                break
        if not rows:
            raise FxError("환율 데이터가 없습니다")

        found: dict[str, float] = {}
        for row in rows:
            unit = str(row.get("cur_unit", "")).strip()
            if unit not in DISPLAY_ORDER:
                continue
            try:
                found[unit] = float(str(row.get("deal_bas_r", "")).replace(",", ""))
            except ValueError:
                continue
        if not found:
            raise FxError("필요한 통화 환율이 없습니다")
        return {unit: found[unit] for unit in DISPLAY_ORDER if unit in found}
