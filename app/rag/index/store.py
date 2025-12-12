# app/rag/index/store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any


class IndexStore:
    """
    Thin wrapper around a persisted index.
    Replace internals later with FAISS / Qdrant / Weaviate.
    """

    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.docs_file = index_dir / "documents.jsonl"

        self.index_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # write
    # -------------------------
    def write_documents(self, docs: List[Dict[str, Any]]) -> None:
        if not docs:
            return

        with open(self.docs_file, "a", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    # -------------------------
    # read
    # -------------------------
    def load_documents(self) -> List[Dict[str, Any]]:
        if not self.docs_file.exists():
            return []

        docs: List[Dict[str, Any]] = []
        with open(self.docs_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                docs.append(json.loads(line))
        return docs
