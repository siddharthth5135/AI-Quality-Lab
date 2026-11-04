"""Run golden-set evaluation and emit a quality-gate report.

Tracks quality (faithfulness, relevancy, context precision, hallucination),
latency (p50/p95), estimated token cost, and drift against a committed baseline.

Usage:
    python eval/run_eval.py                    # run gate
    python eval/run_eval.py --update-baseline  # accept current scores as new baseline
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.rag import DocumentStore, RAGAssistant
from eval.metrics import score_answer, try_deepeval_scores, try_ragas_scores

BASELINE = ROOT / "eval" / "baseline.json"
MAX_DRIFT = 0.05
DRIFT_KEYS = ("avg_faithfulness", "avg_answer_relevancy", "avg_context_precision", "hallucination_rate")


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


def _drift(summary: dict) -> dict:
    if not BASELINE.exists():
        return {"baseline_found": False, "regressions": []}
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    deltas = {k: round(summary[k] - baseline[k], 4) for k in DRIFT_KEYS if k in baseline}
    regressions = [
        k
        for k, d in deltas.items()
        if (k == "hallucination_rate" and d > MAX_DRIFT) or (k != "hallucination_rate" and d < -MAX_DRIFT)
    ]
    return {"baseline_found": True, "deltas": deltas, "max_allowed": MAX_DRIFT, "regressions": regressions}


def run(update_baseline: bool = False) -> dict:
    settings = get_settings()
    golden = json.loads(settings.golden_path.read_text(encoding="utf-8"))
    store = DocumentStore(settings.docs_dir)
    assistant = RAGAssistant(
        store,
        openai_api_key=settings.openai_api_key if settings.use_openai else None,
        model=settings.openai_model,
    )

    rows = []
    latencies: list[float] = []
    total_tokens = 0
    for item in golden["items"]:
        started = time.perf_counter()
        result = assistant.ask(item["question"], session_id=f"eval-{item['id']}")
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        total_tokens += (len(item["question"]) + len(result.answer)) // 4

        if item.get("should_refuse"):
            expected_reason = item.get("refusal_reason")
            ok = result.refused and (expected_reason is None or result.refusal_reason == expected_reason)
            rows.append(
                {
                    "id": item["id"],
                    "category": item.get("category"),
                    "question": item["question"],
                    "refused": result.refused,
                    "refusal_reason": result.refusal_reason,
                    "latency_ms": round(latency_ms, 2),
                    "pass": ok,
                    "faithfulness": 1.0 if ok else 0.0,
                    "answer_relevancy": 1.0 if ok else 0.0,
                    "context_precision": 1.0 if ok else 0.0,
                    "hallucination": 0.0 if ok else 1.0,
                }
            )
            continue

        contexts = [s["snippet"] for s in result.sources] or item.get("reference_contexts", [])
        args = (item["question"], result.answer, contexts, item["expected_answer"])
        judge = {"deepeval": try_deepeval_scores, "ragas": try_ragas_scores}.get(settings.eval_mode)
        scores = (judge(*args) if judge else None) or score_answer(*args)
        rows.append(
            {
                "id": item["id"],
                "category": item.get("category"),
                "question": item["question"],
                "answer": result.answer[:300],
                "latency_ms": round(latency_ms, 2),
                "faithfulness": scores.faithfulness,
                "answer_relevancy": scores.answer_relevancy,
                "context_precision": scores.context_precision,
                "hallucination": scores.hallucination,
                "pass": (
                    scores.faithfulness >= settings.faithfulness_threshold
                    and scores.answer_relevancy >= settings.relevancy_threshold
                    and scores.context_precision >= settings.context_precision_threshold
                    and scores.hallucination <= settings.hallucination_threshold
                ),
            }
        )

    n = len(rows)

    def avg(key: str) -> float:
        return round(sum(r[key] for r in rows) / n, 4)

    summary = {
        "count": n,
        "pass_rate": round(sum(1 for r in rows if r["pass"]) / n, 4),
        "avg_faithfulness": avg("faithfulness"),
        "avg_answer_relevancy": avg("answer_relevancy"),
        "avg_context_precision": avg("context_precision"),
        "hallucination_rate": avg("hallucination"),
        "latency_p50_ms": round(statistics.median(latencies), 2),
        "latency_p95_ms": round(_percentile(latencies, 95), 2),
        "est_tokens": total_tokens,
        "est_cost_usd": round(total_tokens / 1000 * settings.cost_per_1k_tokens_usd, 6),
        "thresholds": {
            "faithfulness": settings.faithfulness_threshold,
            "answer_relevancy": settings.relevancy_threshold,
            "context_precision": settings.context_precision_threshold,
            "hallucination_rate_max": settings.hallucination_threshold,
        },
    }
    drift = _drift(summary)
    gate_pass = (
        summary["avg_faithfulness"] >= settings.faithfulness_threshold
        and summary["avg_answer_relevancy"] >= settings.relevancy_threshold
        and summary["avg_context_precision"] >= settings.context_precision_threshold
        and summary["hallucination_rate"] <= settings.hallucination_threshold
        and summary["pass_rate"] >= 0.75
        and not drift["regressions"]
    )

    if update_baseline:
        BASELINE.write_text(json.dumps({k: summary[k] for k in DRIFT_KEYS}, indent=2), encoding="utf-8")

    report = {"gate_pass": gate_pass, "summary": summary, "drift": drift, "results": rows}
    out = ROOT / "reports" / "eval_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    drift_line = (
        "no regressions vs baseline" if not drift["regressions"] else "REGRESSED: " + ", ".join(drift["regressions"])
    )
    (ROOT / "reports" / "eval_report.md").write_text(
        "\n".join(
            [
                "# AI Quality Lab — Evaluation Report",
                "",
                f"- Gate pass: **{gate_pass}**",
                f"- Pass rate: {summary['pass_rate']:.2%}",
                f"- Faithfulness: {summary['avg_faithfulness']:.3f}",
                f"- Answer relevancy: {summary['avg_answer_relevancy']:.3f}",
                f"- Context precision: {summary['avg_context_precision']:.3f}",
                f"- Hallucination rate: {summary['hallucination_rate']:.3f}",
                f"- Latency p50 / p95: {summary['latency_p50_ms']} ms / {summary['latency_p95_ms']} ms",
                f"- Estimated cost: ${summary['est_cost_usd']} ({summary['est_tokens']} tokens)",
                f"- Drift: {drift_line}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({**summary, "drift": drift}, indent=2))
    print(f"gate_pass={gate_pass}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    report = run(update_baseline=parser.parse_args().update_baseline)
    raise SystemExit(0 if report["gate_pass"] else 1)
