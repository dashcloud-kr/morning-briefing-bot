"""Config 로딩/검증 테스트."""

from __future__ import annotations

import pytest

from app.config import Config, ConfigError

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF",
    "DATA_GO_KR_KEY": "data-key",
    "KOREAEXIM_API_KEY": "fx-key",
}


def test_from_env_필수값과_기본값():
    config = Config.from_env(BASE_ENV)
    assert config.bot_token == "123456:ABC-DEF"
    assert config.data_go_kr_key == "data-key"
    assert config.koreaexim_api_key == "fx-key"
    assert config.db_path == "data/bot.db"
    assert config.log_level == "INFO"


def test_from_env_토큰_없으면_에러():
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        Config.from_env({"DATA_GO_KR_KEY": "k", "KOREAEXIM_API_KEY": "k"})


def test_from_env_토큰_형식_검증():
    with pytest.raises(ConfigError, match="형식"):
        Config.from_env({**BASE_ENV, "TELEGRAM_BOT_TOKEN": "bad"})


def test_from_env_공공데이터키_없으면_에러():
    with pytest.raises(ConfigError, match="DATA_GO_KR_KEY"):
        Config.from_env({"TELEGRAM_BOT_TOKEN": "1:A", "KOREAEXIM_API_KEY": "k"})


def test_from_env_환율키_없으면_에러():
    with pytest.raises(ConfigError, match="KOREAEXIM_API_KEY"):
        Config.from_env({"TELEGRAM_BOT_TOKEN": "1:A", "DATA_GO_KR_KEY": "k"})


def test_from_env_admin_chat_id_파싱():
    config = Config.from_env({**BASE_ENV, "ADMIN_CHAT_ID": "-100123"})
    assert config.admin_chat_id == -100123


def test_from_env_admin_chat_id_숫자_아니면_에러():
    with pytest.raises(ConfigError, match="ADMIN_CHAT_ID"):
        Config.from_env({**BASE_ENV, "ADMIN_CHAT_ID": "abc"})


def test_from_env_로그레벨_대문자_정규화():
    config = Config.from_env({**BASE_ENV, "LOG_LEVEL": "debug"})
    assert config.log_level == "DEBUG"
