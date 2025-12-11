# python
"""
app/rag/build_index.py

Build a RAG index from ORKG sandbox papers. This module:
- fetches papers (and contributions) for a research field,
- extracts contribution-level template annotations,
- converts resources to plain text documents,
- builds and persists a LlamaIndex vector index.

Small improvements:
- explicit types and docstrings
- logging and clearer error context
- safer dict access and corrected template iteration
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from collections import defaultdict


# Configure module logger
logger = logging.getLogger(__name__)

# Where the vector index will be persisted
INDEX_DIR = "storage/nfdixcs_index"

# ORKG sandbox base URL
ORKG_SANDBOX_API = "https://sandbox.orkg.org/api"

# Research field "Software Architecture and Design" in ORKG prod is R659055.
SOFTWARE_ARCH_RF_ID = "R659055"


def build_rag_index() -> None:
    """
    Build and persist a retrieval-augmented generation (RAG) index using
    ORKG metadata + contribution-level annotations only.

    Workflow:
      1. Fetch papers with contribution annotations from ORKG.
      2. Normalize annotation properties into semantic fields.
      3. Use an LLM to generate a 3–6 sentence summary paragraph for each
         (paper, contribution) based ONLY on metadata and annotations.
      4. Print each generated paragraph (debugging / verification).
      5. Embed the paragraphs and build a vector index.
    """

    # -------- 1. Configure LlamaIndex Settings --------
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    # -------- 2. Fetch ORKG data --------
    papers, datasets = fetch_papers_with_annotations()

    # -------- 3. Build vector docs from LLM summaries --------
    logger.info("Generating LLM summaries for RAG index...")
    docs: List[str] = []

    for paper in papers:
        paper_meta = {
            "title": paper.get("title"),
            "authors": paper.get("authors"),
            "research_fields": paper.get("research_fields"),
            "year": paper.get("year", None),
        }

        for contrib in paper.get("annotations", []) or []:

            # Normalize ORKG annotations into semantic fields
            semantic = normalize_annotations(contrib.get("annotations", []) or [])
            if not semantic:
                continue

            # Create the paragraph with LLM
            summary = summarize_contribution_with_llm(
                paper_meta=paper_meta,
                semantic=semantic
            )

            # -------- PRINTING PARAGRAPH --------
            print("\n==============================")
            print(f"Paper: {paper_meta['title']}")
            print(f"Contribution: {contrib.get('label')}")
            print("Generated Summary:")
            print(summary)
            print("==============================\n")

            # Add to docs for indexing
            docs.append(summary)

    # -------- 4. Build vector index --------
    logger.info("Building vector index with %d documents...", len(docs))
    index = VectorStoreIndex.from_documents(docs)

    # -------- 5. Persist to disk --------
    try:
        index.storage_context.persist(persist_dir=INDEX_DIR)
    except AttributeError:
        try:
            index.persist(persist_dir=INDEX_DIR)
        except Exception as e:
            logger.exception("Failed to persist index: %s", e)
            raise


def fetch_template_instance(session, template_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a template instance JSON from ORKG sandbox.
    Returns None if the template is not applicable (HTTP 404).
    """
    url = f"{ORKG_SANDBOX_API}/templates/{template_id}/instances/{instance_id}"
    headers = {
        "Accept": "application/vnd.orkg.template-instance.v1+json",
        "Content-Type": "application/vnd.orkg.template-instance.v1+json",
    }
    resp = session.get(url, headers=headers, timeout=30)

    if resp.status_code == 404:
        # Not applicable to this instance
        return None

    resp.raise_for_status()
    return resp.json()


def extract_annotations_from_instance(instance_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten a template instance into a list of annotation dicts.

    Each dict contains:
      - predicate_id, predicate_label
      - value_id, value_label, value_type
    """
    preds = instance_json.get("predicates", {}) or {}
    stmts = instance_json.get("statements", {}) or {}

    annotations: List[Dict[str, Any]] = []
    for pred_id, stmt_list in stmts.items():
        pred_info = preds.get(pred_id, {}) or {}
        pred_label = pred_info.get("label", pred_id)

        for stmt in stmt_list:
            thing = stmt.get("thing", {}) or {}
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
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch papers from the ORKG sandbox for a research field and extract
    contribution-level template annotations.

    Returns:
      (papers, datasets) where datasets is an empty list for now.
    Each paper dict contains id, title, authors, research_fields, url, annotations.
    """
    import requests

    session = requests.Session()

    # Templates to inspect on contributions (label -> template id)
    TEMPLATES_OF_INTEREST: Dict[str, str] = {"Contribution": "R603969"}

    paper_headers = {
        "Accept": "application/vnd.orkg.paper.v2+json",
        "Content-Type": "application/json",
    }

    papers: List[Dict[str, Any]] = []
    datasets: List[Dict[str, Any]] = []

    for page in range(max_pages):
        params = {
            "research_field": research_field_id,
            "include_subfields": "true",
            "size": page_size,
            "page": page,
            "sort": "created_at,desc",
        }
        logger.debug("Fetching papers page %d with params %s", page, params)
        resp = session.get(
            f"{ORKG_SANDBOX_API}/papers",
            params=params,
            headers=paper_headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("content", []) or []
        if not content:
            # No more results
            break

        for p in content:
            pid = p.get("id")
            if pid is None:
                logger.warning("Skipping paper with no id: %s", p)
                continue

            # fetch full paper to get contributions
            paper_resp = session.get(
                f"{ORKG_SANDBOX_API}/papers/{pid}",
                headers=paper_headers,
                timeout=30,
            )
            paper_resp.raise_for_status()
            paper_full = paper_resp.json()
            # NOTE: We intentionally do NOT use any full-text fields (abstract/body) here;
            # we only rely on metadata and contribution-level template annotations.

            contributions = paper_full.get("contributions", []) or []
            contribution_annos: List[Dict[str, Any]] = []

            for c in contributions:
                cid = c.get("id")
                c_label = c.get("label")
                all_annos: List[Dict[str, Any]] = []

                # Correct iteration over the templates mapping (bug fix)
                for tpl_label, tpl_id in TEMPLATES_OF_INTEREST.items():
                    inst = fetch_template_instance(session, tpl_id, cid)
                    if inst is None:
                        # template not used for this contribution
                        continue

                    annos = extract_annotations_from_instance(inst)
                    # attach template and contribution metadata
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
                    "url": f"https://sandbox.orkg.org/paper/{pid}",
                    "authors": paper_full.get("authors"),
                    "research_fields": paper_full.get("research_fields"),
                    "annotations": contribution_annos,
                }
            )

        # Pagination: stop when on the last page
        page_info = data.get("page", {}) or {}
        if page_info.get("number", 0) >= page_info.get("total_pages", 1) - 1:
            break

    return papers, datasets

