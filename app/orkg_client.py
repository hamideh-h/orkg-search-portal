import httpx
from typing import Dict, Any, Optional, List, Set

RESOURCES_BASE = "https://orkg.org/api/resources"
PAPERS_BASE = "https://orkg.org/api/papers"


# ---------- Generic resources ----------
async def search_resources(q: str, page=0, size=25, classes: Optional[str] = None) -> Dict[str, Any]:
    params = {"q": q, "page": page, "size": size}
    if classes:
        params["classes"] = classes
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(RESOURCES_BASE, params=params)
        r.raise_for_status()
        data = r.json()
    items = [{"id": it.get("id"), "label": it.get("label"), "classes": it.get("classes") or []}
             for it in data.get("content", []) if it.get("id")]
    return {"total": data.get("totalElements", len(items)), "page": page, "size": size, "items": items}


# ---------- Papers helpers ----------
async def _papers_call(params: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Accept": "application/vnd.orkg.paper.v2+json"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        r = await client.get(PAPERS_BASE, params=params)
        r.raise_for_status()
        return r.json()


def _pack_papers(data: Dict[str, Any], page: int, size: int) -> Dict[str, Any]:
    items = [{"id": p.get("id"), "label": p.get("title") or p.get("label"), "classes": ["Paper"]}
             for p in data.get("content", []) if p.get("id")]
    return {"total": data.get("totalElements", len(items)), "page": page, "size": size, "items": items}


# ---------- Hybrid logic ----------
async def search_papers_hybrid(
    q: str,
    author: Optional[str],
    year_from: Optional[int],
    year_to: Optional[int],
    page: int,
    size: int
) -> Dict[str, Any]:
    """
    Robust hybrid: always fetch by title and filter locally by author/year.
    """
    headers = {"Accept": "application/vnd.orkg.paper.v2+json"}
    base = "https://orkg.org/api/papers"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        params = {"title": q or "", "exact": "false", "page": page, "size": size}
        r = await client.get(base, params=params)
        r.raise_for_status()
        data = r.json()

    papers = data.get("content", [])
    author_norm = author.lower() if author else None
    y_from = int(year_from) if year_from else None
    y_to = int(year_to) if year_to else None

    filtered = []
    for p in papers:
        year = p.get("year")
        authors = [a.get("name", "").lower() for a in p.get("authors", [])]
        if author_norm and not any(author_norm in a for a in authors):
            continue
        if y_from and (not year or int(year) < y_from):
            continue
        if y_to and (not year or int(year) > y_to):
            continue
        filtered.append(p)

    items = [
        {"id": p.get("id"), "label": p.get("title") or p.get("label"), "classes": ["Paper"]}
        for p in filtered
        if p.get("id")
    ]

    return {
        "source": "papers_filtered",
        "total": len(items),
        "page": page,
        "size": size,
        "items": items,
    }

