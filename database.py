"""Асинхронная работа с SQLite (leads) через aiosqlite."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import aiosqlite

from config import DATABASE_PATH
from db_schema import STATUS_DEFAULT, VALID_STATUSES, init_db_async

logger = logging.getLogger(__name__)

__all__ = [
    "STATUS_DEFAULT",
    "VALID_STATUSES",
    "init_db",
    "insert_lead",
    "get_recent_leads",
    "find_duplicate_lead_id_by_phone",
    "get_lead_by_id",
]


def _phone_tail(phone: str | None) -> str:
    return re.sub(r"\D", "", phone or "")[-10:]


async def init_db() -> None:
    await init_db_async(DATABASE_PATH)
    logger.info("База данных инициализирована: %s", DATABASE_PATH)


async def insert_lead(
    *,
    telegram_id: int,
    name: str | None,
    phone: str | None,
    service: str | None,
    date: str | None,
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO leads
            (telegram_id, name, phone, service, date, created_at, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                name,
                phone,
                service,
                date,
                created_at,
                STATUS_DEFAULT,
                created_at,
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid
    logger.info("Сохранён лид id=%s telegram_id=%s", row_id, telegram_id)
    return int(row_id)


async def find_duplicate_lead_id_by_phone(
    phone: str | None, *, hours: int = 24
) -> int | None:
    """Ищет недавнюю заявку с тем же телефоном (последние 10 цифр)."""
    tail = _phone_tail(phone)
    if len(tail) < 10:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, phone, created_at FROM leads ORDER BY id DESC LIMIT 300"
        )
        rows = await cursor.fetchall()
    for row in rows:
        if _phone_tail(row["phone"]) != tail:
            continue
        try:
            created = datetime.fromisoformat(row["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if created >= cutoff:
            return int(row["id"])
    return None


async def get_lead_by_id(lead_id: int) -> dict[str, object] | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, telegram_id, name, phone, service, date, created_at, status, updated_at
            FROM leads WHERE id = ?
            """,
            (lead_id,),
        )
        row = await cursor.fetchone()
    return dict(row) if row else None


async def get_recent_leads(limit: int = 10) -> list[dict[str, object]]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, telegram_id, name, phone, service, date, created_at, status, updated_at
            FROM leads
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]
