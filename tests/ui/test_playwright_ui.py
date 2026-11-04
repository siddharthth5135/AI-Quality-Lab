"""Playwright UI tests (Page Object Model)."""
from __future__ import annotations

import os
import threading
import time

import pytest
import uvicorn

from app.main import app
from tests.ui.pages.home_page import HomePage

PORT = int(os.getenv("UI_TEST_PORT", "8765"))
BASE = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def live_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(40):
        try:
            import httpx

            if httpx.get(f"{BASE}/health", timeout=0.5).status_code == 200:
                break
        except Exception:
            time.sleep(0.25)
    yield BASE
    server.should_exit = True


@pytest.mark.ui
def test_ui_ask_warranty(live_server):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        home = HomePage(page)
        home.open(live_server)
        assert home.health_ok()
        home.ask("What is the fan warranty period?")
        page.wait_for_timeout(800)
        text = home.last_bot_message().lower()
        assert "warranty" in text or "2" in text
        assert "sources" in home.inspect_text().lower() or "grounded" in home.inspect_text().lower()
        browser.close()


@pytest.mark.ui
def test_ui_injection_chip(live_server):
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        home = HomePage(page)
        home.open(live_server)
        page.click("text=Injection test")
        page.wait_for_timeout(800)
        assert "refuse" in home.inspect_text().lower() or "instruction" in home.last_bot_message().lower()
        browser.close()
