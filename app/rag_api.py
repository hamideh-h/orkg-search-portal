# app/rag_api.py

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class RAGQueryFilters(BaseModel):
    resource_type: Optional[List[str]] = None
    contribution_type: Optional[List[str]] = None
    task: Optional[List[str]] = None
    dataset: Optional[List[str]] = None
    metric: Optional[List[str]] = None


class RAGQueryRequest(BaseModel):
    query: str
    filters: Optional[RAGQueryFilters] = None
    top_k: int = 10
    include_llm_answer: bool = True
    language: str = "en"


class RAGResultItem(BaseModel):
    paper_id: str
    title: str
    year: Optional[int] = None
    score: float
    snippet: str
    contribution_type: Optional[str] = None
    task: Optional[str] = None
    dataset: Optional[str] = None
    dataset_concept_doi: Optional[str] = None
    dataset_latest_version_doi: Optional[str] = None
    dataset_latest_version_label: Optional[str] = None
    metrics: Optional[List[str]] = None
    orkg_url: Optional[str] = None


class RAGQueryResponse(BaseModel):
    query: str
    answer: Optional[str]
    results: List[RAGResultItem]
    used_filters: Dict[str, List[str]]
    meta: Dict[str, Optional[str]]


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    """
    Online RAG endpoint:
    - embed payload.query
    - apply filters to vector search
    - fetch ORKG metadata (papers + datasets + versions)
    - optionally call LLM to generate `answer`
    """

    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    # TODO: 1) embed query
    # query_vector = embed(payload.query)

    # TODO: 2) build filter dict for vector DB from payload.filters
    used_filters: Dict[str, List[str]] = {}
    if payload.filters:
        for field, value in payload.filters.model_dump().items():
            if value:
                used_filters[field] = value

    # TODO: 3) vector search in your index (Qdrant / etc.)
    # raw_hits = vector_db.search(vector=query_vector, filters=used_filters, top_k=payload.top_k)

    # TODO: 4) for each hit, fetch ORKG metadata + resolve latest dataset version
    # Here we just return a dummy item so you see the shape
    dummy_result = RAGResultItem(
        paper_id="R12345",
        title="Dummy paper just to show the shape",
        year=2024,
        score=0.99,
        snippet="We propose a new segmentation method evaluated on Cityscapes using IoU...",
        contribution_type="new method",
        task="semantic segmentation",
        dataset="Cityscapes",
        dataset_concept_doi="10.1234/xyz",
        dataset_latest_version_doi="10.1234/xyz.v3",
        dataset_latest_version_label="v3 (2024-06-01)",
        metrics=["IoU"],
        orkg_url="https://orkg.org/resource/R12345",
    )

    # TODO: 5) call LLM with top-k snippets + metadata if include_llm_answer
    answer: Optional[str] = None
    if payload.include_llm_answer:
        # llm_context = build_context(payload.query, [dummy_result, ...])
        # answer = llm_client.generate_answer(query=payload.query, context=llm_context, language=payload.language)
        answer = (
            "This is a placeholder RAG answer. "
            "Here I would summarize relevant papers and list the newest dataset versions."
        )

    meta = {
        "top_k": str(payload.top_k),
        "retrieval_time_ms": None,   # fill later
        "llm_model": None,           # e.g. "gpt-4.1-mini"
        "vector_index": "nfdixcs_papers_v1"
    }

    return RAGQueryResponse(
        query=payload.query,
        answer=answer,
        results=[dummy_result],
        used_filters=used_filters,
        meta=meta,
    )
