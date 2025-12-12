import json
import re
import requests
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

ORKG = "https://sandbox.orkg.org/api"
PAPER_ACCEPT = "application/vnd.orkg.paper.v2+json"


# -------------------------
# Utilities
# -------------------------

def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 30) -> dict:
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

def get_paper(paper_id: str) -> dict:
    return _get_json(f"{ORKG}/papers/{paper_id}", headers={"Accept": PAPER_ACCEPT})

def get_statements(subject_id: str, size: int = 200) -> List[dict]:
    data = _get_json(f"{ORKG}/statements", params={"subject_id": subject_id, "size": size})
    return data.get("content", [])

def looks_like_url(s: str) -> bool:
    return bool(re.search(r"https?://", s or ""))

def safe_label(x: dict) -> str:
    return (x.get("label") or x.get("id") or "").strip()

def obj_class(x: dict) -> str:
    return (x.get("_class") or "").strip()

def pred_label(st: dict) -> str:
    p = st.get("predicate", {}) or {}
    return (p.get("label") or p.get("id") or "").strip()


# -------------------------
# Template-agnostic rules
# -------------------------

@dataclass(frozen=True)
class ExtractionRules:
    research_problem_classes: Tuple[str, ...] = ("ResearchProblem",)
    evidence_label: re.Pattern = re.compile(r"\bevidence\b|\beval(uation)?\b|\bvalidation\b", re.I)


# -------------------------
# Graph crawl
# -------------------------

def crawl_neighborhood(
    root_id: str,
    *,
    max_depth: int = 4,
    follow_resources: bool = True,
    statement_page_size: int = 200
) -> List[dict]:
    q = deque([(root_id, 0)])
    seen = set()
    out: List[dict] = []

    while q:
        sid, depth = q.popleft()
        if sid in seen or depth > max_depth:
            continue
        seen.add(sid)

        for st in get_statements(sid, size=statement_page_size):
            out.append(st)
            obj = st.get("object", {}) or {}
            if follow_resources and obj_class(obj) == "resource" and depth < max_depth:
                oid = obj.get("id")
                if oid:
                    q.append((oid, depth + 1))

    return out


# -------------------------
# Noise filtering
# -------------------------

NOISE_OBJECT_LABEL = re.compile(
    r"^(true|false|evaluation|input data|tool support|evaluation method list|list|none|null|n/a)$",
    re.I
)

NOISE_CONTAINING = re.compile(
    r"(list of entities|evaluation method entity|^entity$|^property$|^sub-property$|^properties$)",
    re.I
)

def is_noise_value(v: str) -> bool:
    if not v:
        return True
    v2 = v.strip()
    if NOISE_OBJECT_LABEL.match(v2):
        return True
    if NOISE_CONTAINING.search(v2):
        return True
    if len(v2) <= 2:
        return True
    return False


# -------------------------
# Semantic cues (label-based, no IDs)
# -------------------------
TOOL_CUES = re.compile(r"\b(tool support|tool|replication package|replication|available|used)\b", re.I)
PROBLEM_CUES  = re.compile(r"\b(problem|goal|aim|challenge|addresses|research question|abstract|description|summary)\b", re.I)
DATA_CUES     = re.compile(r"\b(dataset|data|corpus|benchmark)\b", re.I)

# IMPORTANT: include property/sub-property/guideline so evaluation trees get bucketed correctly
EVAL_CUES     = re.compile(
    r"\b(evaluat|validat|metric|measure|case study|experiment|user study|property|sub-property|guideline|threat to validity)\b",
    re.I
)

METHOD_CUES   = re.compile(r"\b(method|approach|model|algorithm|architecture|pipeline|framework|embedding|reference architecture|research object)\b", re.I)
ARTIFACT_CUES = re.compile(r"\b(url|code|repo|implementation|demo|video|artifact|package|replication)\b", re.I)


# -------------------------
# Leaf extractor (template-structure flattener)
# -------------------------

NAME_PRED = re.compile(r"\bname\b", re.I)

