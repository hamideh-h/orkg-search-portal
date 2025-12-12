# app/rag/core/settings.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default


@dataclass(frozen=True)
class Settings:
    """
    Central configuration for ORKG indexing + RAG runtime.

    Keep this file dependency-light and importable everywhere.
    Avoid importing FastAPI, LlamaIndex, etc. here.
    """

    # ---- project paths ----
    # This resolves to: .../Search_ORKG/app/rag/core/settings.py -> .../Search_ORKG/app
    APP_DIR: Path = Path(__file__).resolve().parents[2]
    RAG_DIR: Path = Path(__file__).resolve().parents[1]

    # Data only (should be gitignored)
    STORAGE_DIR: Path = RAG_DIR / "storage"
    INDEX_DIR: Path = STORAGE_DIR / "nfdixcs_index"
    EXPORTS_DIR: Path = STORAGE_DIR / "exports"      # optional: JSON/JSONL outputs
    CACHE_DIR: Path = STORAGE_DIR / "cache"          # optional: http cache, etc.

    # ---- ORKG ----
    ORKG_BASE_URL: str = _env_str("ORKG_BASE_URL", "https://sandbox.orkg.org/api")
    PAPER_ACCEPT: str = _env_str("ORKG_PAPER_ACCEPT", "application/vnd.orkg.paper.v2+json")
    HTTP_TIMEOUT_S: int = _env_int("ORKG_HTTP_TIMEOUT_S", 30)
    HTTP_MAX_RETRIES: int = _env_int("ORKG_HTTP_MAX_RETRIES", 3)
    HTTP_BACKOFF_S: float = float(_env_str("ORKG_HTTP_BACKOFF_S", "0.6"))

    # ---- crawl limits (avoid runaway graphs) ----
    CRAWL_MAX_DEPTH: int = _env_int("CRAWL_MAX_DEPTH", 4)
    STATEMENTS_PAGE_SIZE: int = _env_int("STATEMENTS_PAGE_SIZE", 200)
    LEAVES_MAX_DEPTH: int = _env_int("LEAVES_MAX_DEPTH", 6)
    LEAVES_MAX_NODES: int = _env_int("LEAVES_MAX_NODES", 400)

    # ---- indexing ----
    # Write debug bundle json or not
    WRITE_BUNDLE_JSON: bool = _env_bool("WRITE_BUNDLE_JSON", True)
    WRITE_JSONL_DOCS: bool = _env_bool("WRITE_JSONL_DOCS", True)

    # ---- runtime ----
    # If you later add LLM keys, keep them optional and loaded from env
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY") or None

    def ensure_dirs(self) -> None:
        """Create storage folders if missing."""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)


# A single shared instance you can import everywhere
settings = Settings()
