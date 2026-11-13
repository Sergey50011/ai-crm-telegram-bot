"""Запасной разбор заявки без ИИ (regex): имя, телефон, остальное — в услугу."""

from __future__ import annotations

import logging
import re

from ai_service import LeadExtraction
from lead_validation import MIN_NAME_LEN, MIN_PHONE_DIGITS

logger = logging.getLogger(__name__)

_NAME_SKIP = frozenset(
    {
        "значит",
        "так",
        "ну",
        "и",
        "в",
        "на",
        "к",
        "по",
        "хочу",
        "давайте",
        "тел",
        "телефон",
        "машина",
        "авто",
        "пример",
        "привет",
    }
)

_MAX_SERVICE_LEN = 300


def _digit_count(s: str) -> int:
    return len(re.sub(r"\D", "", s))


def _find_phone_span(text: str) -> tuple[str, int, int] | None:
    """Подстрока с телефоном (>=10 цифр) и её позиция."""
    candidates: list[tuple[int, int, int, str]] = []

    for m in re.finditer(r"[\d\+\(\)\s\-]{10,28}", text):
        sub = m.group()
        digits = _digit_count(sub)
        if digits >= MIN_PHONE_DIGITS:
            candidates.append((digits, m.start(), m.end(), sub))

    for m in re.finditer(r"\d{10,12}", text):
        sub = m.group()
        candidates.append((len(sub), m.start(), m.end(), sub))

    if not candidates:
        return None

    _, start, end, sub = max(candidates, key=lambda c: (c[0], -c[1]))
    return sub, start, end


def _guess_name(chunk: str) -> str | None:
    for part in re.split(r"[\s,;]+", chunk.strip()):
        word = part.strip()
        if len(word) < MIN_NAME_LEN or word.lower() in _NAME_SKIP:
            continue
        if re.fullmatch(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-]{0,29}", word):
            return word
    return None


def _build_service(text: str, phone_start: int, phone_end: int, name: str | None) -> str | None:
    rest = (text[:phone_start] + " " + text[phone_end:]).strip()
    if name:
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        rest = pattern.sub("", rest, count=1).strip(" ,.—–-")
    rest = re.sub(r"\s+", " ", rest).strip()
    if not rest:
        return None
    if len(rest) > _MAX_SERVICE_LEN:
        rest = rest[:_MAX_SERVICE_LEN].rstrip() + "…"
    return rest


def parse_lead_fallback(text: str) -> LeadExtraction | None:
    """Имя + телефон из текста; остальное — в service. None, если нет телефона."""
    stripped = text.strip()
    if not stripped:
        return None

    found = _find_phone_span(stripped)
    if found is None:
        return None

    phone_raw, p_start, p_end = found
    if _digit_count(phone_raw) < MIN_PHONE_DIGITS:
        return None

    before = stripped[:p_start]
    name = _guess_name(before)
    if name is None:
        name = _guess_name(stripped[:p_start] + stripped[p_end:])

    service = _build_service(stripped, p_start, p_end, name)

    if name is None:
        # Без имени is_complete_lead не пройдёт — всё равно отдаём для единообразия
        logger.debug("fallback: телефон найден, имя не распознано")
    else:
        logger.info("fallback: разбор без ИИ (имя=%s)", name)

    return LeadExtraction(
        name=name,
        phone=phone_raw,
        service=service,
        date=None,
    )
