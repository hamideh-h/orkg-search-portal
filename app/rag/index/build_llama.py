# app/rag/index/build_llama.py
from __future__ import annotations

from typing import List, Dict, Any

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.rag.core.settings import settings
from app.rag.extract.build_index import extract_paper_bundle
from app.rag.index.docs import bundle_to_docs


def _docs_to_llama_documents(docs: List[Dict[str, Any]]) -> List[Document]:
    return [
        Document(text=d["text"], metadata=d.get("metadata", {}), doc_id=d.get("doc_id"))
        for d in docs
    ]


def build_llama_index_for_paper(paper_id: str) -> int:
    settings.ensure_dirs()

    # ✅ create embed model instance explicitly
    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # optional: keep global settings consistent
    LlamaSettings.embed_model = embed_model
    LlamaSettings.llm = None

    # -------- NEW: extract + WRITE bundle --------
    bundle = extract_paper_bundle(paper_id)

    import json
    bundle_path = settings.EXPORTS_DIR / f"orkg_bundle_{paper_id}.json"
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print("Wrote bundle:", bundle_path)
    # --------------------------------------------

    docs = bundle_to_docs(bundle)
    llama_docs = _docs_to_llama_documents(docs)

    # ✅ pass embed_model explicitly so it cannot fall back to OpenAI
    index = VectorStoreIndex.from_documents(
        llama_docs, embed_model=embed_model
    )

    index.storage_context.persist(persist_dir=str(settings.INDEX_DIR))
    return len(llama_docs)
