# app/rag/extract/classify.py
from app.rag.extract.normalize import looks_like_url
from app.rag.extract.rules import ExtractionRules


def classify_statement(
    st: dict,
    rules: ExtractionRules,
    *,
    contribution_label: str = "",
) -> str:
    pred = st.get("predicate") or {}
    obj = st.get("object") or {}

    p_lbl = (pred.get("label") or pred.get("id") or "").lower()
    o_lbl = (obj.get("label") or "").lower()
    o_cls = obj.get("_class")

    if o_cls in rules.research_problem_classes:
        return "problem"

    if o_cls == "literal" and looks_like_url(o_lbl):
        return "artifact"

    # Evidence tab: default evaluation
    if rules.evidence_label.search(contribution_label):
        if rules.TOOL.search(p_lbl) or rules.TOOL.search(o_lbl):
            return "artifact"
        if rules.DATA.search(p_lbl) or rules.DATA.search(o_lbl):
            return "data"
        if rules.ARTIFACT.search(p_lbl) or looks_like_url(o_lbl):
            return "artifact"
        return "evaluation"

    # Normal routing (order matters)
    if rules.PROBLEM.search(p_lbl) or rules.PROBLEM.search(o_lbl):
        return "problem"
    if rules.TOOL.search(p_lbl) or rules.TOOL.search(o_lbl):
        return "artifact"
    if rules.DATA.search(p_lbl) or rules.DATA.search(o_lbl):
        return "data"
    if rules.EVALUATION.search(p_lbl) or rules.EVALUATION.search(o_lbl):
        return "evaluation"
    if rules.ARTIFACT.search(p_lbl) or looks_like_url(o_lbl):
        return "artifact"
    if rules.METHOD.search(p_lbl) or rules.METHOD.search(o_lbl):
        return "method"

    return "other"
