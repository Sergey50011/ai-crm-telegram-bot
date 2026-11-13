"""Сценарии работы с заявками (бот + веб)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ai_service import LeadExtraction, extract_lead_from_message
from config import BOT_FALLBACK_PARSE, DATABASE_PATH
from integrations.google_sheets import append_lead_to_sheet, sheets_integration_configured
from lead_fallback import parse_lead_fallback

logger = logging.getLogger(__name__)
from database import find_duplicate_lead_id_by_phone, insert_lead
from db_schema import STATUS_LABELS_RU, VALID_STATUSES
from lead_validation import (
    LLM_UNAVAILABLE_HINT,
    REJECT_HINT,
    SPAM_HINT,
    is_complete_lead,
    is_garbage_user_text,
    is_spam_user_text,
    normalize_lead,
)


@dataclass
class PreparedLeadResult:
    ok: bool
    lead: LeadExtraction | None = None
    rejected: bool = False
    parse_failed: bool = False


@dataclass
class CommitLeadResult:
    success: bool
    lead_id: int | None = None
    duplicate_id: int | None = None


@dataclass
class IncomingLeadResult:
    success: bool
    lead_id: int | None = None
    lead: LeadExtraction | None = None
    rejected: bool = False
    parse_failed: bool = False
    duplicate_id: int | None = None


async def prepare_lead_from_text(text: str) -> PreparedLeadResult:
    if is_spam_user_text(text) or is_garbage_user_text(text):
        return PreparedLeadResult(ok=False, rejected=True)

    raw = await extract_lead_from_message(text)
    if raw is None and BOT_FALLBACK_PARSE:
        raw = parse_lead_fallback(text)
    if raw is None:
        return PreparedLeadResult(ok=False, parse_failed=True)

    lead = normalize_lead(raw)
    if not is_complete_lead(lead):
        return PreparedLeadResult(ok=False, rejected=True)

    return PreparedLeadResult(ok=True, lead=lead)


def message_for_prepare_failure(text: str, result: PreparedLeadResult) -> str:
    """Текст пользователю: спам / сбой ИИ / неполные данные."""
    if is_spam_user_text(text):
        return SPAM_HINT
    if result.parse_failed:
        return LLM_UNAVAILABLE_HINT
    return REJECT_HINT


def format_lead_preview(lead: LeadExtraction) -> str:
    return "\n".join(
        [
            "Проверьте заявку:",
            "",
            f"Имя: {lead.name or '—'}",
            f"Телефон: {lead.phone or '—'}",
            f"Сервис / авто: {lead.service or '—'}",
            f"Дата/время: {lead.date or '—'}",
            "",
            "Всё верно?",
        ]
    )


async def commit_lead(telegram_id: int, lead: LeadExtraction) -> CommitLeadResult:
    dup = await find_duplicate_lead_id_by_phone(lead.phone)
    if dup is not None:
        return CommitLeadResult(success=False, duplicate_id=dup)

    lead_id = await insert_lead(
        telegram_id=telegram_id,
        name=lead.name,
        phone=lead.phone,
        service=lead.service,
        date=lead.date,
    )
    if sheets_integration_configured():
        try:
            await asyncio.to_thread(
                append_lead_to_sheet,
                lead_id,
                telegram_id,
                lead,
            )
        except Exception:
            logger.exception(
                "Google Sheets: не удалось добавить заявку id=%s", lead_id
            )
    return CommitLeadResult(success=True, lead_id=lead_id)


async def process_incoming_lead_text(
    telegram_id: int, text: str
) -> IncomingLeadResult:
    """Прямое сохранение (для тестов / без подтверждения)."""
    prepared = await prepare_lead_from_text(text)
    if not prepared.ok:
        return IncomingLeadResult(
            success=False,
            rejected=prepared.rejected,
            parse_failed=prepared.parse_failed,
        )
    assert prepared.lead is not None
    committed = await commit_lead(telegram_id, prepared.lead)
    if not committed.success:
        return IncomingLeadResult(success=False, duplicate_id=committed.duplicate_id)
    return IncomingLeadResult(
        success=True,
        lead_id=committed.lead_id,
        lead=prepared.lead,
    )


def format_admin_new_lead_message(lead_id: int, lead: LeadExtraction) -> str:
    return "\n".join(
        [
            f"Новая заявка #{lead_id}",
            f"Имя: {lead.name}",
            f"Телефон: {lead.phone}",
            f"Услуга: {lead.service or '—'}",
            f"Дата: {lead.date or '—'}",
        ]
    )


def _resolve_db_path() -> str:
    base = Path(__file__).resolve().parent
    path = Path(DATABASE_PATH)
    if not path.is_absolute():
        path = base / path
    return str(path)


def update_lead_status(lead_id: int, new_status: str) -> bool:
    if new_status not in VALID_STATUSES:
        raise ValueError("invalid status")
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_resolve_db_path()) as conn:
        cur = conn.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, now, lead_id),
        )
        conn.commit()
        return cur.rowcount > 0


def status_label(status: str) -> str:
    return STATUS_LABELS_RU.get(status, status)
