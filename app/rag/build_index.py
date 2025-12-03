# backend/rag/build_index.py

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter
from my_orkg_client import fetch_papers_and_datasets  # you write this

INDEX_DIR = "storage/nfdixcs_index"

def build_rag_index():
    # 1) set global settings for LlamaIndex
    Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    # 2) Fetch your ORKG data (papers + datasets + version info)
    papers, datasets = fetch_papers_and_datasets()

    # 3) Convert to Documents
    docs = []
    for paper in papers:
        docs.append(paper.to_llama_document())  # you'll implement to_llama_document()

    for ds in datasets:
        docs.append(ds.to_llama_document())

    # 4) Build index
    index = VectorStoreIndex.from_documents(docs)

    # 5) Persist to disk
    index.storage_context.persist(persist_dir=INDEX_DIR)

if __name__ == "__main__":
    build_rag_index()
