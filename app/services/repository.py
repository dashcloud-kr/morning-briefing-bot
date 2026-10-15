"""SQLite 저장소 (브리핑 설정)."""

from __future__ import annotations

from dataclasses import dataclass

from app.db import Database
from app.services.briefing import ALL_SECTIONS
from app.services.regions import DEFAULT_REGION

DEFAULT_TIME = "07:30"


@dataclass(frozen=True)
class BriefingSettings:
    chat_id: int
    enabled: bool
    send_time: str
    region: str
    weekend: bool
    sections: list[str]
    last_sent_date: str | None


def _parse_sections(raw: str | None) -> list[str]:
    if not raw:
        return list(ALL_SECTIONS)
    sections = [part.strip() for part in raw.split(",") if part.strip()]
    return sections or list(ALL_SECTIONS)


def _row_to_settings(row) -> BriefingSettings:
    return BriefingSettings(
        chat_id=int(row["chat_id"]),
        enabled=bool(row["enabled"]),
        send_time=str(row["send_time"]),
        region=str(row["region"]),
        weekend=bool(row["weekend"]),
        sections=_parse_sections(row["sections"]),
        last_sent_date=(
            str(row["last_sent_date"]) if row["last_sent_date"] is not None else None
        ),
    )


class Repository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def _upsert(self, chat_id: int, column: str, value) -> None:
        await self._db.execute(
            f"INSERT INTO briefing_settings (chat_id, {column}) VALUES (?, ?) "
            f"ON CONFLICT (chat_id) DO UPDATE SET {column} = excluded.{column}",
            (chat_id, value),
        )

    async def get(self, chat_id: int) -> BriefingSettings:
        row = await self._db.fetchone(
            "SELECT chat_id, enabled, send_time, region, weekend, sections, last_sent_date "
            "FROM briefing_settings WHERE chat_id = ?",
            (chat_id,),
        )
        if row is None:
            return BriefingSettings(
                chat_id=chat_id,
                enabled=False,
                send_time=DEFAULT_TIME,
                region=DEFAULT_REGION,
                weekend=False,
                sections=list(ALL_SECTIONS),
                last_sent_date=None,
            )
        return _row_to_settings(row)

    async def set_enabled(self, chat_id: int, enabled: bool) -> None:
        await self._upsert(chat_id, "enabled", 1 if enabled else 0)

    async def set_time(self, chat_id: int, send_time: str) -> None:
        await self._upsert(chat_id, "send_time", send_time)

    async def set_region(self, chat_id: int, region: str) -> None:
        await self._upsert(chat_id, "region", region)

    async def set_weekend(self, chat_id: int, weekend: bool) -> None:
        await self._upsert(chat_id, "weekend", 1 if weekend else 0)

    async def set_sections(self, chat_id: int, sections: list[str]) -> None:
        await self._upsert(chat_id, "sections", ",".join(sections))

    async def mark_sent(self, chat_id: int, ymd: str) -> None:
        await self._upsert(chat_id, "last_sent_date", ymd)

    async def all_enabled(self) -> list[BriefingSettings]:
        rows = await self._db.fetchall(
            "SELECT chat_id, enabled, send_time, region, weekend, sections, last_sent_date "
            "FROM briefing_settings WHERE enabled = 1"
        )
        return [_row_to_settings(row) for row in rows]
