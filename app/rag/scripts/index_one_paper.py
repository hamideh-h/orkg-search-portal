# app/rag/scripts/index_one_paper.py
import re
import sys

from app.rag.index.build_llama import build_llama_index_for_paper

DEFAULT_PAPER_ID = "R874684"

_RE_PAPER_IN_URL = re.compile(r"/(?:paper|resource)/\s*(R\d+)", re.IGNORECASE)
_RE_PAPER_ID = re.compile(r"^R\d+$", re.IGNORECASE)
_RE_DIGITS = re.compile(r"^\d+$")


def normalize_paper_id(raw: str) -> str | None:
    """Return canonical ORKG paper id (e.g. 'R874643') or None if not parseable.

    Accepts short ids, plain digits, and full ORKG/sandbox URLs.
    """
    if not raw:
        return None
    s = raw.strip()
    m = _RE_PAPER_IN_URL.search(s)
    if m:
        return m.group(1).upper()
    if _RE_PAPER_ID.fullmatch(s):
        return s.upper()
    if _RE_DIGITS.fullmatch(s):
        return "R" + s
    return None


def main():
    # If no argument provided, fall back to the default paper id instead of exiting.
    if len(sys.argv) < 2:
        print(f"No PAPER_ID provided — defaulting to {DEFAULT_PAPER_ID}")
        paper_id = DEFAULT_PAPER_ID
    else:
        raw = sys.argv[1].strip()
        pid = normalize_paper_id(raw)
        if pid is None:
            print(f"Argument '{raw}' is not a valid ORKG paper id — defaulting to {DEFAULT_PAPER_ID}")
            paper_id = DEFAULT_PAPER_ID
        else:
            paper_id = pid

    n = build_llama_index_for_paper(paper_id)
    print(f"Indexed {n} docs for paper {paper_id}")


if __name__ == "__main__":
    main()
