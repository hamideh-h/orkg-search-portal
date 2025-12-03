from typing import Dict, List, Optional
from pydantic import BaseModel

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
