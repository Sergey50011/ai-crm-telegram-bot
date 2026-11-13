"""Добавление строки заявки в Google Sheets (service account)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from ai_service import LeadExtraction

logger = logging.getLogger(__name__)

_HEADER = [
    "id",
    "created_at",
    "name",
    "phone",
    "service",
    "visit_date",
    "status",
    "telegram_id",
]


def sheets_integration_configured() -> bool:
    from config import (
        GOOGLE_SERVICE_ACCOUNT_FILE,
        GOOGLE_SHEETS_ID,
        SHEETS_ENABLED,
    )

    if not SHEETS_ENABLED:
        return False
    if not GOOGLE_SHEETS_ID or not GOOGLE_SERVICE_ACCOUNT_FILE:
        return False
    return Path(_resolve_sa_path(GOOGLE_SERVICE_ACCOUNT_FILE)).is_file()


_ROOT = Path(__file__).resolve().parent.parent


def _resolve_sa_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return _ROOT / path


def _get_worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    from config import (
        GOOGLE_SERVICE_ACCOUNT_FILE,
        GOOGLE_SHEETS_ID,
        GOOGLE_SHEETS_WORKSHEET,
    )

    sa_path = _resolve_sa_path(GOOGLE_SERVICE_ACCOUNT_FILE)
    creds = Credentials.from_service_account_file(
        str(sa_path),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
    try:
        return spreadsheet.worksheet(GOOGLE_SHEETS_WORKSHEET)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(
            title=GOOGLE_SHEETS_WORKSHEET, rows=1000, cols=len(_HEADER)
        )


def _ensure_header(worksheet) -> None:
    first = worksheet.row_values(1)
    if not first:
        worksheet.append_row(_HEADER, value_input_option="USER_ENTERED")


def append_lead_to_sheet(
    lead_id: int,
    telegram_id: int,
    lead: LeadExtraction,
    *,
    status: str = "new",
    created_at: str | None = None,
) -> None:
    """
    Синхронный вызов (из asyncio.to_thread).
    Ошибки наружу — логирует вызывающий код.
    """
    if not sheets_integration_configured():
        return

    created = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    row = [
        lead_id,
        created,
        lead.name or "",
        lead.phone or "",
        lead.service or "",
        lead.date or "",
        status,
        telegram_id,
    ]

    worksheet = _get_worksheet()
    _ensure_header(worksheet)
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    logger.info("Google Sheets: добавлена строка для заявки id=%s", lead_id)