def extract_semantic_leaves_any(
    start_id: str,
    *,
    max_depth: int = 6,
    max_nodes: int = 400
) -> List[str]:
    values: List[str] = []
    q = deque([(start_id, 0)])
    seen = set()

    while q and len(seen) < max_nodes:
        sid, depth = q.popleft()
        if sid in seen or depth > max_depth:
            continue
        seen.add(sid)

        for st in get_statements(sid):
            p_lbl = pred_label(st)
            obj = st.get("object", {}) or {}
            o_cls = obj_class(obj)
            o_lbl = safe_label(obj)

            if o_cls == "literal":
                if looks_like_url(o_lbl):
                    values.append(o_lbl)
                elif NAME_PRED.search(p_lbl):
                    if not is_noise_value(o_lbl):
                        values.append(o_lbl)
                else:
                    if o_lbl and not is_noise_value(o_lbl) and len(o_lbl) >= 4:
                        values.append(o_lbl)

            elif o_cls == "resource":
                oid = obj.get("id")
                if oid:
                    q.append((oid, depth + 1))

    out, seen2 = [], set()
    for v in values:
        v2 = v.strip()
        if not v2 or is_noise_value(v2):
            continue
        if v2 not in seen2:
            out.append(v2)
            seen2.add(v2)
    return out

def split_artifacts(compact: dict) -> None:
    data_like = []
    artifacts = []

    for v in compact.get("artifacts", []):
        if DATA_CUES.search(v):
            data_like.append(v)
        else:
            artifacts.append(v)

    # merge data availability back into data
    compact["data"].extend(x for x in data_like if x not in compact["data"])
    compact["artifacts"] = artifacts

# -------------------------
# Classification
# -------------------------

def classify_statement(st: dict, rules: ExtractionRules, contrib_label: str = "") -> str:
    p_lbl = pred_label(st)
    o = st.get("object", {}) or {}
    o_lbl = safe_label(o)
    o_cls = obj_class(o)

    if o_cls in rules.research_problem_classes:
        return "problem"

    if o_cls == "literal" and looks_like_url(o_lbl):
        return "artifact"

    # Evidence tabs: default to evaluation unless clearly data/artifact/tool
    if rules.evidence_label.search(contrib_label):
        if TOOL_CUES.search(p_lbl) or TOOL_CUES.search(o_lbl):
            return "artifact"
        if DATA_CUES.search(p_lbl) or DATA_CUES.search(o_lbl):
            return "data"
        if ARTIFACT_CUES.search(p_lbl) or looks_like_url(o_lbl):
            return "artifact"
        return "evaluation"

    # Non-evidence: order matters
    if PROBLEM_CUES.search(p_lbl) or PROBLEM_CUES.search(o_lbl):
        return "problem"
    if TOOL_CUES.search(p_lbl) or TOOL_CUES.search(o_lbl):
        return "artifact"
    if DATA_CUES.search(p_lbl) or DATA_CUES.search(o_lbl):
        return "data"
    if EVAL_CUES.search(p_lbl) or EVAL_CUES.search(o_lbl):
        return "evaluation"
    if ARTIFACT_CUES.search(p_lbl) or looks_like_url(o_lbl):
        return "artifact"
    if METHOD_CUES.search(p_lbl) or METHOD_CUES.search(o_lbl):
        return "method"

    return "other"


def normalize_statement(st: dict) -> dict:
    subj = st.get("subject", {}) or {}
    pred = st.get("predicate", {}) or {}
    obj = st.get("object", {}) or {}
    return {
        "subject_id": subj.get("id"),
        "predicate_label": pred.get("label") or pred.get("id"),
        "predicate_id": pred.get("id"),
        "object": {
            "id": obj.get("id"),
            "label": obj.get("label"),
            "class": obj.get("_class"),
        },
    }


# -------------------------
# Core extraction
# -------------------------

def extract_compact_from_bucket(bucket_items: List[dict]) -> List[str]:
    vals: List[str] = []
    for x in bucket_items:
        obj = x["object"]
        ocls = obj.get("class")
        oid = obj.get("id")
        olbl = (obj.get("label") or "").strip()

        if ocls == "resource" and oid:
            vals.extend(extract_semantic_leaves_any(oid))
        elif ocls == "literal":
            if olbl and not is_noise_value(olbl):
                vals.append(olbl)

    out, seen = [], set()
    for v in vals:
        v2 = v.strip()
        if not v2 or is_noise_value(v2):
            continue
        if v2 not in seen:
            out.append(v2)
            seen.add(v2)
    return out


