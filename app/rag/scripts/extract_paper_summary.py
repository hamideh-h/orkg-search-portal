"""extract_paper_summary.py

CLI helper to extract annotations from an ORKG paper and build a short
summary paragraph from them.

This is a cleaned-up, well-documented replacement for
`find_Correct_ORKG_call.py`.

Usage (PowerShell / CMD):
  python -m app.rag.scripts.extract_paper_summary R874684
or
  python app\rag\scripts\extract_paper_summary.py R874684

If no paper id is provided the script defaults to `R874684`.

Outputs:
- Writes `orkg_template_agnostic_<paper_id>.json` in the current working
  directory. This JSON contains the extracted bundle (annotations,
  contributions, and related fields) returned by the extraction runner.
- Prints the number of contributions and a generated summary paragraph to
  stdout.

Return values (when called from Python):
- tuple(out_path, bundle, paragraph)

"""

import json
import sys
from typing import Tuple

from app.rag.orkg.client import OrkgClient
from app.rag.core.settings import settings
from app.rag.extract.runner import extract_paper_and_paragraph


def main(argv=None) -> Tuple[str, dict, str]:
    """Main entrypoint.

    Args:
        argv: list of command-line arguments (not including program name).
              If None, sys.argv[1:] will be used.

    Returns:
        A tuple (out_path, bundle, paragraph).

    Behavior:
        - Determines paper id from argv or uses default R874684.
        - Calls the project's extraction runner to collect the structured
          bundle and a human-readable paragraph summary.
        - Saves the bundle as JSON and prints a short report.
    """

    if argv is None:
        argv = sys.argv[1:]

    # If an ID was provided use it, otherwise default to a known paper id
    if len(argv) > 0 and argv[0]:
        paper_id = argv[0]
    else:
        paper_id = "R874684"

    # Build the ORKG client using the project's settings and run the
    # extraction pipeline.
    client = OrkgClient(settings)
    bundle, paragraph = extract_paper_and_paragraph(client, paper_id)

    # Persist the extracted bundle as a JSON file. This file is the
    # machine-friendly representation of the extracted annotations and
    # can be used by downstream tooling.
    out_path = f"orkg_template_agnostic_{paper_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    # Provide a quick human-readable summary on stdout for convenience.
    print(f"Wrote: {out_path}")
    print(f"Contributions: {len(bundle.get('contributions', []))}")
    print("\nSummary paragraph:")
    print(paragraph)

    return out_path, bundle, paragraph


if __name__ == "__main__":
    main()

