# app/rag/extract/runner.py
"""
High-level extractor runner utilities.

This module exposes a small programmatic API used by the lightweight script
`app/rag/scripts/find_Correct_ORKG_call.py`.

Responsibilities:
- Call the template-agnostic extraction implemented in `bundle.py`.
- Build a short human-readable paragraph from the merged `paper_core` facts.
"""
from typing import Dict, Tuple, Optional

from app.rag.orkg.client import OrkgClient
from app.rag.extract.bundle import extract_template_agnostic_paper_bundle
from app.rag.extract.rules import ExtractionRules


def build_paragraph_from_bundle(bundle: Dict) -> str:
    """Build a concise human-readable paragraph from an extraction bundle.

    The result is intentionally simple: it picks items from the merged
    `paper_core` (problems, methods, data, evaluation, artifacts) and
    formats a short paragraph.
    """
    paper = bundle.get("paper", {})
    core = bundle.get("paper_core", {})

    parts = []
    title = paper.get("title")
    if title:
        parts.append(f"Paper titled '{title}'")
    if core.get("problems"):
        parts.append(f"addresses: {', '.join(core['problems'][:5])}")
    if core.get("methods"):
        parts.append(f"proposes methods: {', '.join(core['methods'][:5])}")
    if core.get("data"):
        parts.append(f"uses/introduces data: {', '.join(core['data'][:5])}")
    if core.get("evaluation"):
        parts.append(f"evaluated by: {', '.join(core['evaluation'][:5])}")
    if core.get("artifacts"):
        parts.append(f"artifacts: {', '.join(core['artifacts'][:5])}")

    if not parts:
        return "No compact facts extracted from paper."

    paragraph = ". ".join(parts) + "."
    return paragraph


def extract_paper_and_paragraph(
    client: OrkgClient, paper_id: str, *, depth: int = 4, rules: Optional[ExtractionRules] = None
) -> Tuple[Dict, str]:
    """Run extraction for a paper and return (bundle, paragraph).

    - client: OrkgClient instance
    - paper_id: ORKG paper id (e.g., 'R874684')
    - depth/rules: forwarded to the extractor

    Returns:
    - bundle: the extraction dict returned by the extractor
    - paragraph: a short summary string built from bundle
    """
    rules = rules or ExtractionRules()
    bundle = extract_template_agnostic_paper_bundle(client, paper_id, depth=depth, rules=rules)
    paragraph = build_paragraph_from_bundle(bundle)
    return bundle, paragraph
