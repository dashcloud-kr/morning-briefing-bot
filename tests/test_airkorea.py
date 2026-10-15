"""에어코리아 클라이언트 테스트."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.clients.airkorea import (
    BASE_URL,
    AirKoreaClient,
    AirKoreaError,
    pm10_grade,
    pm25_grade,
)

PAYLOAD = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "정상"},
        "body": {
            "items": [
                {"pm10Value": "20", "pm25Value": "11"},
                {"pm10Value": "40", "pm25Value": "20"},
                {"pm10Value": "-", "pm25Value": ""},
                {"pm10Value": None, "pm25Value": "25"},
            ]
        },
    }
}


def test_등급_경계():
    assert pm10_grade(30) == "좋음"
    assert pm10_grade(31) == "보통"
    assert pm10_grade(80) == "보통"
    assert pm10_grade(81) == "나쁨"
    assert pm10_grade(151) == "매우나쁨"

    assert pm25_grade(15) == "좋음"
    assert pm25_grade(16) == "보통"
    assert pm25_grade(36) == "나쁨"
    assert pm25_grade(76) == "매우나쁨"


@pytest.fixture
def http():
    return httpx.AsyncClient()


@respx.mock
async def test_시도_평균_파싱(http):
    route = respx.get(f"{BASE_URL}/getCtprvnRltmMesureDnsty").mock(
        return_value=httpx.Response(200, json=PAYLOAD)
    )
    client = AirKoreaClient(http, "test-key")
    dust = await client.get_dust("서울")

    assert dust.pm10 == 30.0  # (20+40)/2
    assert dust.pm10_grade == "좋음"
    assert dust.pm25 == 18.7  # (11+20+25)/3 ≈ 18.67 → 18.7
    assert dust.pm25_grade == "보통"

    params = route.calls[0].request.url.params
    assert params["sidoName"] == "서울"
    assert params["ver"] == "1.0"


@respx.mock
async def test_오류코드는_예외(http):
    payload = {"response": {"header": {"resultCode": "30", "resultMsg": "키 오류"}}}
    respx.get(f"{BASE_URL}/getCtprvnRltmMesureDnsty").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = AirKoreaClient(http, "bad")
    with pytest.raises(AirKoreaError):
        await client.get_dust("서울")


@respx.mock
async def test_타임아웃은_재시도(http, monkeypatch):
    import app.clients.airkorea as airkorea_module

    monkeypatch.setattr(airkorea_module, "RETRY_DELAY_SECONDS", 0)
    route = respx.get(f"{BASE_URL}/getCtprvnRltmMesureDnsty").mock(
        side_effect=[
            httpx.ReadTimeout("timeout"),
            httpx.Response(200, json=PAYLOAD),
        ]
    )
    client = AirKoreaClient(http, "test-key")
    dust = await client.get_dust("서울")
    assert dust.pm10 == 30.0
    assert route.calls.call_count == 2


@respx.mock
async def test_측정값이_없으면_None(http):
    payload = {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": [{"pm10Value": "-", "pm25Value": ""}]},
        }
    }
    respx.get(f"{BASE_URL}/getCtprvnRltmMesureDnsty").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = AirKoreaClient(http, "test-key")
    dust = await client.get_dust("서울")
    assert dust.pm10 is None
    assert dust.pm10_grade is None
