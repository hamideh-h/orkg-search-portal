"""Minimal ORKG HTTP client utilities.

This module provides a small, dependency-light HTTP client wrapper used by
the extraction pipeline. It implements simple caching, pagination helpers,
and search convenience methods.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.rag.core.settings import Settings


@dataclass
class OrkgClient:
    """
    ORKG HTTP client for extraction/indexing.

    - Uses ONE requests.Session (connection pooling)
    - Supports pagination for /statements
    - Basic retries + backoff
    - In-memory cache for statements/pages (big speedup for leaf extraction)
    """

    settings: Settings
    session: requests.Session | None = None

    # caches
    _paper_cache: Dict[str, dict] = None  # type: ignore
    _statements_cache: Dict[Tuple[str, int, int], dict] = None  # type: ignore  # (subject_id, page, size) -> response

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

        if self._paper_cache is None:
            self._paper_cache = {}

        if self._statements_cache is None:
            self._statements_cache = {}

    # -------------------------
    # low-level request
    # -------------------------
    def _get_json(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """Perform a GET request and return parsed JSON with retries.

        This method centralizes timeouts, retries and exponential backoff.
        """
        timeout = timeout or self.settings.HTTP_TIMEOUT_S
        retries = max(0, self.settings.HTTP_MAX_RETRIES)
        backoff = float(self.settings.HTTP_BACKOFF_S)

        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                r = self.session.get(url, params=params, headers=headers, timeout=timeout)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
                if attempt >= retries:
                    break
                time.sleep(backoff * (2 ** attempt))

        raise last_err  # type: ignore[misc]

    # -------------------------
    # endpoints
    # -------------------------
    def get_paper(self, paper_id: str) -> dict:
        """Get paper metadata from ORKG, with in-memory caching."""
        if paper_id in self._paper_cache:
            return self._paper_cache[paper_id]

        url = f"{self.settings.ORKG_BASE_URL}/papers/{paper_id}"
        data = self._get_json(url, headers={"Accept": self.settings.PAPER_ACCEPT})
        self._paper_cache[paper_id] = data
        return data

    def get_statements_page(self, subject_id: str, *, page: int = 0, size: int = 200) -> dict:
        """Fetch a single page of statements for a subject."""
        key = (subject_id, page, size)
        if key in self._statements_cache:
            return self._statements_cache[key]

        url = f"{self.settings.ORKG_BASE_URL}/statements"
        data = self._get_json(url, params={"subject_id": subject_id, "page": page, "size": size})
        self._statements_cache[key] = data
        return data

    def get_all_statements(self, subject_id: str, *, page_size: int = 200, max_pages: int = 200) -> List[dict]:
        """Fetch ALL statements for a subject via pagination.

        max_pages prevents infinite loops if API behaves weirdly.
        """
        out: List[dict] = []
        page = 0

        while page < max_pages:
            data = self.get_statements_page(subject_id, page=page, size=page_size)
            chunk = data.get("content", []) or []
            if not chunk:
                break
            out.extend(chunk)

            # Stop if this is the last page
            total_pages = data.get("totalPages")
            if isinstance(total_pages, int) and page >= total_pages - 1:
                break

            page += 1

        return out

    # -------------------------
    # optional search helpers
    # -------------------------
    def search_resources(self, q: str, *, page: int = 0, size: int = 25, classes: str | None = None) -> dict:
        params: Dict[str, Any] = {"q": q, "page": page, "size": size}
        if classes:
            params["classes"] = classes
        url = f"{self.settings.ORKG_BASE_URL}/resources"
        return self._get_json(url, params=params)

    def search_papers_by_title(self, q: str, *, page: int = 0, size: int = 25, exact: bool = False) -> dict:
        url = f"{self.settings.ORKG_BASE_URL}/papers"
        params = {"title": q or "", "page": page, "size": size, "exact": "true" if exact else "false"}
        return self._get_json(url, params=params, headers={"Accept": self.settings.PAPER_ACCEPT})


# Convenience module-level helpers used by the lightweight API (app/main.py)
import asyncio
from typing import Any


async def search_resources(q: str, *, page: int = 0, size: int = 25, classes: str | None = None) -> dict:
    """Async wrapper around OrkgClient.search_resources returning a normalized response dict."""
    client = OrkgClient(settings)
    # run blocking HTTP in a thread
    data = await asyncio.to_thread(client.search_resources, q, page=page, size=size, classes=classes)
    # Normalize to the lightweight response shape expected by app/main.py
    return {
        "total": int(data.get("totalElements") or data.get("total") or 0),
        "page": int(data.get("page") or page),
        "size": int(data.get("size") or size),
        "items": [
            {
                "id": str(r.get("id") or r.get("resourceId") or ""),
                "title": r.get("label") or r.get("title") or "",
                "year": r.get("year"),
                "doi": r.get("doi"),
                "url": r.get("url"),
                "score": float(r.get("score") or 0.0),
            }
            for r in (data.get("content") or data.get("items") or [])
        ],
        "source": "resources",
    }


async def search_papers_hybrid(q: str, author: str | None, year_from: int | None, year_to: int | None, page: int = 0, size: int = 25) -> dict:
    """Async helper for searching papers with optional basic filters.

    This is a simple implementation that queries the ORKG papers endpoint by
    title and performs minimal post-filtering for author/year. It is intentionally
    lightweight — suitable for the quick /api/search route.
    """
    client = OrkgClient(settings)

    params = {"title": q or "", "page": page, "size": size, "exact": "false"}
    data = await asyncio.to_thread(client._get_json, f"{client.settings.ORKG_BASE_URL}/papers", params=params, headers={"Accept": client.settings.PAPER_ACCEPT})

    items = []
    for p in (data.get("content") or data.get("items") or []):
        # minimal author/year filtering
        if author:
            authors = [a.get("name") if isinstance(a, dict) else str(a) for a in (p.get("authors") or [])]
            if not any(author.lower() in (a or "").lower() for a in authors):
                continue
        if year_from and (p.get("year") is None or int(p.get("year")) < year_from):
            continue
        if year_to and (p.get("year") is None or int(p.get("year")) > year_to):
            continue

        items.append(
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "year": p.get("year"),
                "doi": p.get("doi"),
                "url": p.get("url"),
            }
        )

    return {
        "total": len(items),
        "page": page,
        "size": size,
        "items": items,
        "source": "papers_hybrid",
    }
