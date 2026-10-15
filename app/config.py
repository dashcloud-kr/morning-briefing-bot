"""환경변수 로딩과 검증."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """필수 환경변수가 없거나 형식이 잘못된 경우."""


@dataclass(frozen=True)
class Config:
    bot_token: str
    data_go_kr_key: str
    koreaexim_api_key: str
    db_path: str = "data/bot.db"
    admin_chat_id: int | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        source = os.environ if env is None else env

        bot_token = source.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not bot_token:
            raise ConfigError(
                "TELEGRAM_BOT_TOKEN 환경변수가 필요합니다. "
                "@BotFather에서 봇을 만들고 토큰을 .env에 넣어주세요."
            )
        if ":" not in bot_token:
            raise ConfigError(
                "TELEGRAM_BOT_TOKEN 형식이 올바르지 않습니다 (예: 123456:ABC-DEF...)."
            )

        data_go_kr_key = source.get("DATA_GO_KR_KEY", "").strip()
        if not data_go_kr_key:
            raise ConfigError(
                "DATA_GO_KR_KEY 환경변수가 필요합니다. "
                "data.go.kr 에서 기상청·에어코리아 API 활용신청 후 발급받으세요."
            )

        koreaexim_api_key = source.get("KOREAEXIM_API_KEY", "").strip()
        if not koreaexim_api_key:
            raise ConfigError(
                "KOREAEXIM_API_KEY 환경변수가 필요합니다. "
                "koreaexim.go.kr 에서 환율 API 키를 신청하세요."
            )

        admin_raw = source.get("ADMIN_CHAT_ID", "").strip()
        admin_chat_id: int | None = None
        if admin_raw:
            try:
                admin_chat_id = int(admin_raw)
            except ValueError as exc:
                raise ConfigError("ADMIN_CHAT_ID는 숫자(chat id)여야 합니다.") from exc

        return cls(
            bot_token=bot_token,
            data_go_kr_key=data_go_kr_key,
            koreaexim_api_key=koreaexim_api_key,
            db_path=source.get("DB_PATH", "").strip() or "data/bot.db",
            admin_chat_id=admin_chat_id,
            log_level=source.get("LOG_LEVEL", "").strip().upper() or "INFO",
        )
