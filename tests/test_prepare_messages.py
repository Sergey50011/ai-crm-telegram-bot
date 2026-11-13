"""Тексты отказа после prepare_lead_from_text."""

from leads_service import PreparedLeadResult, message_for_prepare_failure
from lead_validation import LLM_UNAVAILABLE_HINT, REJECT_HINT, SPAM_HINT


def test_message_spam():
    block = "\n".join(
        ["Марина, 89152223344, Kia Rio — скрипят колодки, пятница после 15:00"] * 4
    )
    result = PreparedLeadResult(ok=False, rejected=True)
    assert message_for_prepare_failure(block, result) == SPAM_HINT


def test_message_llm_failed():
    result = PreparedLeadResult(ok=False, parse_failed=True)
    assert message_for_prepare_failure("Марина 89152223344 тормоза", result) == LLM_UNAVAILABLE_HINT


def test_message_validation_failed():
    result = PreparedLeadResult(ok=False, rejected=True)
    assert message_for_prepare_failure("Вася 123 тормоза", result) == REJECT_HINT
