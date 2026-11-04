"""Appium Page Object Model for Android assistant smoke tests."""
from __future__ import annotations

import time


class AssistantPage:
    def __init__(self, driver):
        self.driver = driver

    def open(self, url: str) -> None:
        self.driver.get(url)
        time.sleep(0.5)

    def ask(self, question: str) -> None:
        el = self.driver.find_element("css selector", "#question")
        el.clear()
        el.send_keys(question)
        self.driver.execute_script(
            """
            const form = document.getElementById('askForm');
            form.dispatchEvent(new Event('submit', {cancelable: true, bubbles: true}));
            """
        )

    def bot_messages(self) -> list[str]:
        nodes = self.driver.find_elements("css selector", ".msg.bot")
        return [n.text for n in nodes]

    def wait_for_new_bot_message(self, previous_count: int, timeout: float = 8.0) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            msgs = self.bot_messages()
            if len(msgs) > previous_count and msgs[-1].strip():
                return msgs[-1]
            time.sleep(0.25)
        return self.bot_messages()[-1] if self.bot_messages() else ""
