# app/rag/index/docs.py
from __future__ import annotations

from typing import List, Dict, Any


def _format_list(title: str, items: List[str]) -> str:
    if not items:
        return ""
    body = "\n".join(f"- {x}" for x in items)
    return f"{title}:\n{body}\n"


def contribution_to_doc(
    paper: dict,
    contribution: dict,
) -> Dict[str, Any]:
    comp = contribution.get("compact", {})

    text_parts = [
        f"Paper title: {paper.get('title')}",
        f"Contribution: {contribution.get('label')}",
        _format_list("Problems", comp.get("problems", [])),
        _format_list("Methods", comp.get("methods", [])),
        _format_list("Data", comp.get("data", [])),
        _format_list("Evaluation", comp.get("evaluation", [])),
        _format_list("Artifacts", comp.get("artifacts", [])),
    ]

    text = "\n".join(p for p in text_parts if p.strip())

    return {
        "doc_id": f"orkg:{paper.get('id')}:contrib:{contribution.get('id')}",
        "text": text,
        "metadata": {
            "paper_id": paper.get("id"),
            "paper_title": paper.get("title"),
            "contribution_id": contribution.get("id"),
            "contribution_label": contribution.get("label"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "source": "orkg",
            "level": "contribution",
            "bucket_sizes": {k: len(v) for k, v in comp.items()},
        },
    }


def paper_core_to_doc(bundle: dict) -> Dict[str, Any]:
    paper = bundle.get("paper", {})
    core = bundle.get("paper_core", {})

    text_parts = [
        f"Paper title: {paper.get('title')}",
        _format_list("Problems", core.get("problems", [])),
        _format_list("Methods", core.get("methods", [])),
        _format_list("Data", core.get("data", [])),
        _format_list("Evaluation", core.get("evaluation", [])),
        _format_list("Artifacts", core.get("artifacts", [])),
    ]

    text = "\n".join(p for p in text_parts if p.strip())

    return {
        "doc_id": f"orkg:{paper.get('id')}:paper",
        "text": text,
        "metadata": {
            "paper_id": paper.get("id"),
            "paper_title": paper.get("title"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "source": "orkg",
            "level": "paper",
        },
    }


def bundle_to_docs(bundle: dict) -> List[Dict[str, Any]]:
    """
    Convert an extracted ORKG bundle into RAG-ready documents.
    """
    docs: List[Dict[str, Any]] = []

    # paper-level summary doc
    docs.append(paper_core_to_doc(bundle))

    # contribution-level docs
    for contrib in bundle.get("contributions", []):
        docs.append(contribution_to_doc(bundle["paper"], contrib))

    return docs
