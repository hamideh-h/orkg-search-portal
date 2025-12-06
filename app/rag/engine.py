# backend/rag/engine.py

from typing import Dict, List
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI  # or Mistral etc.

from .schemas import RAGQueryRequest, RAGResultItem, RAGQueryResponse  # pydantic models

INDEX_DIR = "storage/nfdixcs_index"

# initialize global LlamaIndex settings
Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.llm = OpenAI(model="gpt-4.1-mini")  # or whatever


def _load_index() -> VectorStoreIndex:
    storage_context = StorageContext.from_defaults(persist_dir=INDEX_DIR)
    return VectorStoreIndex.from_storage(storage_context)


_index = None  # cache

def get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        _index = _load_index()
    return _index


def run_rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    index = get_index()

    # Build query engine with metadata filters, if any
    query_engine = index.as_query_engine(
        similarity_top_k=payload.top_k,
        # You can later add metadata filters via NodePostprocessors or query_kwargs
    )

    # Run query and get LlamaIndex response
    llm_response = query_engine.query(payload.query)

    # llm_response contains:
    # - .response: generated answer (string)
    # - .source_nodes: list of nodes (each with node metadata, score, text snippet)

    results: List[RAGResultItem] = []
    used_filters: Dict[str, List[str]] = {}

    if payload.filters:
        for field, value in payload.filters.model_dump().items():
            if value:
                used_filters[field] = value

    for node_with_score in llm_response.source_nodes:
        node = node_with_score.node
        score = node_with_score.score or 0.0
        md = node.metadata or {}

        results.append(
            RAGResultItem(
                paper_id=md.get("orkg_id", ""),
                title=md.get("title", ""),
                year=md.get("year"),
                score=score,
                snippet=node.get_content(),
                contribution_type=md.get("contribution_type"),
                task=md.get("task"),
                dataset=md.get("dataset"),
                dataset_concept_doi=md.get("dataset_concept_doi"),
                dataset_latest_version_doi=md.get("dataset_latest_version_doi"),
                dataset_latest_version_label=md.get("dataset_latest_version_label"),
                metrics=md.get("metrics"),
                orkg_url=f"https://orkg.org/resource/{md.get('orkg_id')}" if md.get("orkg_id") else None,
            )
        )

    # Decide whether to use LLM answer based on include_llm_answer
    answer = llm_response.response if payload.include_llm_answer else None

    meta = {
        "top_k": str(payload.top_k),
        "llm_model": getattr(Settings.llm, "model", None),
        "vector_index": "nfdixcs_index_v1",
        "retrieval_time_ms": None,  # fill with actual timing later
    }

    return RAGQueryResponse(
        query=payload.query,
        answer=answer,
        results=results,
        used_filters=used_filters,
        meta=meta,
    )
