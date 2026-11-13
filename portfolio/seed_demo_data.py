"""Демо-данные для портфолио: согласованные лиды в orders.db.

По умолчанию не удаляет существующие заявки.
Для пересъёмки скринов: python portfolio/seed_demo_data.py --replace
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "orders.db"

sys.path.insert(0, str(ROOT))
from db_schema import init_db_sync  # noqa: E402

DEMO_LEADS = [
    (
        900_001,
        "Марина Козлова",
        "+7 915 222-33-44",
        "Kia Rio — скрипят колодки",
        "пятница после 15:00",
        "new",
    ),
    (
        900_002,
        "Олег Петров",
        "+7 903 111-22-33",
        "Toyota Camry — замена масла и фильтра",
        "суббота утром",
        "in_progress",
    ),
    (
        900_003,
        "Виктор Смирнов",
        "+7 905 123-45-67",
        "VW Polo — диагностика двигателя",
        "завтра в 10:00",
        "new",
    ),
    (
        900_004,
        "Ильяс Нурланов",
        "+7 977 400-11-22",
        "Hyundai Solaris — развал-схождение",
        "12 ноября",
        "in_progress",
    ),
    (
        900_005,
        "Анна Черных",
        "+7 926 555-01-88",
        "Шиномонтаж R17",
        "8 ноября",
        "completed",
    ),
    (
        900_006,
        "Руслан Гасанов",
        "+7 918 300-77-66",
        "Acura MDX — плановое ТО",
        "15 ноября",
        "completed",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить orders.db демо-заявками")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Удалить все заявки и записать демо-набор (для portfolio/capture_screenshots)",
    )
    args = parser.parse_args()

    init_db_sync(str(DB_PATH))
    base_time = datetime(2026, 11, 8, 10, 0, tzinfo=timezone.utc)

    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        if count > 0 and not args.replace:
            print(
                f"В БД уже {count} заявок. Живые данные не тронуты. "
                "Для демо-портафеля: python portfolio/seed_demo_data.py --replace"
            )
            return

        if args.replace:
            conn.execute("DELETE FROM leads")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='leads'")

        for idx, row in enumerate(DEMO_LEADS):
            tg_id, name, phone, service, date, status = row
            created = (base_time + timedelta(minutes=idx * 12)).isoformat()
            conn.execute(
                """
                INSERT INTO leads
                (telegram_id, name, phone, service, date, created_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tg_id, name, phone, service, date, created, status, created),
            )
        conn.commit()
    print(f"Записано {len(DEMO_LEADS)} демо-заявок в {DB_PATH}")


if __name__ == "__main__":
    main()
