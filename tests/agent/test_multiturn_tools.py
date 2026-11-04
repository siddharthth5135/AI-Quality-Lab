"""Multi-turn conversation and tool-calling / failure-recovery tests."""
from __future__ import annotations

import pytest


@pytest.mark.agent
def test_multiturn_followup_uses_prior_context(client):
    sid = "multi-1"
    client.post("/api/sessions/" + sid + "/reset")
    first = client.post(
        "/api/ask",
        json={"question": "Tell me about Atomberg fan warranty", "session_id": sid},
    ).json()
    assert first["refused"] is False
    follow = client.post(
        "/api/ask",
        json={"question": "How many years for the motor?", "session_id": sid},
    ).json()
    assert follow["refused"] is False
    text = follow["answer"].lower()
    assert "2" in text or "motor" in text or "warranty" in text


@pytest.mark.agent
def test_tool_calling_success_path(client):
    res = client.post(
        "/api/ask",
        json={
            "question": "Lookup warranty for Renesa",
            "session_id": "tool-ok",
            "use_tools": True,
            "force_tool_failure": False,
        },
    )
    body = res.json()
    assert body["tool_calls"]
    assert body["tool_calls"][0]["name"] == "lookup_warranty"
    assert body["tool_calls"][0]["status"] == "ok"


@pytest.mark.agent
def test_tool_failure_recovery_does_not_invent(client):
    res = client.post(
        "/api/ask",
        json={
            "question": "Lookup warranty for Renesa",
            "session_id": "tool-fail",
            "use_tools": True,
            "force_tool_failure": True,
        },
    )
    body = res.json()
    assert body["tool_calls"][0]["status"] == "error"
    assert "failed" in body["answer"].lower()
    assert "5 year" not in body["answer"].lower()
    assert "5-year" not in body["answer"].lower()
