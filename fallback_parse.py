"""Локальный разбор заявки без LLM (имя, телефон, остальное → service)."""

from __future__ import annotations

import re

from ai_service import LeadExtraction

from lead_validation import MIN_NAME_LEN, MIN_PHONE_DIGITS

_NAME_PART_RE = re.compile(r"^[\w.\-]+$", re.UNICODE)
_HAS_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]")
_PHONE_CHUNK_RE = re.compile(r"\+?[\d\s\-\(\)]{10,22}")
_MAX_SERVICE_LEN = 300


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _find_phone_span(text: str) -> tuple[str, int, int] | None:
    """Возвращает (сырой фрагмент с телефоном, start, end) или None."""
    candidates: list[tuple[int, int, int]] = []
    for m in _PHONE_CHUNK_RE.finditer(text):
        digits = _digits_only(m.group())
        if MIN_PHONE_DIGITS <= len(digits) <= 11:
            candidates.append((len(digits), m.start(), m.end()))
    for m in re.finditer(r"\d{10,11}", text):
        digits = m.group()
        if MIN_PHONE_DIGITS <= len(digits) <= 11:
            candidates.append((len(digits), m.start(), m.end()))
    if not candidates:
        return None
  # предпочитаем 11-значный (89...) ближе к началу
    candidates.sort(key=lambda t: (-t[0], t[1]))
    _, start, end = candidates[0]
    return text[start:end], start, end


def _take_name_words(parts: list[str]) -> tuple[list[str], list[str]]:
    name_words: list[str] = []
    rest: list[str] = []
    for i, part in enumerate(parts):
        cleaned = part.strip(".,;:!?")
        if not cleaned:
            continue
        if (
            i < 2
            and len(cleaned) >= MIN_NAME_LEN
            and _NAME_PART_RE.fullmatch(cleaned)
            and _HAS_LETTER_RE.search(cleaned)
            and not cleaned.isdigit()
        ):
            name_words.append(cleaned)
        else:
            rest = parts[i:]
            break
    if not name_words:
        rest = parts
    return name_words, rest


def parse_lead_without_llm(text: str) -> LeadExtraction | None:
    """
    Извлекает имя и телефон эвристиками; всё остальное в поле service.
    date всегда None — при необходимости клиент уточняет в комментарии.
    """
    stripped = text.strip()
    if not stripped:
        return None

    located = _find_phone_span(stripped)
    if located is None:
        return None
    phone_raw, start, end = located
    phone_digits = _digits_only(phone_raw)
    if len(phone_digits) < MIN_PHONE_DIGITS:
        return None

    before = stripped[:start].strip()
    after = stripped[end:].strip()
    parts_before = [p for p in re.split(r"[\s,]+", before) if p.strip()]
    name_words, rest_before_parts = _take_name_words(parts_before)
    name = " ".join(name_words) if name_words else None

    if not name:
        # имя после телефона или одно слово в начале без запятой
        all_parts = [p for p in re.split(r"[\s,]+", before + " " + after) if p.strip()]
        name_words, rest_all = _take_name_words(all_parts)
        if name_words:
            name = " ".join(name_words)
            service_bits = rest_all
        else:
            service_bits = rest_before_parts + ([p for p in re.split(r"[\s,]+", after) if p.strip()])
    else:
        service_bits = rest_before_parts + [p for p in re.split(r"[\s,]+", after) if p.strip()]

    service = " ".join(service_bits).strip(" ,;")
    if len(service) > _MAX_SERVICE_LEN:
        service = service[: _MAX_SERVICE_LEN - 1] + "…"
    if not service:
        service = None

    if not name or len(name) < MIN_NAME_LEN:
        return None

    return LeadExtraction(
        name=name,
        phone=phone_digits if len(phone_digits) >= 10 else phone_raw,
        service=service,
        date=None,
    )
