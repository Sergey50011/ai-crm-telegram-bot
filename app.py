"""
Веб-админка (Dashboard) для заявок автосервиса.

Запуск: python app.py
Откройте в браузере: http://127.0.0.1:5000
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from config import DASHBOARD_PASSWORD, DASHBOARD_USERNAME, DATABASE_PATH
from db_schema import STATUS_DEFAULT, VALID_STATUSES, init_db_sync
from leads_service import update_lead_status

app = Flask(__name__)


_MIN_DASHBOARD_PASSWORD_LEN = 8


def _dashboard_auth_ok() -> bool:
    auth = request.authorization
    if not auth:
        return False
    return (
        auth.username == DASHBOARD_USERNAME and auth.password == DASHBOARD_PASSWORD
    )


@app.before_request
def _require_dashboard_auth() -> Response | None:
    if request.endpoint is None:
        return None
    if _dashboard_auth_ok():
        return None
    return Response(
        "Требуется авторизация",
        401,
        {"WWW-Authenticate": 'Basic realm="CRM Dashboard", charset="UTF-8"'},
    )


def _db_path() -> str:
    """Абсолютный путь к SQLite, чтобы сервер работал из любой рабочей директории."""
    base = Path(__file__).resolve().parent
    path = Path(DATABASE_PATH)
    if not path.is_absolute():
        path = base / path
    return str(path)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "telegram_id": row["telegram_id"],
        "name": row["name"] or "—",
        "phone": row["phone"] or "—",
        "service": row["service"] or "—",
        "date": row["date"] or "—",
        "created_at": row["created_at"],
        "status": row["status"] or STATUS_DEFAULT,
        "updated_at": row["updated_at"] if "updated_at" in row.keys() else row["created_at"],
    }


@app.route("/")
def index():
    """Главная страница с таблицей заявок."""
    return render_template("index.html")


@app.get("/api/leads")
def api_leads():
    """Список всех заявок (от новых к старым)."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, telegram_id, name, phone, service, date, created_at, status, updated_at
            FROM leads
            ORDER BY id DESC
            """
        ).fetchall()
    return jsonify([_row_to_dict(row) for row in rows])


@app.get("/api/stats")
def api_stats():
    """Сводка для карточек в шапке дашборда."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE status = 'in_progress'"
        ).fetchone()[0]
        waiting = conn.execute(
            "SELECT COUNT(*) FROM leads WHERE status = 'new'"
        ).fetchone()[0]
    return jsonify(
        {
            "total": total,
            "in_progress": in_progress,
            "waiting": waiting,
        }
    )


@app.patch("/api/leads/<int:lead_id>/status")
def api_update_status(lead_id: int):
    """Обновляет статус заявки по id (тело JSON: {"status": "new"|"in_progress"|"completed"})."""
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()
    try:
        if new_status not in VALID_STATUSES:
            return jsonify({"error": "Недопустимый статус"}), 400
        if not update_lead_status(lead_id, new_status):
            return jsonify({"error": "Заявка не найдена"}), 404
    except ValueError:
        return jsonify({"error": "Недопустимый статус"}), 400

    return jsonify({"ok": True, "id": lead_id, "status": new_status})


def _ensure_dashboard_password_configured() -> None:
    pwd = DASHBOARD_PASSWORD
    if len(pwd) < _MIN_DASHBOARD_PASSWORD_LEN:
        print(
            f"Задайте DASHBOARD_PASSWORD в .env (не короче {_MIN_DASHBOARD_PASSWORD_LEN} символов). "
            "Веб-админка не запустится без пароля.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main() -> None:
    _ensure_dashboard_password_configured()
    init_db_sync(_db_path())
    # debug=False — достаточно для локальной админки; threaded=True для параллельных fetch.
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
