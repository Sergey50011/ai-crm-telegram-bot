"""
Снятие PNG для портфолио (Playwright).
Запуск из корня проекта: python portfolio/capture_screenshots.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCKUPS = Path(__file__).resolve().parent / "mockups"
OUT = ROOT / "portfolio-screenshots"

TELEGRAM_SHOTS = [
    ("01-start.html", "01-telegram-dialog", "01-start-welcome.png"),
    ("02-lead-marina.html", "01-telegram-dialog", "02-lead-marina-brakes.png"),
    ("03-lead-oleg.html", "01-telegram-dialog", "03-lead-oleg-oil-change.png"),
    ("04-parse-error.html", "01-telegram-dialog", "04-clarify-then-success.png"),
    ("05-admin.html", "02-telegram-admin", "01-admin-recent-leads.png"),
]

DB_SHOTS = [
    ("database-browser.html", "04-database", "01-table-schema-status-column.png"),
    ("database-data.html", "04-database", "02-leads-data-all-statuses.png"),
]


def ensure_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


TMP = Path(__file__).resolve().parent / "_shot_tmp.png"


def _save_tmp(page, target: Path, *, clip: dict | None = None, locator=None) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if locator is not None:
        locator.screenshot(path=str(TMP))
    elif clip:
        page.screenshot(path=str(TMP), clip=clip)
    else:
        page.screenshot(path=str(TMP))
    shutil.copy2(TMP, target)
    return target


def shot_html(page, html_name: str, subdir: str, filename: str) -> Path:
    target = OUT / subdir / filename
    path = MOCKUPS / html_name
    page.goto(path.as_uri(), wait_until="networkidle")
    page.wait_for_timeout(300)
    frame = page.locator(".frame, .window").first
    box = frame.bounding_box()
    if box:
        clip = {
            "x": max(0, box["x"] - 24),
            "y": max(0, box["y"] - 24),
            "width": box["width"] + 48,
            "height": box["height"] + 48,
        }
        _save_tmp(page, target, clip=clip)
    else:
        _save_tmp(page, target)
    return target


def main() -> None:
    ensure_playwright()
    from playwright.sync_api import sync_playwright

    # Демо-данные
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "portfolio" / "seed_demo_data.py"),
            "--replace",
        ]
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)
            for html, subdir, name in TELEGRAM_SHOTS:
                shot_html(page, html, subdir, name)
                print("OK", subdir, name)
            shot_html(page, "database-browser.html", *DB_SHOTS[0][1:])
            print("OK", DB_SHOTS[0][1], DB_SHOTS[0][2])
            browser.close()

        subprocess.check_call(
            [sys.executable, str(ROOT / "portfolio" / "capture_dashboard_only.py")]
        )
        subprocess.check_call(
            [sys.executable, str(ROOT / "portfolio" / "export_db_mock.py")]
        )

        with sync_playwright() as p:
            page = p.chromium.launch().new_page(device_scale_factor=2)
            shot_html(page, "database-data.html", *DB_SHOTS[1][1:])
            print("OK", DB_SHOTS[1][1], DB_SHOTS[1][2])
    finally:
        if TMP.is_file():
            TMP.unlink()

    # Тест API
    subprocess.check_call(
        [
            sys.executable,
            "-c",
            "from app import app; c=app.test_client(); "
            "assert c.get('/api/stats').status_code==200; "
            "r=c.patch('/api/leads/1/status', json={'status':'in_progress'}); "
            "assert r.status_code==200",
        ],
        cwd=str(ROOT),
    )
    print("API test OK")
    print(f"Скрины сохранены в {OUT}")


if __name__ == "__main__":
    main()
