# app/rag/extract/bundle.py
from collections import defaultdict
from typing import Any, Dict, Optional, List

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


# -------------------------
# Template-agnostic paper-level extraction
# -------------------------


def merge_paper_core_from_contributions(contribs: List[dict]) -> dict:
    """
    Merge contribution-level `compact` results into a single paper-level core dict.

    - Keeps insertion order and avoids duplicates.
    - Applies a simple leakage guard: anything appearing in evaluation is removed from methods.
    """
    merged = {"problems": [], "methods": [], "data": [], "evaluation": [], "artifacts": []}

    def add_unique(key: str, vals: list[str]):
        seen = set(merged[key])
        for v in vals:
            if v not in seen:
                merged[key].append(v)
                seen.add(v)

    for c in contribs:
        comp = c.get("compact", {})
        for k in merged.keys():
            add_unique(k, comp.get(k, []))

    # leakage guard at paper level too
    ev2 = set(merged["evaluation"])
    merged["methods"] = [m for m in merged["methods"] if m not in ev2]

    return merged


def extract_template_agnostic_paper_bundle(
    client: OrkgClient,
    paper_id: str,
    *,
    depth: int = 4,
    rules: Optional[ExtractionRules] = None,
) -> Dict[str, Any]:
    """
    Extract a template-agnostic representation of a paper using contribution-level
    crawling and classification.

    This function mirrors the older script-based implementation but uses the
    shared `OrkgClient`, settings and the existing contribution extractor.

    Returns a dict containing paper metadata, per-contribution compact facts and
    a merged `paper_core` composed from contributions.
    """
    rules = rules or ExtractionRules()
    paper = client.get_paper(paper_id)

    # --- core paper metadata (unchanged) ---
    authors = []
    for a in (paper.get("authors") or []):
        if isinstance(a, dict):
            authors.append(a.get("name") or a.get("label") or a.get("id"))
        else:
            authors.append(str(a))

    bundle: Dict[str, Any] = {
        "paper": {
            "id": paper.get("id"),
            "title": paper.get("title"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
            "authors": [x for x in authors if x],
            "research_fields": [rf.get("label") for rf in (paper.get("research_fields") or []) if isinstance(rf, dict)],
        },
        "paper_core": {  # filled after extracting contributions
            "problems": [],
            "methods": [],
            "data": [],
            "evaluation": [],
            "artifacts": [],
        },
        "contributions": [],
        "extraction": {
            "depth": depth,
            "template_agnostic": True,
            "notes": [
                "No predicate IDs are used.",
                "Paper core is derived by merging contribution-level facts (more reliable than paper node crawl).",
                "Leaf extraction follows resource edges and collects Name literals.",
            ],
        },
    }

    # --- extract contributions first ---
    for c in (paper.get("contributions") or []):
        cid = c.get("id")
        clabel = c.get("label") or ""
        if not cid:
            continue

        contrib = extract_contribution_bundle(client, cid, clabel, rules=rules)

        # leakage guard: if something appears in evaluation, it must not be a method
        ev = set(contrib["compact"].get("evaluation", []))
        contrib["compact"]["methods"] = [m for m in contrib["compact"].get("methods", []) if m not in ev]

        bundle["contributions"].append(contrib)

    # --- merge paper_core from contribution compacts ---
    bundle["paper_core"] = merge_paper_core_from_contributions(bundle["contributions"])

    return bundle
