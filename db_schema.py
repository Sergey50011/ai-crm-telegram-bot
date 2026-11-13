"""Общая схема SQLite для бота и Flask-админки."""

from __future__ import annotations

import sqlite3

import aiosqlite

CREATE_LEADS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    name TEXT,
    phone TEXT,
    service TEXT,
    date TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    updated_at TEXT NOT NULL
);
"""

STATUS_DEFAULT = "new"
VALID_STATUSES = frozenset({"new", "in_progress", "completed"})

STATUS_LABELS_RU: dict[str, str] = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
}


def _migrate_columns_sync(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
    if "status" not in columns:
        conn.execute(
            "ALTER TABLE leads ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
        )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE leads ADD COLUMN updated_at TEXT")
        conn.execute(
            "UPDATE leads SET updated_at = created_at WHERE updated_at IS NULL"
        )


async def _migrate_columns_async(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(leads)")
    rows = await cursor.fetchall()
    columns = {row[1] for row in rows}
    if "status" not in columns:
        await db.execute(
            "ALTER TABLE leads ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
        )
    cursor = await db.execute("PRAGMA table_info(leads)")
    rows = await cursor.fetchall()
    columns = {row[1] for row in rows}
    if "updated_at" not in columns:
        await db.execute("ALTER TABLE leads ADD COLUMN updated_at TEXT")
        await db.execute(
            "UPDATE leads SET updated_at = created_at WHERE updated_at IS NULL"
        )


def init_db_sync(db_path: str) -> None:
    """Синхронная инициализация (Flask)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_LEADS_TABLE_SQL)
        _migrate_columns_sync(conn)
        conn.commit()


async def init_db_async(db_path: str) -> None:
    """Асинхронная инициализация (бот)."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_LEADS_TABLE_SQL)
        await _migrate_columns_async(db)
        await db.commit()
