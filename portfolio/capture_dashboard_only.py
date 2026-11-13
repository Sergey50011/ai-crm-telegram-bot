"""Дособрать скрины дашборда."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "portfolio-screenshots" / "03-web-dashboard"
TMP = ROOT / "portfolio" / "_shot_tmp.png"


def save(page, locator, dest: Path) -> None:
    locator.screenshot(path=str(TMP))
    shutil.copy2(TMP, dest)


def main() -> None:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    flask = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py")],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)
            page.set_viewport_size({"width": 1440, "height": 1300})
            page.goto("http://127.0.0.1:5000", wait_until="networkidle")
            page.wait_for_selector('tr[data-row-id]', timeout=20000)
            page.wait_for_timeout(800)

            page.screenshot(path=str(TMP))
            shutil.copy2(TMP, OUT / "01-dashboard-full-page.png")
            save(page, page.locator(".mb-8.grid.gap-4").first, OUT / "02-stats-three-cards.png")
            save(
                page,
                page.locator(".overflow-hidden.rounded-2xl.border").first,
                OUT / "03-leads-table-and-header.png",
            )

            lead_id = page.locator('tr[data-row-id]').last.get_attribute("data-row-id")
            row = page.locator(f'tr[data-row-id="{lead_id}"]')
            row.scroll_into_view_if_needed()
            save(page, row, OUT / "04-status-row-before-new.png")
            page.select_option(f'select[data-lead-id="{lead_id}"]', "in_progress")
            page.wait_for_timeout(1000)
            save(page, row, OUT / "05-status-row-after-in-progress.png")
            save(page, page.locator(".mb-8.grid.gap-4").first, OUT / "06-stats-after-status-update.png")
            browser.close()
    finally:
        flask.terminate()
        if TMP.is_file():
            TMP.unlink()
    print("Dashboard PNG updated")


if __name__ == "__main__":
    main()
