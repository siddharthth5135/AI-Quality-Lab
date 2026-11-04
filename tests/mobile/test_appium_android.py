"""Appium Android smoke tests with Page Object Model.

Default CI path uses Selenium mobile emulation (Chrome) so the suite is runnable
without a local Appium server. Set RUN_APPIUM=1 and start Appium to exercise the
real Appium-Python-Client path against Chrome on Android / emulator.
"""
from __future__ import annotations

import os
import threading
import time

import pytest
import uvicorn

from app.main import app
from tests.mobile.pages.assistant_page import AssistantPage

PORT = int(os.getenv("MOBILE_TEST_PORT", "8766"))
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


@pytest.mark.mobile
def test_android_webview_ask_with_mobile_emulation(live_server):
    """POM smoke test using mobile Chrome emulation (always runnable)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=390,844")
    options.add_experimental_option(
        "mobileEmulation", {"deviceName": "Pixel 7"}
    )
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as exc:
        pytest.skip(f"Chrome WebDriver unavailable: {exc}")

    try:
        page = AssistantPage(driver)
        page.open(live_server)
        before = len(page.bot_messages())
        page.ask("How does BLE Wi-Fi provisioning work?")
        texts = page.wait_for_new_bot_message(before).lower()
        assert any(
            k in texts
            for k in ("ble", "wi-fi", "wifi", "pairing", "provision", "ssid", "password", "fan", "bluetooth")
        ), texts
    finally:
        driver.quit()


@pytest.mark.mobile
@pytest.mark.skipif(os.getenv("RUN_APPIUM") != "1", reason="Set RUN_APPIUM=1 with Appium server")
def test_appium_android_chrome(live_server):
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.browser_name = "Chrome"
    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    try:
        page = AssistantPage(driver)
        page.open(live_server)
        page.ask("What is faithfulness?")
        time.sleep(1.2)
        assert any("faithfulness" in t.lower() or "context" in t.lower() for t in page.bot_messages())
    finally:
        driver.quit()
