"""Запасной разбор без ИИ."""

from lead_fallback import parse_lead_fallback
from lead_validation import is_complete_lead, normalize_lead


def test_fallback_marina_style():
    text = "Марина, 89152223344, Kia Rio — скрипят колодки, пятница после 15:00"
    raw = parse_lead_fallback(text)
    assert raw is not None
    lead = normalize_lead(raw)
    assert lead.name == "Марина"
    assert is_complete_lead(lead)
    assert lead.service and "Kia" in lead.service
    assert lead.date is None


def test_fallback_sergey_messy():
    text = "значит так сергей машина митсубиси ударился в столб хочу завтра 79031234567"
    raw = parse_lead_fallback(text)
    assert raw is not None
    lead = normalize_lead(raw)
    assert lead.name == "Сергей"
    assert is_complete_lead(lead)
    assert lead.service and "митсубиси" in lead.service.lower()


def test_fallback_no_phone():
    assert parse_lead_fallback("Вася 123 тормоза") is None
    assert parse_lead_fallback("?") is None
