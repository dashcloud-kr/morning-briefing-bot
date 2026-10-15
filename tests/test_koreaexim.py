"""수출입은행 환율 클라이언트 테스트."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from app.clients.koreaexim import BASE_URL, FxError, KoreaEximClient

KST = ZoneInfo("Asia/Seoul")

ROWS = [
    {"result": 1, "cur_unit": "USD", "deal_bas_r": "1,340.5"},
    {"result": 1, "cur_unit": "JPY(100)", "deal_bas_r": "951.05"},
    {"result": 1, "cur_unit": "EUR", "deal_bas_r": "1,286.91"},
    {"result": 1, "cur_unit": "CNY", "deal_bas_r": "163.65"},
    {"result": 1, "cur_unit": "AUD", "deal_bas_r": "836.28"},
]


@pytest.fixture
def http():
    return httpx.AsyncClient()


@respx.mock
async def test_환율_파싱과_통화_필터(http):
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=ROWS))
    client = KoreaEximClient(http, "test-key")
    rates = await client.get_rates(datetime(2026, 10, 15, 12, 0, tzinfo=KST))

    assert rates == {"USD": 1340.5, "JPY(100)": 951.05, "EUR": 1286.91, "CNY": 163.65}
    assert "AUD" not in rates
    params = route.calls[0].request.url.params
    assert params["authkey"] == "test-key"
    assert params["data"] == "AP01"


@respx.mock
async def test_빈_응답이면_이전_영업일로_폴백(http):
    route = respx.get(BASE_URL).mock(
        side_effect=[
            httpx.Response(200, json=[]),  # 오늘(11시 이전)
            httpx.Response(200, json=[]),  # 어제(휴장)
            httpx.Response(200, json=ROWS),  # 그제
        ]
    )
    client = KoreaEximClient(http, "test-key")
    rates = await client.get_rates(datetime(2026, 10, 15, 9, 0, tzinfo=KST))

    assert rates["USD"] == 1340.5
    assert route.calls[2].request.url.params["searchdate"] == "20261013"


@respx.mock
async def test_모두_비면_에러(http):
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json=[]))
    client = KoreaEximClient(http, "test-key")
    with pytest.raises(FxError):
        await client.get_rates(datetime(2026, 10, 15, 9, 0, tzinfo=KST))


@respx.mock
async def test_필요_통화가_없으면_에러(http):
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=[{"cur_unit": "AUD", "deal_bas_r": "1"}])
    )
    client = KoreaEximClient(http, "test-key")
    with pytest.raises(FxError):
        await client.get_rates(datetime(2026, 10, 15, 12, 0, tzinfo=KST))


@respx.mock
async def test_리스트가_아니면_에러(http):
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"result": 3}))
    client = KoreaEximClient(http, "test-key")
    with pytest.raises(FxError):
        await client.get_rates(datetime(2026, 10, 15, 12, 0, tzinfo=KST))
