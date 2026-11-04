"""REST API tests derived from the OpenAPI / Swagger contract."""
from __future__ import annotations

import pytest


@pytest.mark.api
def test_openapi_available(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"]
    paths = spec["paths"]
    assert "/api/ask" in paths
    assert "/health" in paths
    ask = paths["/api/ask"]["post"]
    assert "AskRequest" in str(ask) or "application/json" in str(ask)


@pytest.mark.api
def test_health_contract(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["docs_indexed"] > 0
    assert "version" in body


@pytest.mark.api
def test_ask_validation_empty_rejected(client):
    res = client.post("/api/ask", json={"question": ""})
    assert res.status_code == 422


@pytest.mark.api
def test_ask_returns_schema_fields(client):
    res = client.post("/api/ask", json={"question": "What is faithfulness?"})
    assert res.status_code == 200
    body = res.json()
    for key in ("answer", "sources", "refused", "model", "grounded", "tool_calls"):
        assert key in body


@pytest.mark.api
def test_docs_list(client):
    res = client.get("/api/docs/list")
    assert res.status_code == 200
    assert res.json()["count"] > 0
