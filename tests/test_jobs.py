"""브리핑 발송 잡 테스트 (시간 고정)."""

from __future__ import annotations

from datetime import datetime as RealDatetime

from app.handlers import briefing as briefing_handlers
from tests.factories import make_context
from tests.test_briefing import clients

KST = briefing_handlers.KST


class FakeDatetime(RealDatetime):
    """특정 시각으로 고정된 datetime."""

    frozen: RealDatetime = RealDatetime(2026, 10, 15, 7, 30, tzinfo=KST)  # 목요일

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.frozen.replace(tzinfo=None)
        return cls.frozen.astimezone(tz)


def _ctx(repo):
    return make_context(bot_data={"repo": repo, "clients": clients()})


def _texts(ctx) -> list[str]:
    return [call.kwargs["text"] for call in ctx.bot.send_message.await_args_list]


def _freeze(monkeypatch, when: RealDatetime) -> None:
    FakeDatetime.frozen = when
    monkeypatch.setattr(briefing_handlers, "datetime", FakeDatetime)


async def test_설정시각에_발송과_하루1회(repo, monkeypatch):
    _freeze(monkeypatch, RealDatetime(2026, 10, 15, 7, 30, tzinfo=KST))  # 목요일
    await repo.set_enabled(100, True)
    await repo.set_time(100, "07:30")

    ctx = _ctx(repo)
    await briefing_handlers.briefing_job(ctx)

    assert ctx.bot.send_message.await_count == 1
    assert "아침 브리핑" in _texts(ctx)[0]
    assert (await repo.get(100)).last_sent_date == "20261015"

    await briefing_handlers.briefing_job(ctx)  # 같은 분 재실행
    assert ctx.bot.send_message.await_count == 1


async def test_다른_시각이면_발송없음(repo, monkeypatch):
    _freeze(monkeypatch, RealDatetime(2026, 10, 15, 8, 0, tzinfo=KST))
    await repo.set_enabled(100, True)
    await repo.set_time(100, "07:30")

    ctx = _ctx(repo)
    await briefing_handlers.briefing_job(ctx)
    assert ctx.bot.send_message.await_count == 0


async def test_꺼진_채팅은_발송없음(repo, monkeypatch):
    _freeze(monkeypatch, RealDatetime(2026, 10, 15, 7, 30, tzinfo=KST))
    await repo.set_enabled(100, False)
    await repo.set_time(100, "07:30")

    ctx = _ctx(repo)
    await briefing_handlers.briefing_job(ctx)
    assert ctx.bot.send_message.await_count == 0


async def test_주말은_기본_발송없음(repo, monkeypatch):
    _freeze(monkeypatch, RealDatetime(2026, 10, 17, 7, 30, tzinfo=KST))  # 토요일
    await repo.set_enabled(100, True)
    await repo.set_time(100, "07:30")

    ctx = _ctx(repo)
    await briefing_handlers.briefing_job(ctx)
    assert ctx.bot.send_message.await_count == 0

    await repo.set_weekend(100, True)
    await briefing_handlers.briefing_job(ctx)
    assert ctx.bot.send_message.await_count == 1


async def test_이미_보낸_날은_재발송없음(repo, monkeypatch):
    _freeze(monkeypatch, RealDatetime(2026, 10, 15, 7, 30, tzinfo=KST))
    await repo.set_enabled(100, True)
    await repo.set_time(100, "07:30")
    await repo.mark_sent(100, "20261015")

    ctx = _ctx(repo)
    await briefing_handlers.briefing_job(ctx)
    assert ctx.bot.send_message.await_count == 0
