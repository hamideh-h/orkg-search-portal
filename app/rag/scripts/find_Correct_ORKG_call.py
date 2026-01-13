"""Deprecated compatibility stub.

The original `find_Correct_ORKG_call.py` script was replaced by
`extract_paper_summary.py` to provide a clearer, documented, and
maintainable extraction entrypoint.

This module now intentionally refuses to run and prints a short message
explaining the new location. Keeping a stub here avoids surprising
`FileNotFound` errors from IDE run configurations while guiding users to
the updated script.
"""

import sys

if __name__ == "__main__":
    print("find_Correct_ORKG_call.py has been removed.")
    print("Please use app/rag/scripts/extract_paper_summary.py instead.")
    print("Example: python -m app.rag.scripts.extract_paper_summary R874684")
    sys.exit(1)

# Prevent accidental imports from providing functionality.
raise RuntimeError(
    "find_Correct_ORKG_call.py has been removed. Use app.rag.scripts.extract_paper_summary instead."
)
