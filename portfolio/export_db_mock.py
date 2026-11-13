"""Собрать database-data.html из реального orders.db."""

from __future__ import annotations

import html
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCK = Path(__file__).resolve().parent / "mockups" / "database-data.html"
DB = ROOT / "orders.db"

STATUS_CLASS = {
    "new": "status-new",
    "in_progress": "status-work",
    "completed": "status-done",
}


def main() -> None:
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            """
            SELECT id, telegram_id, name, phone, service, date, created_at, status
            FROM leads ORDER BY id
            """
        ).fetchall()

    body_rows = []
    for row in rows:
        lid, tg, name, phone, service, date, created, status = row
        cls = STATUS_CLASS.get(status or "new", "status-new")
        body_rows.append(
            "          <tr>"
            f"<td>{lid}</td><td>{tg}</td>"
            f"<td>{html.escape(name or '')}</td>"
            f"<td>{html.escape(phone or '')}</td>"
            f"<td>{html.escape(service or '')}</td>"
            f"<td>{html.escape(date or '')}</td>"
            f"<td>{html.escape(created or '')}</td>"
            f'<td class="{cls}">{html.escape(status or "new")}</td>'
            "</tr>"
        )

    content = MOCK.read_text(encoding="utf-8")
    updated = re.sub(
        r"<tbody>.*?</tbody>",
        "<tbody>\n" + "\n".join(body_rows) + "\n        </tbody>",
        content,
        count=1,
        flags=re.DOTALL,
    )
    MOCK.write_text(updated, encoding="utf-8")
    print(f"Обновлён {MOCK} ({len(rows)} строк)")


if __name__ == "__main__":
    main()
