# app/rag/schemas/schemas.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RAGFilters(BaseModel):
    """
    Optional filter fields.
    Keep these as lists so the UI can pass multi-select filters later.
    """
    paper_id: Optional[List[str]] = None
    year: Optional[List[int]] = None
    research_field: Optional[List[str]] = None
    author: Optional[List[str]] = None

    # Contribution-level filters
    contribution_id: Optional[List[str]] = None
    contribution_label: Optional[List[str]] = None
    level: Optional[List[str]] = None  # e.g. ["paper", "contribution"]


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query text")
    top_k: int = Field(5, ge=1, le=50, description="How many chunks to retrieve")
    include_llm_answer: bool = Field(True, description="Whether to include generated answer")

    # optional filters
    filters: Optional[RAGFilters] = None


class RAGResultItem(BaseModel):
    """
    One retrieved source chunk/node.
    """
    paper_id: str = ""
    title: str = ""
    year: Optional[int] = None
    score: float = 0.0
    snippet: str = ""

    # keep old fields for compatibility
    contribution_type: Optional[str] = None
    task: Optional[Any] = None
    dataset: Optional[Any] = None
    dataset_concept_doi: Optional[Any] = None
    dataset_latest_version_doi: Optional[Any] = None
    dataset_latest_version_label: Optional[Any] = None
    metrics: Optional[Any] = None

    orkg_url: Optional[str] = None


class RAGQueryResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: List[RAGResultItem] = Field(default_factory=list)

    used_filters: Dict[str, List[Any]] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


# -- Compatibility: models expected by the lightweight search API (app/main.py)
class ResourceItem(BaseModel):
    """Lightweight resource item used by the simple search endpoint.

    Keep fields permissive — the frontend only needs a few attributes.
    """
    id: str
    title: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    score: Optional[float] = None


class SearchResponse(BaseModel):
    total: int = 0
    page: int = 0
    size: int = 0
    items: List[ResourceItem] = Field(default_factory=list)

