import json
import sys
from app.rag.orkg.client import OrkgClient
from app.rag.core.settings import settings
from app.rag.extract.runner import extract_paper_and_paragraph


if __name__ == "__main__":
    if len(sys.argv) > 1:
        paper_id = sys.argv[1]
    else:
        paper_id = "R874684"

    client = OrkgClient(settings)
    bundle, paragraph = extract_paper_and_paragraph(client, paper_id)

    out_path = f"orkg_template_agnostic_{paper_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print("Wrote:", out_path)
    print("Contributions:", len(bundle.get("contributions", [])))
    print("\nSummary paragraph:")
    print(paragraph)
