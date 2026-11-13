"""Проверка и нормализация данных заявки после ответа ИИ."""

from __future__ import annotations

import re
from collections import Counter

from ai_service import LeadExtraction
from config import BOT_MAX_MESSAGE_CHARS, BOT_REPEAT_LINE_THRESHOLD

MIN_PHONE_DIGITS = 10
MIN_NAME_LEN = 2
MIN_MESSAGE_LEN = 6
# Строка короче — не учитываем в детекте копипаста (имя, короткая реплика)
_REPEAT_MIN_LINE_LEN = 15

REJECT_HINT = (
    "К сожалению, не удалось оформить заявку. Пожалуйста, отправьте сообщение ещё раз — "
    "укажите имя, телефон, что случилось с автомобилем (или марку) и удобное время визита."
)

SPAM_HINT = (
    "Сообщение слишком длинное или похоже на повтор одной заявки. "
    "Отправьте одну короткую заявку: имя, телефон, проблема с авто и удобное время."
)

LLM_UNAVAILABLE_HINT = (
    "Сервис распознавания заявки сейчас недоступен или перегружен. "
    "Подождите минуту и отправьте сообщение ещё раз — укажите имя, телефон, "
    "что случилось с автомобилем (или марку) и удобное время визита."
)


def _normalize_line_for_repeat(line: str) -> str:
    collapsed = re.sub(r"\s+", " ", line.strip().casefold())
    return re.sub(r"\d+", "#", collapsed)


def is_repetitive_user_text(text: str) -> bool:
    """Несколько одинаковых строк (копипаст в одном сообщении)."""
    lines = [
        ln
        for ln in (_normalize_line_for_repeat(part) for part in text.splitlines())
        if len(ln) >= _REPEAT_MIN_LINE_LEN
    ]
    if len(lines) < BOT_REPEAT_LINE_THRESHOLD:
        return False
    _line, count = Counter(lines).most_common(1)[0]
    return count >= BOT_REPEAT_LINE_THRESHOLD


def is_oversized_user_text(text: str) -> bool:
    return len(text.strip()) > BOT_MAX_MESSAGE_CHARS


def is_spam_user_text(text: str) -> bool:
    return is_oversized_user_text(text) or is_repetitive_user_text(text)


def is_garbage_user_text(text: str) -> bool:
    """Слишком короткий или бессмысленный ввод — не вызываем LLM."""
    stripped = text.strip()
    if not stripped:
        return True
    digits = sum(1 for c in stripped if c.isdigit())
    if len(stripped) < MIN_MESSAGE_LEN and digits < MIN_PHONE_DIGITS:
        return True
    if re.fullmatch(r"[\s\?\.\!\,\-\+\*\#\@\%\^\&\(\)]+", stripped):
        return True
    return False


def _phone_digit_count(phone: str | None) -> int:
    return len(re.sub(r"\D", "", phone or ""))


def is_complete_lead(lead: LeadExtraction) -> bool:
    """Достаточно данных для записи в CRM."""
    name = (lead.name or "").strip()
    if len(name) < MIN_NAME_LEN:
        return False
    if _phone_digit_count(lead.phone) < MIN_PHONE_DIGITS:
        return False
    return True


def normalize_name(name: str | None) -> str | None:
    if not name or not name.strip():
        return None
    parts = name.strip().split()
    return " ".join(p[:1].upper() + p[1:] if p else p for p in parts)


def normalize_phone(phone: str | None) -> str | None:
    """Приводит российский номер к читаемому виду +7 (XXX) XXX-XX-XX."""
    if not phone or not phone.strip():
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10:
        d = digits
        return f"+7 ({d[0:3]}) {d[3:6]}-{d[6:8]}-{d[8:10]}"
    if len(digits) == 11 and digits.startswith("7"):
        d = digits
        return f"+{d[0]} ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}"
    return phone.strip()


def normalize_lead(lead: LeadExtraction) -> LeadExtraction:
    return LeadExtraction(
        name=normalize_name(lead.name),
        phone=normalize_phone(lead.phone),
        service=(lead.service or "").strip() or None,
        date=(lead.date or "").strip() or None,
    )
