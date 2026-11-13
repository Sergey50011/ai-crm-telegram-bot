"""Тесты валидации заявок (этап 0)."""

from ai_service import LeadExtraction
from lead_validation import (
    is_complete_lead,
    is_garbage_user_text,
    is_oversized_user_text,
    is_repetitive_user_text,
    is_spam_user_text,
    normalize_lead,
    normalize_name,
)


def test_garbage_rejected():
    assert is_garbage_user_text("?")
    assert is_garbage_user_text("   ")
    assert is_garbage_user_text("ok")
    assert not is_garbage_user_text("марина 89152223344 тормоза")


def test_oversized_rejected():
    assert is_oversized_user_text("x" * 601)
    assert not is_oversized_user_text("марина 89152223344 тормоза")


def test_repetitive_lines_rejected():
    line = "Марина, 89152223344, Kia Rio — скрипят колодки, пятница после 15:00"
    block = "\n".join([line] * 4)
    assert is_repetitive_user_text(block)
    assert is_spam_user_text(block)
    assert not is_repetitive_user_text("\n".join([line, line]))


def test_repetitive_ignores_short_lines():
    assert not is_repetitive_user_text("да\nда\nда")


def test_incomplete_lead():
    assert not is_complete_lead(LeadExtraction(name=None, phone=None, service="x", date=None))
    assert not is_complete_lead(LeadExtraction(name="И", phone="123", service="x", date=None))
    assert is_complete_lead(
        LeadExtraction(name="Марина", phone="89152223344", service="колодки", date="пт")
    )


def test_normalize_name():
    assert normalize_name("марина") == "Марина"
    assert normalize_name("олег петров") == "Олег Петров"


def test_normalize_lead_phone():
    lead = normalize_lead(
        LeadExtraction(name="марина", phone="89152223344", service="rio", date=None)
    )
    assert lead.name == "Марина"
    assert "+7" in (lead.phone or "")
