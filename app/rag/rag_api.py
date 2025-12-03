# backend/rag_api.py

from fastapi import APIRouter
from .schemas import RAGQueryRequest, RAGQueryResponse
from .engine import run_rag_query

router = APIRouter()

@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    return run_rag_query(payload)
