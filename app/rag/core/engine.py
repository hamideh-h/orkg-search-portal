"""RAG engine helpers and entrypoint.

Provides a single function `run_rag_query` used by the API. Handles lazy
initialization of LlamaIndex-related settings and the persisted index.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from threading import Lock

from llama_index.core import VectorStoreIndex, StorageContext, Settings as LlamaSettings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.rag.core.settings import settings
from app.rag.schemas.schemas import RAGQueryRequest, RAGResultItem, RAGQueryResponse  # adjust if your path differs

_index = None
_index_lock = Lock()

LlamaSettings.llm = None  # retrieval-only mode
# -------------------------
# LlamaIndex global config (lazy init)
# -------------------------

_llama_inited = False
_llama_init_lock = Lock()

def _init_llama_once() -> None:
    global _llama_inited
    if _llama_inited:
        return
    with _llama_init_lock:
        if _llama_inited:
            return

        # Local embeddings (no OpenAI)
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Retrieval-only mode (no LLM -> no OpenAI key needed)
        LlamaSettings.llm = None

        _llama_inited = True


def _load_index() -> VectorStoreIndex:
    settings.ensure_dirs()
    persist_dir = str(settings.INDEX_DIR)  # absolute, stable
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    # Use getattr to avoid static-analysis errors if the installed llama_index
    # version exposes a different API. If the method is unavailable, raise a
    # helpful error at runtime.
    loader = getattr(VectorStoreIndex, "from_storage", None)
    if callable(loader):
        return loader(storage_context)
    raise RuntimeError("VectorStoreIndex.from_storage is unavailable in the installed llama_index package. Please install a compatible version.")


def get_index() -> VectorStoreIndex:
    global _index
    global _index_lock
    if _index is not None:
        return _index

    with _index_lock:
        if _index is None:
            _init_llama_once()
            _index = _load_index()
    return _index


# -------------------------
# Helpers: metadata mapping (old + new)
# -------------------------

def _md_first(md: dict, *keys: str, default=None):
    for k in keys:
        v = md.get(k)
        if v is not None and v != "":
            return v
    return default



def _orkg_url(paper_id: Optional[str], contribution_id: Optional[str] = None) -> Optional[str]:
    # Choose what we want to link to:
    # - paper: https://orkg.org/paper/<id>
    # - resource: https://orkg.org/resource/<id>
    # ORKG often uses /paper/<id> and /resource/<id>. Here we prefer contribution/resource if available.
    if contribution_id:
        return f"https://orkg.org/resource/{contribution_id}"
    if paper_id:
        return f"https://orkg.org/paper/{paper_id}"
    return None


# -------------------------
# Main entry
# -------------------------

def run_rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    index = get_index()

    query_engine = index.as_query_engine(
        similarity_top_k=payload.top_k,
    )

    llm_response = query_engine.query(payload.query)

    results: List[RAGResultItem] = []
    used_filters: Dict[str, List[str]] = {}

    if payload.filters:
        for field, value in payload.filters.model_dump().items():
            if value:
                used_filters[field] = value

    for nws in llm_response.source_nodes:
        node = nws.node
        score = float(nws.score or 0.0)
        md = node.metadata or {}

        # Support both old and new metadata keys
        paper_id = _md_first(md, "paper_id", "orkg_id", "id")
        title = _md_first(md, "paper_title", "title", "label")
        year = _md_first(md, "year")
        contribution_id = _md_first(md, "contribution_id")
        contribution_label = _md_first(md, "contribution_label", "contribution_type")

        results.append(
            RAGResultItem(
                paper_id=paper_id or "",
                title=title or "",
                year=year,
                score=score,
                snippet=node.get_content(),

                # If the schema still expects these old fields,
                #
                contribution_type=contribution_label,
                task=md.get("task"),
                dataset=md.get("dataset"),
                dataset_concept_doi=md.get("dataset_concept_doi"),
                dataset_latest_version_doi=md.get("dataset_latest_version_doi"),
                dataset_latest_version_label=md.get("dataset_latest_version_label"),
                metrics=md.get("metrics"),

                orkg_url=_orkg_url(paper_id, contribution_id),
            )
        )

    answer = llm_response.response if payload.include_llm_answer else None

    meta = {
        "top_k": str(payload.top_k),
        "llm_model": getattr(LlamaSettings.llm, "model", None),
        "vector_index": settings.INDEX_DIR.name,
        "retrieval_time_ms": None,
    }

    return RAGQueryResponse(
        query=payload.query,
        answer=answer,
        results=results,
        used_filters=used_filters,
        meta=meta,
    )
