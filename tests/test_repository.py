"""Repository (브리핑 설정) 테스트."""

from __future__ import annotations

from app.services.briefing import ALL_SECTIONS


async def test_기본값(repo):
    settings = await repo.get(100)
    assert settings.enabled is False
    assert settings.send_time == "07:30"
    assert settings.region == "서울"
    assert settings.weekend is False
    assert settings.sections == ALL_SECTIONS
    assert settings.last_sent_date is None


async def test_설정_변경과_유지(repo):
    await repo.set_enabled(100, True)
    await repo.set_time(100, "06:45")
    await repo.set_region(100, "수원")
    await repo.set_weekend(100, True)
    await repo.set_sections(100, ["weather", "news"])

    settings = await repo.get(100)
    assert settings.enabled is True
    assert settings.send_time == "06:45"
    assert settings.region == "수원"
    assert settings.weekend is True
    assert settings.sections == ["weather", "news"]

    await repo.mark_sent(100, "20261015")
    assert (await repo.get(100)).last_sent_date == "20261015"

    # 다른 설정은 유지된 채 부분 갱신
    await repo.set_time(100, "07:00")
    settings = await repo.get(100)
    assert settings.send_time == "07:00"
    assert settings.region == "수원"
    assert settings.sections == ["weather", "news"]


async def test_켜진_것만_조회(repo):
    await repo.set_enabled(100, True)
    await repo.set_enabled(200, False)
    await repo.set_enabled(300, True)

    enabled = await repo.all_enabled()
    assert sorted(s.chat_id for s in enabled) == [100, 300]


async def test_마이그레이션_재적용_안전(tmp_path):
    from app.db import Database
    from app.services.repository import Repository
    from bot import MIGRATIONS

    path = tmp_path / "again.db"
    first = Database(path)
    await first.connect(MIGRATIONS)
    await Repository(first).set_time(100, "06:00")
    await first.close()

    second = Database(path)
    await second.connect(MIGRATIONS)
    try:
        assert (await Repository(second).get(100)).send_time == "06:00"
    finally:
        await second.close()
