"""아침 브리핑 명령어와 발송 잡."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CommandHandler, ContextTypes

from app.services.briefing import (
    ALL_SECTIONS,
    SECTION_LABELS,
    BriefingClients,
    build_briefing,
    parse_sections,
)
from app.services.regions import region_names, resolve_region
from app.services.repository import Repository

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

WEEKEND_DAYS = {5, 6}  # 토, 일

BRIEFING_HELP = """아침 브리핑 봇 — 명령어 목록

/briefing on — 매일 아침 브리핑 받기 (기본 꺼짐)
/settime 07:30 — 발송 시각 (KST)
/region 서울 — 지역 (수원, 부산 등)
/sections weather,dust,fx,news — 섹션 선택
/weekend on — 주말에도 받기 (기본 꺼짐)

/preview — 지금 바로 미리보기
/settings — 내 설정 요약
/status — 봇 상태 · /id — 내 chat id

섹션: weather(날씨) dust(미세먼지) fx(환율) news(뉴스)
지역: 서울 부산 대구 인천 광주 대전 울산 세종 수원 춘천 강릉 청주
      천안 전주 목포 여수 포항 창원 제주"""


def handlers() -> list[CommandHandler]:
    return [
        CommandHandler("briefing", cmd_briefing),
        CommandHandler("settime", cmd_settime),
        CommandHandler("region", cmd_region),
        CommandHandler("sections", cmd_sections),
        CommandHandler("weekend", cmd_weekend),
        CommandHandler("preview", cmd_preview),
        CommandHandler("settings", cmd_settings),
    ]


# ---- 내부 헬퍼 -------------------------------------------------------------


def _repo(context: ContextTypes.DEFAULT_TYPE) -> Repository:
    return context.bot_data["repo"]


def _clients(context: ContextTypes.DEFAULT_TYPE) -> BriefingClients:
    return context.bot_data["clients"]


def _ids(update: Update) -> tuple[int, int] | None:
    if update.effective_user is None or update.effective_chat is None:
        return None
    return update.effective_user.id, update.effective_chat.id


async def _say(update: Update, text: str) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(text)


async def _send_briefing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, settings) -> bool:
    chunks = await build_briefing(
        region_name=settings.region,
        sections=settings.sections,
        clients=_clients(context),
        now=datetime.now(KST),
    )
    try:
        for chunk in chunks:
            await context.bot.send_message(chat_id=chat_id, text=chunk)
        return True
    except TelegramError:
        logger.warning("브리핑 전송 실패 (chat_id=%s)", chat_id, exc_info=True)
        return False


def _sections_text(sections: list[str]) -> str:
    return ", ".join(f"{section}({SECTION_LABELS[section]})" for section in sections)


# ---- 명령어 ----------------------------------------------------------------


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    repo = _repo(context)
    if not context.args or context.args[0].lower() not in {"on", "off", "켜기", "끄기"}:
        settings = await repo.get(chat_id)
        state = "켜짐" if settings.enabled else "꺼짐"
        await _say(update, f"아침 브리핑: {state}\n사용법: /briefing on 또는 /briefing off")
        return
    enabled = context.args[0].lower() in {"on", "켜기"}
    await repo.set_enabled(chat_id, enabled)
    if enabled:
        settings = await repo.get(chat_id)
        await _say(
            update,
            f"아침 브리핑을 켰습니다. 매일 {settings.send_time} (KST)에 "
            f"{settings.region} 기준으로 보내드립니다.\n/preview 로 미리 확인해보세요.",
        )
    else:
        await _say(update, "아침 브리핑을 껐습니다.")


async def cmd_settime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    if not context.args or not TIME_RE.match(context.args[0]):
        await _say(update, "시간은 HH:MM 형식으로 입력하세요. 예: /settime 07:30")
        return
    send_time = context.args[0]
    await _repo(context).set_time(chat_id, send_time)
    await _say(update, f"발송 시각을 {send_time} (KST)로 설정했습니다.")


async def cmd_region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    repo = _repo(context)
    if not context.args:
        settings = await repo.get(chat_id)
        await _say(
            update,
            f"현재 지역: {settings.region}\n지역 목록: {region_names()}",
        )
        return
    region = resolve_region(context.args[0])
    if region is None:
        await _say(update, f"지원하지 않는 지역입니다.\n지역 목록: {region_names()}")
        return
    await repo.set_region(chat_id, region.label)
    await _say(update, f"지역을 {region.label}로 설정했습니다.")


async def cmd_sections(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    repo = _repo(context)
    if not context.args:
        settings = await repo.get(chat_id)
        await _say(
            update,
            f"현재 섹션: {_sections_text(settings.sections)}\n"
            f"사용 가능: {_sections_text(ALL_SECTIONS)}\n"
            "사용법: /sections weather,dust,fx,news",
        )
        return
    sections = parse_sections(" ".join(context.args))
    if sections is None:
        await _say(update, f"섹션 이름을 확인하세요. 사용 가능: {_sections_text(ALL_SECTIONS)}")
        return
    await repo.set_sections(chat_id, sections)
    await _say(update, f"섹션 설정: {_sections_text(sections)}")


async def cmd_weekend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    repo = _repo(context)
    if not context.args or context.args[0].lower() not in {"on", "off", "켜기", "끄기"}:
        settings = await repo.get(chat_id)
        state = "켜짐" if settings.weekend else "꺼짐"
        await _say(update, f"주말 발송: {state}\n사용법: /weekend on 또는 /weekend off")
        return
    enabled = context.args[0].lower() in {"on", "켜기"}
    await repo.set_weekend(chat_id, enabled)
    await _say(
        update,
        "주말에도 브리핑을 보냅니다." if enabled else "주말에는 브리핑을 보내지 않습니다.",
    )


async def cmd_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    settings = await _repo(context).get(chat_id)
    await _send_briefing(context, chat_id, settings)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = _ids(update)
    if ids is None:
        return
    _user_id, chat_id = ids
    settings = await _repo(context).get(chat_id)
    lines = [
        "내 설정",
        f"브리핑: {'켜짐' if settings.enabled else '꺼짐'}",
        f"시각: {settings.send_time} (KST)",
        f"지역: {settings.region}",
        f"섹션: {_sections_text(settings.sections)}",
        f"주말 발송: {'켜짐' if settings.weekend else '꺼짐'}",
    ]
    await _say(update, "\n".join(lines))


# ---- 백그라운드 잡 ---------------------------------------------------------


async def briefing_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """매 분 확인해 설정 시각이 되면 브리핑을 보낸다 (하루 1회)."""
    now = datetime.now(KST)
    hhmm = now.strftime("%H:%M")
    today = now.strftime("%Y%m%d")

    repo = _repo(context)
    for settings in await repo.all_enabled():
        if settings.send_time != hhmm or settings.last_sent_date == today:
            continue
        if not settings.weekend and now.weekday() in WEEKEND_DAYS:
            continue
        sent = await _send_briefing(context, settings.chat_id, settings)
        if sent:
            await repo.mark_sent(settings.chat_id, today)
