"""Точка входа: логирование, инициализация БД, запуск polling Telegram-бота (aiogram 2.x)."""

from __future__ import annotations

import logging
import sys

from aiogram import Bot, Dispatcher, executor

from config import BOT_TOKEN, LOG_LEVEL, OPENROUTER_API_KEY
from database import init_db
from handlers import register_handlers


def setup_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    if level <= logging.DEBUG:
        logging.getLogger("ai_service").setLevel(logging.DEBUG)


async def on_startup(dp: Dispatcher) -> None:
    await init_db()
    logging.getLogger(__name__).info("Бот запущен (long polling)")


def main() -> None:
    setup_logging()
    log = logging.getLogger(__name__)

    if not BOT_TOKEN:
        log.error("Не задан BOT_TOKEN в .env")
        sys.exit(1)
    if not OPENROUTER_API_KEY:
        log.error("Не задан OPENROUTER_API_KEY в .env")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot)
    register_handlers(dp)

    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


if __name__ == "__main__":
    # aiogram 2.x на Python 3.10+ (в т.ч. 3.15): нужен явный event loop
    import asyncio

    asyncio.set_event_loop(asyncio.new_event_loop())
    main()

