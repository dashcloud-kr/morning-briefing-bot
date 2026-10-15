"""morning-briefing-bot 엔트리포인트.

매일 아침 날씨·미세먼지·환율·뉴스를 한 번에 보내주는 24/7 텔레그램 봇.
"""

from __future__ import annotations

import logging

import httpx
from dotenv import load_dotenv
from telegram import BotCommand, Update

from app.bot import build_application
from app.clients.airkorea import AirKoreaClient
from app.clients.kma import KmaClient
from app.clients.koreaexim import KoreaEximClient
from app.clients.newsrss import NewsRssClient
from app.config import Config
from app.handlers import briefing
from app.services.briefing import BriefingClients
from app.services.repository import Repository

MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS briefing_settings (
      chat_id INTEGER PRIMARY KEY,
      enabled INTEGER NOT NULL DEFAULT 0,
      send_time TEXT NOT NULL DEFAULT '07:30',
      region TEXT NOT NULL DEFAULT '서울',
      weekend INTEGER NOT NULL DEFAULT 0,
      sections TEXT NOT NULL DEFAULT 'weather,dust,fx,news',
      last_sent_date TEXT
    );
    """,
]

COMMANDS = [
    BotCommand("briefing", "아침 브리핑 켜기/끄기"),
    BotCommand("settime", "발송 시각 설정"),
    BotCommand("region", "지역 설정"),
    BotCommand("sections", "섹션 선택 (날씨/미세먼지/환율/뉴스)"),
    BotCommand("weekend", "주말 발송 켜기/끄기"),
    BotCommand("preview", "지금 바로 미리보기"),
    BotCommand("settings", "내 설정 요약"),
    BotCommand("start", "시작"),
    BotCommand("help", "명령어 목록"),
    BotCommand("status", "봇 상태"),
    BotCommand("id", "내 chat id"),
]

CHECK_INTERVAL_SECONDS = 60


async def setup(application) -> None:
    config: Config = application.bot_data["config"]
    http = httpx.AsyncClient(timeout=20.0)
    application.bot_data["http"] = http
    application.bot_data["clients"] = BriefingClients(
        kma=KmaClient(http, config.data_go_kr_key),
        airkorea=AirKoreaClient(http, config.data_go_kr_key),
        koreaexim=KoreaEximClient(http, config.koreaexim_api_key),
        news=NewsRssClient(http),
    )
    application.bot_data["repo"] = Repository(application.bot_data["db"])


async def teardown(application) -> None:
    http: httpx.AsyncClient | None = application.bot_data.get("http")
    if http is not None:
        await http.aclose()


def main() -> None:
    load_dotenv()
    config = Config.from_env()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    application = build_application(
        config,
        migrations=MIGRATIONS,
        extra_handlers=briefing.handlers(),
        help_text=briefing.BRIEFING_HELP,
        commands=COMMANDS,
        setup=setup,
        teardown=teardown,
    )
    application.job_queue.run_repeating(
        briefing.briefing_job,
        interval=CHECK_INTERVAL_SECONDS,
        first=30,
        name="briefing",
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
