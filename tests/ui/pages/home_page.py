"""Page Object Model for the AI Quality Lab web UI."""
from __future__ import annotations


class HomePage:
    def __init__(self, page):
        self.page = page

    def open(self, base_url: str) -> None:
        self.page.goto(base_url)
        self.page.wait_for_selector("#askForm")

    def ask(self, question: str) -> None:
        self.page.fill("#question", question)
        self.page.click("#askForm button[type=submit]")
        self.page.wait_for_timeout(500)

    def last_bot_message(self) -> str:
        bots = self.page.locator(".msg.bot")
        return bots.nth(bots.count() - 1).inner_text()

    def inspect_text(self) -> str:
        return self.page.locator("#inspect").inner_text()

    def health_ok(self) -> bool:
        return "ok" in self.page.locator("#healthPill").inner_text().lower()
