"""브리핑 명령어 핸들러 테스트."""

from __future__ import annotations

from app.handlers import briefing as briefing_handlers
from tests.factories import make_context, make_message_update
from tests.test_briefing import clients


def _ctx(update, repo, briefing_clients=None):
    message = update.effective_message
    args = message.text.split()[1:] if message is not None and message.text else []
    return make_context(
        args=args,
        bot_data={"repo": repo, "clients": briefing_clients or clients()},
    )


def _texts(update) -> list[str]:
    return [call.kwargs["text"] for call in update.get_bot().send_message.await_args_list]


def _last(update) -> str:
    return _texts(update)[-1]


async def test_briefing_상태와_켜기_끄기(repo):
    update = make_message_update("/briefing")
    await briefing_handlers.cmd_briefing(update, _ctx(update, repo))
    assert "꺼짐" in _last(update)

    update = make_message_update("/briefing on")
    await briefing_handlers.cmd_briefing(update, _ctx(update, repo))
    assert "켰습니다" in _last(update)
    assert (await repo.get(100)).enabled is True

    update = make_message_update("/briefing off")
    await briefing_handlers.cmd_briefing(update, _ctx(update, repo))
    assert (await repo.get(100)).enabled is False


async def test_settime(repo):
    update = make_message_update("/settime 25:99")
    await briefing_handlers.cmd_settime(update, _ctx(update, repo))
    assert "HH:MM" in _last(update)

    update = make_message_update("/settime 06:45")
    await briefing_handlers.cmd_settime(update, _ctx(update, repo))
    assert "06:45" in _last(update)
    assert (await repo.get(100)).send_time == "06:45"


async def test_region(repo):
    update = make_message_update("/region 평양")
    await briefing_handlers.cmd_region(update, _ctx(update, repo))
    assert "지원하지 않는" in _last(update)

    update = make_message_update("/region 부산")
    await briefing_handlers.cmd_region(update, _ctx(update, repo))
    assert "부산" in _last(update)
    assert (await repo.get(100)).region == "부산"


async def test_sections(repo):
    update = make_message_update("/sections")
    await briefing_handlers.cmd_sections(update, _ctx(update, repo))
    assert "weather(날씨)" in _last(update)

    update = make_message_update("/sections weather,news")
    await briefing_handlers.cmd_sections(update, _ctx(update, repo))
    assert (await repo.get(100)).sections == ["weather", "news"]

    update = make_message_update("/sections 잘못된섹션")
    await briefing_handlers.cmd_sections(update, _ctx(update, repo))
    assert "섹션 이름을 확인하세요" in _last(update)


async def test_weekend(repo):
    update = make_message_update("/weekend on")
    await briefing_handlers.cmd_weekend(update, _ctx(update, repo))
    assert (await repo.get(100)).weekend is True

    update = make_message_update("/weekend off")
    await briefing_handlers.cmd_weekend(update, _ctx(update, repo))
    assert (await repo.get(100)).weekend is False


async def test_preview_즉시_발송(repo):
    update = make_message_update("/preview")
    ctx = _ctx(update, repo)
    await briefing_handlers.cmd_preview(update, ctx)
    texts = [call.kwargs["text"] for call in ctx.bot.send_message.await_args_list]
    assert len(texts) == 1
    assert "아침 브리핑" in texts[0]
    assert "날씨: 맑음" in texts[0]
    assert "주요 뉴스" in texts[0]


async def test_settings_요약(repo):
    await repo.set_enabled(100, True)
    await repo.set_time(100, "06:30")
    await repo.set_region(100, "대전")
    await repo.set_sections(100, ["weather"])

    update = make_message_update("/settings")
    await briefing_handlers.cmd_settings(update, _ctx(update, repo))
    text = _last(update)
    assert "06:30" in text
    assert "대전" in text
    assert "weather(날씨)" in text
