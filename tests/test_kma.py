"""기상청 클라이언트 테스트."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from app.clients.kma import BASE_URL, KmaClient, KmaError, latest_bases

KST = ZoneInfo("Asia/Seoul")


def test_최신_발표_후보_순서():
    now = datetime(2026, 10, 15, 10, 30, tzinfo=KST)
    bases = latest_bases(now)
    assert bases[0] == ("20261015", "0800")
    assert bases[1] == ("20261015", "0500")
    assert bases[-1] == ("20261014", "2300")


def test_새벽에는_전날_발표분부터():
    now = datetime(2026, 10, 15, 1, 0, tzinfo=KST)
    bases = latest_bases(now)
    assert bases[0] == ("20261014", "2300")
    assert bases[1] == ("20261014", "2000")


def _item(category: str, value: str, time: str = "1200", date: str = "20261015") -> dict:
    return {
        "category": category,
        "fcstValue": value,
        "fcstTime": time,
        "fcstDate": date,
        "baseDate": "20261015",
        "baseTime": "0800",
        "nx": 60,
        "ny": 127,
    }


PAYLOAD = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
        "body": {
            "items": {
                "item": [
                    _item("TMX", "24"),
                    _item("TMN", "13"),
                    _item("POP", "10", time="0900"),
                    _item("POP", "60", time="1500"),
                    _item("SKY", "1"),
                    _item("PTY", "0"),
                ]
            }
        },
    }
}

NO_DATA_PAYLOAD = {
    "response": {"header": {"resultCode": "03", "resultMsg": "NO_DATA"}}
}


@pytest.fixture
def http():
    return httpx.AsyncClient()


@respx.mock
async def test_요약_파싱(http):
    respx.get(f"{BASE_URL}/getVilageFcst").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    client = KmaClient(http, "test-key")
    summary = await client.get_summary(60, 127, datetime(2026, 10, 15, 10, 30, tzinfo=KST))

    assert summary.max_temp == 24
    assert summary.min_temp == 13
    assert summary.pop == 60  # 하루 중 최대 강수확률
    assert summary.sky == "맑음"
    assert summary.precipitation is None


@respx.mock
async def test_NO_DATA면_이전_발표분으로_폴백(http):
    route = respx.get(f"{BASE_URL}/getVilageFcst").mock(
        side_effect=[
            httpx.Response(200, json=NO_DATA_PAYLOAD),
            httpx.Response(200, json=PAYLOAD),
        ]
    )
    client = KmaClient(http, "test-key")
    summary = await client.get_summary(60, 127, datetime(2026, 10, 15, 10, 30, tzinfo=KST))

    assert summary.max_temp == 24
    assert route.calls[1].request.url.params["base_time"] == "0500"


@respx.mock
async def test_모두_NO_DATA면_에러(http):
    respx.get(f"{BASE_URL}/getVilageFcst").mock(
        return_value=httpx.Response(200, json=NO_DATA_PAYLOAD)
    )
    client = KmaClient(http, "test-key")
    with pytest.raises(KmaError):
        await client.get_summary(60, 127, datetime(2026, 10, 15, 10, 30, tzinfo=KST))


@respx.mock
async def test_오류코드는_예외(http):
    payload = {"response": {"header": {"resultCode": "30", "resultMsg": "키 오류"}}}
    respx.get(f"{BASE_URL}/getVilageFcst").mock(return_value=httpx.Response(200, json=payload))
    client = KmaClient(http, "bad")
    with pytest.raises(KmaError, match="30"):
        await client.get_summary(60, 127, datetime(2026, 10, 15, 10, 30, tzinfo=KST))


@respx.mock
async def test_비JSON_응답은_예외(http):
    respx.get(f"{BASE_URL}/getVilageFcst").mock(
        return_value=httpx.Response(200, text="<html>error</html>")
    )
    client = KmaClient(http, "bad")
    with pytest.raises(KmaError):
        await client.get_summary(60, 127, datetime(2026, 10, 15, 10, 30, tzinfo=KST))
