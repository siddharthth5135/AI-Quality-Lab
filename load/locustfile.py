"""Locust load test for /api/ask — track p95 latency under concurrent users."""
from __future__ import annotations

from locust import HttpUser, between, task


class AssistantUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def ask_warranty(self):
        self.client.post(
            "/api/ask",
            json={"question": "What is the fan warranty period?", "session_id": "load"},
            name="/api/ask:warranty",
        )

    @task(2)
    def ask_eval(self):
        self.client.post(
            "/api/ask",
            json={"question": "What is faithfulness in LLM evaluation?", "session_id": "load"},
            name="/api/ask:eval",
        )

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
