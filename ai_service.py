"""Асинхронные запросы к OpenRouter и валидация ответа через Pydantic."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from config import OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — умный робот-ассистент сети автосервисов. Твоя задача — проанализировать "
    "сообщение клиента и строго извлечь из него ключевые данные. Сформируй JSON-ответ "
    "со следующими ключами: 'name' (имя клиента с заглавной буквы), 'phone' (телефон, цифры), "
    "'service' (кратко: марка авто и суть работы, до 80 символов, без лишней речи клиента), "
    "'date' (желаемая дата/время визита). "
    "Если каких-то данных нет, ставь null. Выводи СТРОГО чистый JSON-объект без "
    "markdown-разметки (не используй ```json), никаких вступлений и пояснений. "
    "Только текст, начинающийся с { и заканчивающийся }."
)


class LeadExtraction(BaseModel):
    """Структура данных, которую должен вернуть ИИ."""

    name: str | None = Field(default=None, description="Имя клиента")
    phone: str | None = Field(default=None, description="Телефон")
    service: str | None = Field(default=None, description="Поломка или марка авто")
    date: str | None = Field(default=None, description="Желаемая дата/время визита")


def _extract_json_object(raw: str) -> str | None:
    """Достаёт JSON-объект из текста (убирает markdown-ограждения при необходимости)."""
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parse_model_content(message: str) -> LeadExtraction | None:
    logger.debug("OpenRouter сырой текст модели: %s", message[:2000])
    json_str = _extract_json_object(message)
    if json_str is None:
        logger.warning("Не удалось выделить JSON из ответа: %s", message[:300])
        return None
    logger.debug("OpenRouter выделенный JSON: %s", json_str)
    try:
        parsed = json.loads(json_str)
        return LeadExtraction.model_validate(parsed)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.warning("Некорректный JSON или данные от ИИ: %s", e)
        return None


async def _fetch_openrouter_content(session: aiohttp.ClientSession, user_text: str) -> str | None:
    payload: dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/local/crm-booking-bot",
        "X-Title": "Auto Service Lead Bot",
    }

    async with session.post(OPENROUTER_API_URL, json=payload, headers=headers) as resp:
        body = await resp.text()
        if resp.status >= 400:
            logger.error("OpenRouter HTTP %s: %s", resp.status, body[:500])
            return None
        data = json.loads(body)

    choices = data.get("choices") or []
    if not choices:
        logger.error("Пустой choices в ответе OpenRouter: %s", str(data)[:500])
        return None
    content = (choices[0].get("message") or {}).get("content") or ""
    if not isinstance(content, str) or not content.strip():
        logger.error("Нет текста ответа модели")
        return None
    return content


async def extract_lead_from_message(user_text: str) -> LeadExtraction | None:
    """
    Отправляет сообщение в OpenRouter (до 2 попыток при ошибке разбора JSON)
    и возвращает валидированную модель или None.
    """
    logger.info("Запрос к OpenRouter, модель: %s", OPENROUTER_MODEL)

    try:
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in (1, 2):
                try:
                    content = await _fetch_openrouter_content(session, user_text)
                except (aiohttp.ClientError, json.JSONDecodeError, TimeoutError) as e:
                    logger.exception("Ошибка запроса к OpenRouter (попытка %s): %s", attempt, e)
                    content = None

                if content is None:
                    if attempt == 2:
                        return None
                    continue

                lead = _parse_model_content(content)
                if lead is not None:
                    return lead
                if attempt == 1:
                    logger.info("Повтор запроса к OpenRouter из-за невалидного JSON")
    except Exception:
        logger.exception("Непредвиденная ошибка extract_lead_from_message")
    return None
