import asyncio

import pytest

from database import find_duplicate_lead_id_by_phone, insert_lead
from db_schema import init_db_async


def test_duplicate_phone_within_24h(tmp_path, monkeypatch):
    db_path = tmp_path / "d.db"
    monkeypatch.setattr("database.DATABASE_PATH", str(db_path))

    async def _run() -> None:
        await init_db_async(str(db_path))
        phone = "+7 (915) 222-33-44"
        lid = await insert_lead(
            telegram_id=1,
            name="A",
            phone=phone,
            service="s",
            date="d",
        )
        dup = await find_duplicate_lead_id_by_phone("89152223344")
        assert dup == lid

    asyncio.run(_run())
