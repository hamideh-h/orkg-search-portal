from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import SearchResponse, ResourceItem
from app.orkg_client import (
    search_resources,
    search_papers_hybrid,
)
from rag_api import router as rag_router

app = FastAPI(title="ORKG Search API")
app.include_router(rag_router)



# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/search", response_model=SearchResponse)
async def api_search(
    response: Response,
    q: str = Query(..., min_length=1),
    page: int = Query(0, ge=0),
    size: int = Query(25, ge=1, le=500),
    classes: str | None = Query(None, description="Comma-separated classes, e.g. Paper,Software"),
    author: str | None = Query(None, description="Optional author substring (for Paper)"),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
):
    """
    - If only `q` (and Paper): /api/papers (fast)
    - If author or year given: fallback to /api/resources (generic)
    - Other classes: /api/resources
    """
    try:
        cls_list = [c.strip() for c in (classes.split(",") if classes else []) if c.strip()]
        cls_norm = [c.lower() for c in cls_list]
        wants_paper_only = (len(cls_norm) == 1 and cls_norm[0] == "paper")

        if wants_paper_only:
            data = await search_papers_hybrid(q, author, year_from, year_to, page, size)
            response.headers["X-Source"] = data["source"]
            return SearchResponse(
                total=data["total"],
                page=data["page"],
                size=data["size"],
                items=[ResourceItem(**it) for it in data["items"]],
            )

        response.headers["X-Source"] = "resources"
        data = await search_resources(q=q, page=page, size=size, classes=",".join(cls_list) if cls_list else None)
        return SearchResponse(
            total=data["total"],
            page=data["page"],
            size=data["size"],
            items=[ResourceItem(**it) for it in data["items"]],
        )

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream ORKG error: {e}")
