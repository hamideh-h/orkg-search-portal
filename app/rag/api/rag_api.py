# app/rag/api/rag_api.py

from fastapi import APIRouter
from app.rag.schemas import RAGQueryRequest, RAGQueryResponse
from app.rag.core.engine import run_rag_query

router = APIRouter()

@router.post("/rag/query", response_model=RAGQueryResponse)
def rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    return run_rag_query(payload)
