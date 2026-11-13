import sqlite3

import pytest

from db_schema import init_db_sync
from leads_service import update_lead_status


def test_update_lead_status_sets_updated_at(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    init_db_sync(str(db_path))
    monkeypatch.setattr("leads_service.DATABASE_PATH", str(db_path))

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO leads
            (telegram_id, name, phone, service, date, created_at, status, updated_at)
            VALUES (1, 'Test', '+7999', 's', 'd', '2026-01-01T00:00:00+00:00', 'new', '2026-01-01T00:00:00+00:00')
            """
        )
        conn.commit()

    assert update_lead_status(1, "completed")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, updated_at, created_at FROM leads WHERE id = 1"
        ).fetchone()
    assert row[0] == "completed"
    assert row[1] != row[2]