def extract_core_from_contribution(
    contribution_id: str,
    contribution_label: str,
    *,
    rules: ExtractionRules,
    depth: int = 4
) -> Dict[str, Any]:
    stmts = crawl_neighborhood(contribution_id, max_depth=depth, follow_resources=True)
    buckets: Dict[str, List[dict]] = defaultdict(list)

    for st in stmts:
        bucket = classify_statement(st, rules, contrib_label=contribution_label)
        buckets[bucket].append(normalize_statement(st))

    compact = {
        "problems": extract_compact_from_bucket(buckets.get("problem", [])),
        "methods": extract_compact_from_bucket(buckets.get("method", [])),
        "data": extract_compact_from_bucket(buckets.get("data", [])),
        "evaluation": extract_compact_from_bucket(buckets.get("evaluation", [])),
        "artifacts": extract_compact_from_bucket(buckets.get("artifact", [])),
    }

    split_artifacts(compact)

    return {
        "id": contribution_id,
        "label": contribution_label,
        "compact": compact,
        "buckets": {k: v for k, v in buckets.items()},
    }


def extract_template_agnostic_paper_bundle(
    paper_id: str,
    *,
    depth: int = 4,
    rules: Optional[ExtractionRules] = None
) -> Dict[str, Any]:
    rules = rules or ExtractionRules()
    paper = get_paper(paper_id)

    # --- core paper metadata (unchanged) ---
    authors = []
    for a in (paper.get("authors") or []):
        if isinstance(a, dict):
            authors.append(a.get("name") or a.get("label") or a.get("id"))
        else:
            authors.append(str(a))

    bundle: Dict[str, Any] = {
        "paper": {
            "id": paper.get("id"),
            "title": paper.get("title"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
            "authors": [x for x in authors if x],
            "research_fields": [rf.get("label") for rf in (paper.get("research_fields") or []) if isinstance(rf, dict)],
        },
        "paper_core": {  # filled after extracting contributions
            "problems": [],
            "methods": [],
            "data": [],
            "evaluation": [],
            "artifacts": [],
        },
        "contributions": [],
        "extraction": {
            "depth": depth,
            "template_agnostic": True,
            "notes": [
                "No predicate IDs are used.",
                "Paper core is derived by merging contribution-level facts (more reliable than paper node crawl).",
                "Leaf extraction follows resource edges and collects Name literals."
            ]
        }
    }

    # --- extract contributions first ---
    for c in (paper.get("contributions") or []):
        cid = c.get("id")
        clabel = c.get("label") or ""
        if not cid:
            continue

        contrib = extract_core_from_contribution(cid, clabel, rules=rules, depth=depth)

        # leakage guard: if something appears in evaluation, it must not be a method
        ev = set(contrib["compact"].get("evaluation", []))
        contrib["compact"]["methods"] = [m for m in contrib["compact"].get("methods", []) if m not in ev]

        bundle["contributions"].append(contrib)

    # --- merge paper_core from contribution compacts ---
    def add_unique(target: list, items: list):
        seen = set(target)
        for it in items:
            if it not in seen:
                target.append(it)
                seen.add(it)

    merged = {"problems": [], "methods": [], "data": [], "evaluation": [], "artifacts": []}
    for contrib in bundle["contributions"]:
        comp = contrib.get("compact", {})
        for k in merged.keys():
            add_unique(merged[k], comp.get(k, []))

    # leakage guard at paper level too
    ev2 = set(merged["evaluation"])
    merged["methods"] = [m for m in merged["methods"] if m not in ev2]

    bundle["paper_core"] = merged

    return bundle


def merge_paper_core_from_contributions(contribs: list[dict]) -> dict:
    merged = {"problems": [], "methods": [], "data": [], "evaluation": [], "artifacts": []}

    def add_unique(key: str, vals: list[str]):
        seen = set(merged[key])
        for v in vals:
            if v not in seen:
                merged[key].append(v)
                seen.add(v)

    for c in contribs:
        comp = c.get("compact", {})
        for k in merged.keys():
            add_unique(k, comp.get(k, []))

    return merged


# -------------------------
# Run & write JSON
# -------------------------

if __name__ == "__main__":
    paper_id = "R874643"
    bundle = extract_template_agnostic_paper_bundle(paper_id, depth=4)

    out_path = f"orkg_template_agnostic_{paper_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print("Wrote:", out_path)
    print("Contributions:", len(bundle["contributions"]))

    print("\nPaper core (preview):")
    for k, v in bundle["paper_core"].items():
        print(f"  {k}: {v[:10]}")

    for c in bundle["contributions"][:6]:
        print("\n-", c["label"], c["id"])
        print("  problems :", c["compact"]["problems"][:10])
        print("  methods  :", c["compact"]["methods"][:10])
        print("  data     :", c["compact"]["data"][:10])
        print("  eval     :", c["compact"]["evaluation"][:10])
        print("  artifacts:", c["compact"]["artifacts"][:10])
