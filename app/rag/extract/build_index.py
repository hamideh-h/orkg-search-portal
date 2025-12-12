# app/rag/extract/build_index.py
import json
from pathlib import Path

from app.rag.extract.bundle import extract_contribution_bundle
from app.rag.extract.rules import ExtractionRules
from app.rag.orkg.client import OrkgClient
from app.rag.core.settings import settings


def extract_paper_bundle(paper_id: str) -> dict:
    client = OrkgClient(settings)
    rules = ExtractionRules()

    paper = client.get_paper(paper_id)

    contributions = []
    for c in paper.get("contributions", []):
        cid = c.get("id")
        clabel = c.get("label") or ""
        if not cid:
            continue

        contributions.append(
            extract_contribution_bundle(
                client,
                cid,
                clabel,
                rules=rules,
            )
        )

    return {
        "paper": {
            "id": paper.get("id"),
            "title": paper.get("title"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
        },
        "contributions": contributions,
    }


def write_bundle(paper_id: str) -> Path:
    settings.ensure_dirs()
    bundle = extract_paper_bundle(paper_id)

    out = settings.EXPORTS_DIR / f"orkg_bundle_{paper_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    return out
