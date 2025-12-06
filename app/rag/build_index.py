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
    papers, datasets = fetch_papers_with_annotations()

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



def fetch_template_instance(session, template_id: str, instance_id: str):
    url = f"{ORKG_SANDBOX_API}/templates/{template_id}/instances/{instance_id}"
    headers = {
        "Accept": "application/vnd.orkg.template-instance.v1+json",
        "Content-Type": "application/vnd.orkg.template-instance.v1+json",
    }
    resp = session.get(url, headers=headers, timeout=30)

    if resp.status_code == 404:
        # template not applicable to this instance
        return None

    resp.raise_for_status()
    return resp.json()


def extract_annotations_from_instance(instance_json: dict) -> list[dict]:
    """Flatten template instance to (predicate_label, value, value_type, predicate_id, value_id)."""
    preds = instance_json.get("predicates", {})
    stmts = instance_json.get("statements", {})

    annotations = []
    for pred_id, stmt_list in stmts.items():
        pred_info = preds.get(pred_id, {})
        pred_label = pred_info.get("label", pred_id)

        for stmt in stmt_list:
            thing = stmt.get("thing", {})
            t_class = thing.get("_class")
            value_id = thing.get("id")
            value_label = thing.get("label")

            if t_class == "literal":
                value_type = thing.get("datatype", "xsd:string")
            elif t_class == "resource":
                value_type = "resource"
            elif t_class == "list":
                value_type = "list"
            else:
                value_type = t_class or "unknown"

            annotations.append(
                {
                    "predicate_id": pred_id,
                    "predicate_label": pred_label,
                    "value_id": value_id,
                    "value_label": value_label,
                    "value_type": value_type,
                }
            )

    return annotations

def fetch_papers_with_annotations(
    research_field_id: str = SOFTWARE_ARCH_RF_ID,
    page_size: int = 50,
    max_pages: int = 10,
):
    import requests

    session = requests.Session()

    TEMPLATES_OF_INTEREST = {
        "Contribution": "R603969"
    }
    paper_headers = {
        "Accept": "application/vnd.orkg.paper.v2+json",
        "Content-Type": "application/json",
    }

    papers = []

    for page in range(max_pages):
        params = {
            "research_field": research_field_id,
            "include_subfields": "true",
            "size": page_size,
            "page": page,
            "sort": "created_at,desc",
        }
        resp = session.get(
            f"{ORKG_SANDBOX_API}/papers",
            params=params,
            headers=paper_headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("content", [])
        if not content:
            break

        for p in content:
            pid = p["id"]

            # fetch full paper to get contributions
            paper_resp = session.get(
                f"{ORKG_SANDBOX_API}/papers/{pid}",
                headers=paper_headers,
                timeout=30,
            )
            paper_resp.raise_for_status()
            paper_full = paper_resp.json()

            contributions = paper_full.get("contributions", [])

            contribution_annos = []
            for c in contributions:
                cid = c["id"]
                c_label = c.get("label")

                all_annos = []


                for tpl_label, tpl_id in "TEMPLATES_OF_INTEREST".items():
                    inst = fetch_template_instance(session, tpl_id, cid)
                    if inst is None:
                        continue  # this template not used for this contribution

                    annos = extract_annotations_from_instance(inst)
                    # tag them with template info + contribution
                    for a in annos:
                        a["template_id"] = tpl_id
                        a["template_label"] = tpl_label
                        a["contribution_id"] = cid
                        a["contribution_label"] = c_label
                    all_annos.extend(annos)

                if all_annos:
                    contribution_annos.append(
                        {
                            "id": cid,
                            "label": c_label,
                            "annotations": all_annos,
                        }
                    )

            papers.append(
                {
                    "id": pid,
                    "title": paper_full.get("title"),
                    "authors": paper_full.get("authors"),
                    "research_fields": paper_full.get("research_fields"),
                    "annotations": contribution_annos,
                }
            )

        page_info = data.get("page", {}) or {}
        if page_info.get("number", 0) >= page_info.get("total_pages", 1) - 1:
            break

    return papers



if __name__ == "__main__":
    build_rag_index()
