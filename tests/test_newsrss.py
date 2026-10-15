"""뉴스 RSS 클라이언트 테스트."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.clients.newsrss import NEWS_RSS_URL, NewsError, NewsRssClient

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>주요 뉴스 - Google 뉴스</title>
<item><title>첫 번째 헤드라인</title><link>https://news.google.com/1</link></item>
<item><title>두 번째 헤드라인</title><link>https://news.google.com/2</link></item>
<item><title>세 번째 헤드라인</title><link>https://news.google.com/3</link></item>
<item><title></title><link>https://news.google.com/4</link></item>
<item><title>네 번째 헤드라인</title><link>https://news.google.com/5</link></item>
</channel>
</rss>"""


@pytest.fixture
def http():
    return httpx.AsyncClient()


@respx.mock
async def test_헤드라인_파싱과_제한(http):
    respx.get(NEWS_RSS_URL).mock(return_value=httpx.Response(200, text=RSS))
    client = NewsRssClient(http)
    headlines = await client.get_headlines(limit=3)
    assert headlines == ["첫 번째 헤드라인", "두 번째 헤드라인", "세 번째 헤드라인"]


@respx.mock
async def test_빈_제목은_건너뜀(http):
    respx.get(NEWS_RSS_URL).mock(return_value=httpx.Response(200, text=RSS))
    client = NewsRssClient(http)
    headlines = await client.get_headlines(limit=5)
    assert len(headlines) == 4
    assert "" not in headlines


@respx.mock
async def test_파싱_실패는_예외(http):
    respx.get(NEWS_RSS_URL).mock(return_value=httpx.Response(200, text="not xml"))
    client = NewsRssClient(http)
    with pytest.raises(NewsError):
        await client.get_headlines()


@respx.mock
async def test_아이템이_없으면_예외(http):
    empty = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    respx.get(NEWS_RSS_URL).mock(return_value=httpx.Response(200, text=empty))
    client = NewsRssClient(http)
    with pytest.raises(NewsError):
        await client.get_headlines()
