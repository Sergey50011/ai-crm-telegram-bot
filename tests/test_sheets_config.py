"""Конфигурация Google Sheets (без реального API)."""

import importlib

import config
from integrations.google_sheets import sheets_integration_configured


def test_sheets_disabled_by_default(monkeypatch):
    monkeypatch.setenv("SHEETS_ENABLED", "0")
    importlib.reload(config)
    assert config.SHEETS_ENABLED is False
    assert sheets_integration_configured() is False


def test_sheets_enabled_without_file(monkeypatch):
    monkeypatch.setenv("SHEETS_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_SHEETS_ID", "abc123")
    monkeypatch.setenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE", "secrets/does-not-exist-test.json"
    )
    importlib.reload(config)
    assert sheets_integration_configured() is False
    importlib.reload(config)
