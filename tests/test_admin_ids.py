"""Проверка списка админов."""

import importlib

import config


def test_is_bot_admin_demo_mode(monkeypatch):
    monkeypatch.setenv("ADMIN_ID", "")
    monkeypatch.setenv("ADMIN_IDS", "")
    importlib.reload(config)
    assert config.is_bot_admin(1) is True
    assert config.is_bot_admin(999) is True


def test_is_bot_admin_restricted(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "111,222")
    monkeypatch.setenv("ADMIN_ID", "")
    importlib.reload(config)
    assert config.is_bot_admin(111) is True
    assert config.is_bot_admin(222) is True
    assert config.is_bot_admin(333) is False
    importlib.reload(config)  # restore project .env values for other tests
