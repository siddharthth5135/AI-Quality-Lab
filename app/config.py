from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "AI Quality Lab"
    app_version: str = "1.0.0"
    docs_dir: Path = ROOT / "data" / "docs"
    golden_path: Path = ROOT / "data" / "golden" / "golden_set.json"
    log_db_path: Path = ROOT / "reports" / "conversations.db"
    cost_per_1k_tokens_usd: float = 0.00015
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    use_openai: bool = False  # set USE_OPENAI=true to enable live LLM generation
    eval_mode: str = "heuristic"  # heuristic | deepeval | ragas
    faithfulness_threshold: float = 0.70
    relevancy_threshold: float = 0.70
    hallucination_threshold: float = 0.30  # max allowed rate
    context_precision_threshold: float = 0.65
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
