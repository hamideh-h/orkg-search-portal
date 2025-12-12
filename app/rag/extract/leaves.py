# app/rag/extract/leaves.py
from collections import deque
from typing import List

from app.rag.orkg.client import OrkgClient
from app.rag.extract.normalize import is_noise_value, looks_like_url

NAME_PRED = "name"


def extract_semantic_leaves(
    client: OrkgClient,
    start_id: str,
    *,
    max_depth: int,
    max_nodes: int,
) -> List[str]:
    values: List[str] = []
    queue = deque([(start_id, 0)])
    seen = set()

    while queue and len(seen) < max_nodes:
        sid, depth = queue.popleft()
        if sid in seen or depth > max_depth:
            continue

        seen.add(sid)

        for st in client.get_all_statements(sid):
            pred = st.get("predicate", {}) or {}
            obj = st.get("object", {}) or {}

            p_lbl = (pred.get("label") or pred.get("id") or "").lower()
            o_cls = obj.get("_class")
            o_lbl = (obj.get("label") or "").strip()

            if o_cls == "literal":
                if looks_like_url(o_lbl):
                    values.append(o_lbl)
                elif NAME_PRED in p_lbl:
                    if not is_noise_value(o_lbl):
                        values.append(o_lbl)
                else:
                    if o_lbl and not is_noise_value(o_lbl) and len(o_lbl) >= 4:
                        values.append(o_lbl)

            elif o_cls == "resource":
                oid = obj.get("id")
                if oid:
                    queue.append((oid, depth + 1))

    # de-duplicate preserving order
    out, seen2 = [], set()
    for v in values:
        if v not in seen2:
            out.append(v)
            seen2.add(v)

    return out
