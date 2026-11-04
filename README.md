# AI Quality Lab

**LLM evaluation & test automation framework** for grounded RAG assistants.

Live demo + OpenAPI · Golden dataset (50) · DeepEval/Ragas-ready metrics · Safety red-team · Multi-turn & tool-calling · Playwright · Appium POM · Locust · GitHub Actions quality gate

**Repo:** [github.com/siddharthth5135/AI-Quality-Lab](https://github.com/siddharthth5135/AI-Quality-Lab)

---

## What this project proves

| Capability | Implementation |
|---|---|
| LLM evaluation | `eval/` — faithfulness, answer relevancy, context precision, hallucination rate on a 50-question golden set |
| Quality gate | `python eval/run_eval.py` + `.github/workflows/quality-gate.yml` fails CI below thresholds |
| AI safety | Prompt injection, jailbreak, PII leakage, blocked topics (`tests/safety`, `promptfoo/`) |
| Multi-turn & tools | Session memory + `lookup_warranty` success/failure recovery tests |
| API testing | Contract tests from `/openapi.json` (Swagger/OpenAPI) |
| SQL data validation | Every `/api/ask` call is logged; `tests/data` runs Athena-style SQL checks for empty answers, latency SLO, refusal reasons, PII leakage and cost fields |
| Latency, cost, drift | `eval/run_eval.py` reports p50/p95 latency, estimated token cost, and fails on >0.05 drift vs `eval/baseline.json` |
| Web UI automation | Playwright + Page Object Model |
| Android automation | Appium POM (+ mobile Chrome emulation smoke for CI) |
| Load / latency | Locust on `/api/ask` (p95) |
| Live web app | FastAPI + grounded RAG UI |

Default judge mode is **heuristic** (offline, deterministic, CI-friendly). Set `OPENAI_API_KEY` and install `requirements-optional.txt` to enable DeepEval/Ragas LLM-as-judge.

---

## Quick start

```bash
cd D:\AI-Quality-Lab
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m playwright install chromium
python scripts/generate_golden_set.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000** — UI, **http://127.0.0.1:8000/docs** — Swagger.

---

## Run the quality suite

```bash
# API + safety + agent
pytest -m "api or safety or agent"

# SQL data validation over conversation logs
pytest -m data

# Golden-set evaluation gate (exit 1 if thresholds or drift fail)
python eval/run_eval.py
python eval/run_eval.py --update-baseline   # accept current scores as the new baseline

# Playwright UI
pytest -m ui

# Mobile POM smoke (Chrome mobile emulation)
pytest -m mobile

# Locust (server must be running)
locust -f load/locustfile.py --host http://127.0.0.1:8000 --headless -u 20 -r 5 -t 60s
```

### Thresholds (quality gate)

- Faithfulness ≥ **0.70**
- Answer relevancy ≥ **0.70**
- Context precision ≥ **0.65**
- Hallucination rate ≤ **0.30**
- Case pass rate ≥ **75%**

---

## Architecture

```
app/                FastAPI RAG assistant + live UI
data/docs/          Knowledge base (Atomberg product + eval concepts)
data/golden/        50-question golden dataset
eval/               Metrics + quality gate runner
tests/safety/       Injection / jailbreak / PII / blocked topics
tests/agent/        Multi-turn + tool failure recovery
tests/api/          OpenAPI contract tests
tests/ui/           Playwright POM
tests/mobile/       Appium POM
load/               Locust
promptfoo/          Red-team YAML
.github/workflows/  CI quality gate
```

---

## Deploy

- **Docker:** `docker build -t ai-quality-lab . && docker run -p 8000:8000 ai-quality-lab`
- **Render:** `render.yaml` included (free web service)
- **Tunnel (local → public):** `cloudflared tunnel --url http://127.0.0.1:8000`

---

## Interview talking points

1. Non-deterministic outputs → metrics + thresholds, not `assert answer == expected`
2. Production failures become golden regression cases
3. Faithfulness fail example: model says “5-year warranty” while policy says 2 years
4. Tool failure must not invent results
5. CI gate blocks merge when scores drop

Built for the Atomberg AI Quality Engineer skill profile.
