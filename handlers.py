"""Обработчики команд и сообщений Telegram (aiogram 2.x)."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher, types
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from ai_service import LeadExtraction

from config import ADMIN_IDS, BOT_RATE_LIMIT_PER_MIN, NOTIFY_ON_NEW_LEAD, is_bot_admin
from database import get_recent_leads
from db_schema import STATUS_LABELS_RU, VALID_STATUSES
from lead_validation import LLM_UNAVAILABLE_HINT, REJECT_HINT, SPAM_HINT, is_spam_user_text
from leads_service import (
    commit_lead,
    format_admin_new_lead_message,
    format_lead_preview,
    message_for_prepare_failure,
    prepare_lead_from_text,
    status_label,
    update_lead_status,
)
from rate_limit import UserRateLimiter

logger = logging.getLogger(__name__)

_message_limiter = UserRateLimiter(BOT_RATE_LIMIT_PER_MIN)
_pending_leads: dict[int, LeadExtraction] = {}

RATE_LIMIT_MESSAGE = (
    "Слишком много сообщений подряд. Подождите около минуты и отправьте заявку снова."
)

CONFIRM_KB = InlineKeyboardMarkup().row(
    InlineKeyboardButton("Подтвердить", callback_data="lead_confirm"),
    InlineKeyboardButton("Отменить", callback_data="lead_cancel"),
)

EXAMPLE_TEXT = (
    "Пример: Марина, 89152223344, Kia Rio — скрипят колодки, пятница после 15:00"
)

CLIENT_KB = ReplyKeyboardMarkup(resize_keyboard=True)
CLIENT_KB.add(KeyboardButton("Пример текста заявки"))


def _format_leads_message(leads: list[dict[str, object]]) -> str:
    if not leads:
        return "Заявок пока нет."

    header = f"Последние заявки ({len(leads)}):"
    blocks: list[str] = [header, ""]

    for row in leads:
        lead_id = row.get("id")
        blocks.append(f"——— Заявка #{lead_id} ———")
        blocks.append(f"Имя: {row.get('name') or '—'}")
        blocks.append(f"Телефон: {row.get('phone') or '—'}")
        blocks.append(f"Услуга: {row.get('service') or '—'}")
        blocks.append(f"Дата: {row.get('date') or '—'}")
        status_key = str(row.get("status") or "new")
        blocks.append(f"Статус: {STATUS_LABELS_RU.get(status_key, status_key)}")
        blocks.append("")

    blocks.append("Смена статуса: /setstatus <id> new|in_progress|completed")
    return "\n".join(blocks).rstrip()


async def _notify_admin_new_lead(bot: types.Bot, lead_id: int, lead) -> None:
    if not NOTIFY_ON_NEW_LEAD or not ADMIN_IDS:
        return
    text = format_admin_new_lead_message(lead_id, lead)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Не удалось отправить уведомление админу id=%s", admin_id)


def register_handlers(dp: Dispatcher) -> None:
    @dp.message_handler(commands=["start"])
    async def handle_start(message: types.Message) -> None:
        await message.answer(
            "Здравствуйте! Я помощник автосервиса. Опишите в свободной форме, что вам нужно: "
            "имя, телефон, суть проблемы или марку авто и желаемое время визита — я оформлю заявку.",
            reply_markup=CLIENT_KB,
        )

    @dp.message_handler(commands=["admin"])
    async def handle_admin(message: types.Message) -> None:
        if not message.from_user:
            return
        user_id = message.from_user.id
        if not is_bot_admin(user_id):
            await message.answer("У вас нет доступа к этой команде.")
            return
        try:
            leads = await get_recent_leads(limit=10)
        except Exception:
            logger.exception("Ошибка чтения заявок для admin telegram_id=%s", user_id)
            await message.answer("Не удалось загрузить заявки. Попробуйте позже.")
            return
        await message.answer(_format_leads_message(leads))

    @dp.message_handler(commands=["setstatus"])
    async def handle_setstatus(message: types.Message) -> None:
        if not message.from_user or not message.text:
            return
        if not is_bot_admin(message.from_user.id):
            await message.answer("У вас нет доступа к этой команде.")
            return
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer(
                "Формат: /setstatus <id> new|in_progress|completed\n"
                "Пример: /setstatus 5 in_progress"
            )
            return
        try:
            lead_id = int(parts[1])
        except ValueError:
            await message.answer("id заявки должен быть числом.")
            return
        new_status = parts[2].strip()
        if new_status not in VALID_STATUSES:
            await message.answer("Статус: new, in_progress или completed.")
            return
        ok = await asyncio.to_thread(update_lead_status, lead_id, new_status)
        if not ok:
            await message.answer(f"Заявка #{lead_id} не найдена.")
            return
        await message.answer(
            f"Заявка #{lead_id}: статус → {status_label(new_status)}"
        )

    @dp.message_handler(
        lambda message: message.text is not None,
        content_types=types.ContentType.TEXT,
    )
    async def handle_text(message: types.Message) -> None:
        if not message.from_user or not message.text:
            return

        user_id = message.from_user.id
        text = message.text.strip()

        if text == "Пример текста заявки":
            await message.answer(EXAMPLE_TEXT)
            return

        logger.info("Входящее сообщение от telegram_id=%s", user_id)

        if is_spam_user_text(text):
            await message.answer(SPAM_HINT)
            return

        if not _message_limiter.allow(user_id):
            await message.answer(RATE_LIMIT_MESSAGE)
            return

        await message.bot.send_chat_action(message.chat.id, types.ChatActions.TYPING)
        wait_notice = await message.answer(
            "Обрабатываю заявку… (ИИ может отвечать до минуты на бесплатной модели)"
        )

        try:
            prepared = await prepare_lead_from_text(text)
        except Exception:
            logger.exception("Ошибка разбора заявки telegram_id=%s", user_id)
            try:
                await wait_notice.delete()
            except Exception:
                pass
            await message.answer(LLM_UNAVAILABLE_HINT)
            return

        try:
            await wait_notice.delete()
        except Exception:
            pass

        if not prepared.ok or prepared.lead is None:
            await message.answer(message_for_prepare_failure(text, prepared))
            return

        _pending_leads[user_id] = prepared.lead
        await message.answer(format_lead_preview(prepared.lead), reply_markup=CONFIRM_KB)

    @dp.callback_query_handler(lambda c: c.data in ("lead_confirm", "lead_cancel"))
    async def handle_lead_confirm(cb: types.CallbackQuery) -> None:
        if not cb.from_user or not cb.message:
            return
        user_id = cb.from_user.id
        await cb.answer()

        if cb.data == "lead_cancel":
            _pending_leads.pop(user_id, None)
            await cb.message.edit_text("Заявка отменена. Можете отправить текст заново.")
            return

        lead = _pending_leads.pop(user_id, None)
        if lead is None:
            await cb.message.edit_text("Сессия устарела. Отправьте заявку текстом снова.")
            return

        try:
            result = await commit_lead(user_id, lead)
        except Exception:
            logger.exception("Ошибка сохранения lead telegram_id=%s", user_id)
            await cb.message.edit_text(
                "Не удалось сохранить заявку. Попробуйте позже."
            )
            return

        if not result.success:
            if result.duplicate_id:
                await cb.message.edit_text(
                    f"Заявка с этим телефоном уже есть (#{result.duplicate_id}) за последние 24 часа."
                )
            else:
                await cb.message.edit_text(REJECT_HINT)
            return

        assert result.lead_id is not None
        await cb.message.edit_text(
            "\n".join(
                [
                    f"Заявка #{result.lead_id} принята и сохранена.",
                    "",
                    f"Имя: {lead.name}",
                    f"Телефон: {lead.phone}",
                    f"Сервис / авто: {lead.service or '—'}",
                    f"Дата/время: {lead.date or '—'}",
                ]
            )
        )
        await _notify_admin_new_lead(cb.bot, result.lead_id, lead)