PROPERTY_MAP = {
    "P32_hasResearchProblem": "research_problem",
    "P33_hasApproach": "method",
    "P40_usesDataset": "datasets",
    "P47_reportsMetric": "metrics",
    "P50_reportsResult": "results",
    "P60_hasLimitation": "limitations",
}



def normalize_annotations(annos):
    """
       #
    # Normalize raw ORKG template annotations into semantically meaningful fields.
    #
    # ORKG template instances contain property/value pairs with predicate IDs
    # (e.g., "P32_hasResearchProblem"). This function maps those predicates into a
    # stable semantic schema (e.g., "research_problem", "method", "datasets",
    # "metrics") using PROPERTY_MAP.
    #
    # The output is a dictionary where each semantic field contains either a
    # single value or a list of values. This normalized structure is used as the
    # input for the LLM summarization step.
    #
    # Notes:
    # - Only properties present in PROPERTY_MAP are retained.
    # - No inference or guessing is performed; missing properties remain missing.
    # - This function does NOT fetch any external data or full text.
    #
    # Example output:
    #     {
    #         "research_problem": "Denoising microscopy images",
    #         "method": "Self-supervised CNN",
    #         "datasets": ["Simulated", "Real high-speed"],
    #         "metrics": ["PSNR", "SSIM"]
    #     }
    #
    """
    result = defaultdict(list)

    for a in annos:
        prop = a.get("property")
        value = a.get("value")
        if prop is None or value is None:
            continue

        field = PROPERTY_MAP.get(prop)
        if field is None:
            # ignore fields not relevant for summarization
            continue

        result[field].append(value)

    # convert single-element lists to scalars if you prefer
    final = {}
    for k, v in result.items():
        if len(v) == 1:
            final[k] = v[0]
        else:
            final[k] = v

    return final


from typing import Dict, Any
from openai import OpenAI

client = OpenAI()

def summarize_contribution_with_llm(
    paper_meta: Dict[str, Any],
    semantic: Dict[str, Any],
    model: str = "gpt-4.1-mini",
) -> str:
    """
    Use ONLY metadata + normalized annotations to generate a single
    contribution summary paragraph (3–6 sentences).
    No full text involved.
    """
    # keep JSON small and clean for the prompt
    minimal_paper_meta = {
        "title": paper_meta.get("title"),
        "year": paper_meta.get("year"),
        "research_fields": paper_meta.get("research_fields"),
        "authors": [a.get("name") for a in (paper_meta.get("authors") or [])],
    }

    system_msg = (
        "You generate concise, technical summaries of research contributions "
        "from structured metadata.\n"
        "Rules:\n"
        "- Use ONLY the information provided.\n"
        "- Do NOT invent datasets, methods, metrics, or results.\n"
        "- Use all non-empty fields if possible.\n"
        "- Write exactly ONE paragraph of 3–6 sentences.\n"
        "- Focus on: research problem, method, data/evaluation, results, novelty, limitations.\n"
        "- Do not mention field names like 'research_problem' explicitly.\n"
        "- Do not say 'the metadata says'; just describe the contribution directly."
    )

    user_msg = (
        "Here is the paper metadata:\n"
        f"{minimal_paper_meta}\n\n"
        "Here are the normalized contribution fields:\n"
        f"{semantic}\n\n"
        "Write one coherent paragraph suitable for semantic search. "
        "Return only the paragraph."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,  # keep it tight, less hallucination
        max_tokens=300,
    )

    return resp.choices[0].message.content.strip()

if __name__ == "__main__":
    # Basic logging configuration for when run as a script
    logging.basicConfig(level=logging.INFO)
    build_rag_index()
