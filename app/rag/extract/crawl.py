# app/rag/extract/crawl.py
from collections import deque
from typing import List

from app.rag.orkg.client import OrkgClient


def crawl_neighborhood(
    client: OrkgClient,
    root_id: str,
    *,
    max_depth: int,
    follow_resources: bool = True,
    page_size: int = 200,
) -> List[dict]:
    queue = deque([(root_id, 0)])
    seen = set()
    statements: List[dict] = []

    while queue:
        sid, depth = queue.popleft()
        if sid in seen or depth > max_depth:
            continue

        seen.add(sid)

        for st in client.get_all_statements(sid, page_size=page_size):
            statements.append(st)

            obj = st.get("object") or {}
            if follow_resources and obj.get("_class") == "resource" and depth < max_depth:
                oid = obj.get("id")
                if oid:
                    queue.append((oid, depth + 1))

    return statements
