"""Index build helpers.

Small wrappers that run the extract -> docs -> persist pipeline for one or many papers.
"""

from typing import List

from app.rag.core.settings import settings
from app.rag.extract.build_index import extract_paper_bundle
from app.rag.index.docs import bundle_to_docs
from app.rag.index.store import IndexStore


def build_index_for_paper(paper_id: str) -> List[dict]:
    """
    Full pipeline:
      ORKG -> bundle -> docs -> persisted index
    """
    settings.ensure_dirs()

    bundle = extract_paper_bundle(paper_id)
    docs = bundle_to_docs(bundle)

    store = IndexStore(settings.INDEX_DIR)
    store.write_documents(docs)

    return docs


def build_index_for_papers(paper_ids: List[str]) -> int:
    store = IndexStore(settings.INDEX_DIR)
    settings.ensure_dirs()

    count = 0
    for pid in paper_ids:
        bundle = extract_paper_bundle(pid)
        docs = bundle_to_docs(bundle)
        store.write_documents(docs)
        count += len(docs)

    return count
