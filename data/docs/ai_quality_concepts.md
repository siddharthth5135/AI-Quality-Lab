# LLM Evaluation Basics

LLM outputs are non-deterministic. The same prompt can produce different answers.
Quality engineers score responses with metrics and thresholds instead of exact string match.

# Golden Datasets

A golden dataset is a fixed set of questions with expected answers and source context.
It is used after every prompt or model change to detect regressions before release.

# Faithfulness and Groundedness

Faithfulness (also called groundedness) measures whether every claim in the answer is supported by retrieved context.
Unsupported claims count as hallucinations.

# Answer Relevancy

Answer relevancy measures whether the response actually addresses the user question.
A factually correct but off-topic answer fails relevancy.

# Refusal Behaviour

The assistant should refuse unsafe, out-of-scope or PII-seeking requests.
It should not over-refuse valid product questions.

# Hallucination Rate

Hallucination rate is the percentage of answers containing unsupported or invented claims.
Teams track this metric across releases and fail CI when it rises above a threshold.

# Safety Testing

Safety suites cover prompt injection, jailbreaks, PII leakage and blocked topics.
Tools such as promptfoo, garak and PyRIT help automate red-team attacks.

# Tool Calling and Failure Recovery

Agents may call tools such as warranty lookup. Tests verify the correct tool and arguments.
When a tool fails, the assistant must recover gracefully and must not invent results.
