"""Pytest wrapper around the golden-set evaluation gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.run_eval import run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.eval
def test_golden_dataset_exists():
    data = json.loads((ROOT / "data" / "golden" / "golden_set.json").read_text(encoding="utf-8"))
    assert data["count"] == 50
    assert len(data["items"]) == 50


@pytest.mark.eval
def test_quality_gate_passes():
    report = run()
    assert report["gate_pass"] is True
    assert report["summary"]["avg_faithfulness"] >= 0.70
    assert report["summary"]["hallucination_rate"] <= 0.30
