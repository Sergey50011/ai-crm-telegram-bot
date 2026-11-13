"""Загрузка настроек из переменных окружения."""

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PROJECT_DIR / ".env"


def _load_dotenv_safe() -> None:
    """Читает .env в UTF-8; при ошибке пробует cp1251 (типично для Windows)."""
    if _ENV_FILE.is_file():
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                with _ENV_FILE.open(encoding=encoding) as handle:
                    handle.read()
                load_dotenv(dotenv_path=_ENV_FILE, encoding=encoding)
                return
            except UnicodeDecodeError:
                continue
        load_dotenv(dotenv_path=_ENV_FILE, encoding="cp1251")
    else:
        load_dotenv()


_load_dotenv_safe()

BOT_TOKEN: str = (os.getenv("BOT_TOKEN") or "").strip()
OPENROUTER_API_KEY: str = (os.getenv("OPENROUTER_API_KEY") or "").strip()
OPENROUTER_MODEL: str = (
    os.getenv("OPENROUTER_MODEL") or "meta-llama/llama-3-8b-instruct:free"
).strip()

OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

# Путь к SQLite относительно корня проекта
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "orders.db").strip() or "orders.db"

def _parse_admin_ids() -> frozenset[int]:
    ids: set[int] = set()
    multi = (os.getenv("ADMIN_IDS") or "").strip()
    if multi:
        for part in multi.replace(";", ",").split(","):
            piece = part.strip()
            if not piece:
                continue
            try:
                ids.add(int(piece))
            except ValueError:
                continue
    single = (os.getenv("ADMIN_ID") or "").strip()
    if single:
        try:
            ids.add(int(single))
        except ValueError:
            pass
    return frozenset(ids)


# Пусто — демо: /admin доступен всем в Telegram (не для продакшена)
ADMIN_IDS: frozenset[int] = _parse_admin_ids()
# Обратная совместимость (уведомления, документация)
ADMIN_ID: int | None = next(iter(ADMIN_IDS), None) if ADMIN_IDS else None


def is_bot_admin(user_id: int) -> bool:
    """Команды /admin и /setstatus только для перечисленных telegram user id."""
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS

# Веб-админка: Basic Auth (пустой пароль — без защиты, только для локального демо)
DASHBOARD_USERNAME: str = (os.getenv("DASHBOARD_USERNAME") or "admin").strip() or "admin"
DASHBOARD_PASSWORD: str = (os.getenv("DASHBOARD_PASSWORD") or "").strip()

_rate_raw = (os.getenv("BOT_RATE_LIMIT_PER_MIN") or "5").strip()
BOT_RATE_LIMIT_PER_MIN: int = 5
try:
    BOT_RATE_LIMIT_PER_MIN = max(1, int(_rate_raw))
except ValueError:
    BOT_RATE_LIMIT_PER_MIN = 5

_len_raw = (os.getenv("BOT_MAX_MESSAGE_CHARS") or "600").strip()
BOT_MAX_MESSAGE_CHARS: int = 600
try:
    BOT_MAX_MESSAGE_CHARS = max(100, int(_len_raw))
except ValueError:
    BOT_MAX_MESSAGE_CHARS = 600

_repeat_raw = (os.getenv("BOT_REPEAT_LINE_THRESHOLD") or "3").strip()
BOT_REPEAT_LINE_THRESHOLD: int = 3
try:
    BOT_REPEAT_LINE_THRESHOLD = max(2, int(_repeat_raw))
except ValueError:
    BOT_REPEAT_LINE_THRESHOLD = 3

LOG_LEVEL: str = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()

_notify_raw = (os.getenv("NOTIFY_ON_NEW_LEAD") or "1").strip().lower()
NOTIFY_ON_NEW_LEAD: bool = _notify_raw not in ("0", "false", "no", "off")

_fallback_raw = (os.getenv("BOT_FALLBACK_PARSE") or "1").strip().lower()
BOT_FALLBACK_PARSE: bool = _fallback_raw not in ("0", "false", "no", "off")

_sheets_raw = (os.getenv("SHEETS_ENABLED") or "0").strip().lower()
SHEETS_ENABLED: bool = _sheets_raw in ("1", "true", "yes", "on")

GOOGLE_SHEETS_ID: str = (os.getenv("GOOGLE_SHEETS_ID") or "").strip()
GOOGLE_SHEETS_WORKSHEET: str = (
    os.getenv("GOOGLE_SHEETS_WORKSHEET") or "Заявки"
).strip() or "Заявки"
GOOGLE_SERVICE_ACCOUNT_FILE: str = (
    os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "secrets/google-sa.json"
).strip()
