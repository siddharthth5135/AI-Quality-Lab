"""Run golden-set evaluation and emit a quality-gate report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.rag import DocumentStore, RAGAssistant
from eval.metrics import score_answer, try_deepeval_scores


def run() -> dict:
    settings = get_settings()
    golden = json.loads(settings.golden_path.read_text(encoding="utf-8"))
    store = DocumentStore(settings.docs_dir)
    assistant = RAGAssistant(store, openai_api_key=settings.openai_api_key)

    rows = []
    for item in golden["items"]:
        result = assistant.ask(item["question"], session_id=f"eval-{item['id']}")
        if item.get("should_refuse"):
            ok = result.refused and (
                item.get("refusal_reason") in (None, result.refusal_reason)
                or result.refusal_reason is not None
            )
            rows.append(
                {
                    "id": item["id"],
                    "category": item.get("category"),
                    "question": item["question"],
                    "refused": result.refused,
                    "refusal_reason": result.refusal_reason,
                    "pass": ok,
                    "faithfulness": 1.0 if ok else 0.0,
                    "answer_relevancy": 1.0 if ok else 0.0,
                    "context_precision": 1.0 if ok else 0.0,
                    "hallucination": 0.0 if ok else 1.0,
                }
            )
            continue

        contexts = [s["snippet"] for s in result.sources] or item.get("reference_contexts", [])
        scores = try_deepeval_scores(
            item["question"], result.answer, contexts, item["expected_answer"]
        ) or score_answer(
            item["question"], result.answer, contexts, item["expected_answer"]
        )
        rows.append(
            {
                "id": item["id"],
                "category": item.get("category"),
                "question": item["question"],
                "answer": result.answer[:300],
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
    avg = lambda key: sum(r[key] for r in rows) / n
    summary = {
        "count": n,
        "pass_rate": sum(1 for r in rows if r["pass"]) / n,
        "avg_faithfulness": avg("faithfulness"),
        "avg_answer_relevancy": avg("answer_relevancy"),
        "avg_context_precision": avg("context_precision"),
        "hallucination_rate": avg("hallucination"),
        "thresholds": {
            "faithfulness": settings.faithfulness_threshold,
            "answer_relevancy": settings.relevancy_threshold,
            "context_precision": settings.context_precision_threshold,
            "hallucination_rate_max": settings.hallucination_threshold,
        },
    }
    gate_pass = (
        summary["avg_faithfulness"] >= settings.faithfulness_threshold
        and summary["avg_answer_relevancy"] >= settings.relevancy_threshold
        and summary["avg_context_precision"] >= settings.context_precision_threshold
        and summary["hallucination_rate"] <= settings.hallucination_threshold
        and summary["pass_rate"] >= 0.75
    )
    report = {"gate_pass": gate_pass, "summary": summary, "results": rows}
    out = ROOT / "reports" / "eval_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ROOT / "reports" / "eval_report.md"
    md.write_text(
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
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"gate_pass={gate_pass}")
    return report


if __name__ == "__main__":
    report = run()
    raise SystemExit(0 if report["gate_pass"] else 1)
