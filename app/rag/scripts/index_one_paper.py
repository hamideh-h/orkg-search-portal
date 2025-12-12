# app/rag/scripts/index_one_paper.py
import sys

from app.rag.index.build_llama import build_llama_index_for_paper


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.rag.scripts.index_one_paper <PAPER_ID>")
        raise SystemExit(2)

    paper_id = sys.argv[1].strip()
    n = build_llama_index_for_paper(paper_id)
    print(f"Indexed {n} docs for paper {paper_id}")


if __name__ == "__main__":
    main()
