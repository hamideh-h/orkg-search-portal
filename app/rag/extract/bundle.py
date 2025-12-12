# app/rag/extract/bundle.py
from collections import defaultdict
from typing import Any, Dict

from app.rag.extract.crawl import crawl_neighborhood
from app.rag.extract.classify import classify_statement
from app.rag.extract.leaves import extract_semantic_leaves
from app.rag.extract.normalize import is_noise_value
from app.rag.extract.rules import ExtractionRules
from app.rag.orkg.client import OrkgClient
from app.rag.core.settings import settings


def _normalize_statement(st: dict) -> dict:
    subj = st.get("subject") or {}
    pred = st.get("predicate") or {}
    obj = st.get("object") or {}

    return {
        "subject_id": subj.get("id"),
        "predicate_label": pred.get("label") or pred.get("id"),
        "predicate_id": pred.get("id"),
        "object": {
            "id": obj.get("id"),
            "label": obj.get("label"),
            "class": obj.get("_class"),
        },
    }


def _compact_bucket(client: OrkgClient, items: list[dict]) -> list[str]:
    values: list[str] = []

    for x in items:
        obj = x["object"]
        ocls = obj.get("class")
        oid = obj.get("id")
        olbl = (obj.get("label") or "").strip()

        if ocls == "resource" and oid:
            values.extend(
                extract_semantic_leaves(
                    client,
                    oid,
                    max_depth=settings.LEAVES_MAX_DEPTH,
                    max_nodes=settings.LEAVES_MAX_NODES,
                )
            )
        elif ocls == "literal":
            if olbl and not is_noise_value(olbl):
                values.append(olbl)

    out, seen = [], set()
    for v in values:
        if v not in seen:
            out.append(v)
            seen.add(v)

    return out


def extract_contribution_bundle(
    client: OrkgClient,
    contribution_id: str,
    contribution_label: str,
    *,
    rules: ExtractionRules,
) -> Dict[str, Any]:
    stmts = crawl_neighborhood(
        client,
        contribution_id,
        max_depth=settings.CRAWL_MAX_DEPTH,
        page_size=settings.STATEMENTS_PAGE_SIZE,
    )

    buckets = defaultdict(list)

    for st in stmts:
        bucket = classify_statement(
            st,
            rules,
            contribution_label=contribution_label,
        )
        buckets[bucket].append(_normalize_statement(st))

    compact = {
        "problems": _compact_bucket(client, buckets.get("problem", [])),
        "methods": _compact_bucket(client, buckets.get("method", [])),
        "data": _compact_bucket(client, buckets.get("data", [])),
        "evaluation": _compact_bucket(client, buckets.get("evaluation", [])),
        "artifacts": _compact_bucket(client, buckets.get("artifact", [])),
    }

    # leakage guard
    ev = set(compact["evaluation"])
    compact["methods"] = [m for m in compact["methods"] if m not in ev]

    return {
        "id": contribution_id,
        "label": contribution_label,
        "compact": compact,
        "buckets": dict(buckets),
    }
