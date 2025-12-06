from llama_index.core import VectorStoreIndex
from llama_index.core import Settings
from llama_index.core.node_parser import (SentenceSplitter)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

INDEX_DIR = "storage/nfdixcs_index"
# ORKG sandbox base URL
ORKG_SANDBOX_API = "https://sandbox.orkg.org/api"

# Research field "Software Architecture and Design" in ORKG prod is R659055.

SOFTWARE_ARCH_RF_ID = "R659055"


def build_rag_index():
    # Build a RAG index from ORKG papers/datasets.



    # 1) set global settings for LlamaIndex
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    # 2) Fetch the ORKG data (papers + datasets + version info)
    papers, datasets = fetch_papers_and_datasets()

    # 3) Convert to Documents
    docs = []
    for paper in papers:
        # papers are dicts here; calling to_llama_document() is a placeholder
        # If a Paper class elsewhere implement that conversion there.
        if hasattr(paper, "to_llama_document"):
            docs.append(paper.to_llama_document())
        else:
            # create a minimal LlamaIndex Document-like object via dict
            # LlamaIndex accepts plain strings in from_documents, so pass text
            text = paper.get("title", "") + "\n" + (paper.get("url") or "")
            docs.append(text)

    for ds in datasets:
        if hasattr(ds, "to_llama_document"):
            docs.append(ds.to_llama_document())
        else:
            docs.append(str(ds))

    # 4) Build index
    index = VectorStoreIndex.from_documents(docs)

    # 5) Persist to disk
    try:
        index.storage_context.persist(persist_dir=INDEX_DIR)
    except AttributeError:
        # Some vector store backends may store differently; try generic persist
        try:
            index.persist(persist_dir=INDEX_DIR)
        except Exception:
            # If persistence fails, surface a helpful message at runtime
            raise



def fetch_papers_and_datasets(
    research_field_id: str = SOFTWARE_ARCH_RF_ID,
    page_size: int = 50,
    max_pages: int = 10,
):
    """
    Fetch papers (and later datasets) from ORKG sandbox for a given research field.

    Returns:
        papers: list[dict]
        datasets: list[dict]  # currently empty, left as TODO
    """
    import requests

    session = requests.Session()

    headers = {
        # v2 gives the modern paper representation
        "Accept": "application/vnd.orkg.paper.v2+json",
        "Content-Type": "application/json",
    }

    papers = []
    datasets = []  # TODO: wire via /api/datasets/... once I decide how I map research problems

    for page in range(max_pages):
        params = {
            "research_field": research_field_id,
            "include_subfields": "true",
            "size": page_size,
            "page": page,
            # created_at,desc / title,asc / etc.
            "sort": "created_at,desc",
        }

        resp = session.get(f"{ORKG_SANDBOX_API}/papers", params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # ORKG uses a paged response with "content" and "page"
        page_content = data.get("content", [])
        if not page_content:
            break

        for p in page_content:
            pid = p.get("id")
            papers.append(
                {
                    "id": pid,
                    "title": p.get("title"),
                    "url": f"https://sandbox.orkg.org/paper/{pid}" if pid else None,
                    "publication_info": p.get("publication_info"),
                    "identifiers": p.get("identifiers"),
                    "authors": p.get("authors"),
                    "research_fields": p.get("research_fields"),
                }
            )

        page_info = data.get("page", {}) or {}
        if page_info.get("number", 0) >= page_info.get("total_pages", 1) - 1:
            break

    return papers, datasets



if __name__ == "__main__":
    build_rag_index()
