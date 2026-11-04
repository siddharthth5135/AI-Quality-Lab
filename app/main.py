"""FastAPI application: live RAG demo + OpenAPI surface for tests."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logstore import ConversationLog
from app.rag import DocumentStore, RAGAssistant

settings = get_settings()
store = DocumentStore(settings.docs_dir)
conversation_log = ConversationLog(settings.log_db_path)
assistant = RAGAssistant(
    store,
    openai_api_key=settings.openai_api_key if settings.use_openai else None,
    model=settings.openai_model,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI Quality Lab demo: grounded RAG assistant with evaluation hooks for "
        "faithfulness, relevancy, hallucination, safety, multi-turn and tool calling."
    ),
    openapi_tags=[
        {"name": "chat", "description": "Ask the RAG assistant"},
        {"name": "health", "description": "Service health"},
        {"name": "eval", "description": "Evaluation helpers"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What is the fan warranty?"])
    session_id: str = "default"
    use_tools: bool = False
    force_tool_failure: bool = False


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    refused: bool
    refusal_reason: str | None = None
    tool_calls: list[dict[str, Any]] = []
    model: str
    grounded: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    docs_indexed: int
    eval_mode: str


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        docs_indexed=len(store.chunks),
        eval_mode=settings.eval_mode,
    )


@app.post("/api/ask", response_model=AskResponse, tags=["chat"])
def ask(payload: AskRequest) -> AskResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")
    started = time.perf_counter()
    result = assistant.ask(
        payload.question.strip(),
        session_id=payload.session_id,
        use_tools=payload.use_tools,
        force_tool_failure=payload.force_tool_failure,
    )
    conversation_log.record(
        session_id=payload.session_id,
        question=payload.question.strip(),
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        model=result.model,
        latency_ms=(time.perf_counter() - started) * 1000,
    )
    return AskResponse(
        answer=result.answer,
        sources=result.sources,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        tool_calls=result.tool_calls,
        model=result.model,
        grounded=result.grounded,
    )


@app.post("/api/sessions/{session_id}/reset", tags=["chat"])
def reset_session(session_id: str) -> dict[str, str]:
    assistant.sessions.pop(session_id, None)
    return {"status": "reset", "session_id": session_id}


@app.get("/api/docs/list", tags=["eval"])
def list_docs() -> dict[str, Any]:
    return {
        "count": len(store.chunks),
        "chunks": [
            {"doc_id": c.doc_id, "section": c.section, "path": c.path}
            for c in store.chunks
        ],
    }


@app.get("/openapi.json", include_in_schema=False)
def openapi_alias() -> dict:
    return app.openapi()
