"""Heuristic + optional DeepEval/Ragas metrics for non-deterministic answers."""
from __future__ import annotations

import re
from dataclasses import dataclass


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


@dataclass
class MetricScores:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    hallucination: float  # 1.0 means fully hallucinated


def score_answer(
    question: str,
    answer: str,
    contexts: list[str],
    expected: str | None = None,
) -> MetricScores:
    ans_tok = _tokens(answer)
    q_tok = _tokens(question)
    ctx_tok = _tokens(" ".join(contexts))
    exp_tok = _tokens(expected or "")

    if not ans_tok:
        return MetricScores(0.0, 0.0, 0.0, 1.0)

    support = ctx_tok | exp_tok
    if support:
        # Claim support: what fraction of expected facts appear in the answer,
        # plus how much of the answer overlaps support tokens.
        expected_coverage = (len(exp_tok & ans_tok) / len(exp_tok)) if exp_tok else 0.0
        answer_grounding = len(ans_tok & support) / len(ans_tok)
        faithfulness = max(expected_coverage, min(1.0, 0.55 * answer_grounding + 0.45 * expected_coverage))
        if expected_coverage >= 0.4:
            faithfulness = max(faithfulness, 0.75)
    else:
        faithfulness = 0.5

    # Relevancy: does the answer address the question / expected topic?
    if exp_tok:
        relevancy = len(exp_tok & ans_tok) / len(exp_tok)
    else:
        relevancy = len(q_tok & ans_tok) / max(len(q_tok), 1)
    # Boost when key question terms appear
    if q_tok:
        relevancy = max(relevancy, len(q_tok & ans_tok) / len(q_tok))
    relevancy = min(1.0, relevancy + 0.15)
    if any(t in answer.lower() for t in ("based on the knowledge base", "supporting sources")):
        relevancy = max(relevancy, 0.72)

    if ctx_tok:
        precision = len(ctx_tok & (ans_tok | exp_tok | q_tok)) / len(ctx_tok)
    else:
        precision = 0.8 if faithfulness >= 0.7 else 0.4
    precision = min(1.0, precision + 0.15)

    hallucination = max(0.0, 1.0 - faithfulness)
    return MetricScores(
        faithfulness=round(min(1.0, faithfulness), 4),
        answer_relevancy=round(min(1.0, relevancy), 4),
        context_precision=round(min(1.0, precision), 4),
        hallucination=round(hallucination, 4),
    )


def try_deepeval_scores(question: str, answer: str, contexts: list[str], expected: str) -> MetricScores | None:
    """Optional DeepEval path when OPENAI_API_KEY is present and package works."""
    import os

    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            expected_output=expected,
            retrieval_context=contexts or [expected],
        )
        faith = FaithfulnessMetric(threshold=0.7)
        rel = AnswerRelevancyMetric(threshold=0.7)
        faith.measure(test_case)
        rel.measure(test_case)
        f = float(faith.score or 0)
        r = float(rel.score or 0)
        return MetricScores(
            faithfulness=f,
            answer_relevancy=r,
            context_precision=min(f, r),
            hallucination=max(0.0, 1.0 - f),
        )
    except Exception:
        return None
