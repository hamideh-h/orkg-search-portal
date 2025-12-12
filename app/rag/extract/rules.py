# app/rag/extract/rules.py
import re
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ExtractionRules:
    # ORKG class-based hints
    research_problem_classes: Tuple[str, ...] = ("ResearchProblem",)

    # contribution label hint
    evidence_label: re.Pattern = re.compile(
        r"\b(evidence|evaluation|validation)\b", re.I
    )

    # cues
    PROBLEM: re.Pattern = re.compile(
        r"\b(problem|goal|aim|challenge|addresses|research question|abstract|description|summary)\b",
        re.I,
    )

    DATA: re.Pattern = re.compile(
        r"\b(dataset|data|corpus|benchmark)\b", re.I
    )

    EVALUATION: re.Pattern = re.compile(
        r"\b(evaluat|validat|metric|measure|case study|experiment|user study|"
        r"property|sub-property|guideline|threat to validity)\b",
        re.I,
    )

    METHOD: re.Pattern = re.compile(
        r"\b(method|approach|model|algorithm|architecture|pipeline|framework|"
        r"embedding|reference architecture|research object)\b",
        re.I,
    )

    ARTIFACT: re.Pattern = re.compile(
        r"\b(url|code|repo|implementation|demo|video|artifact|package|replication)\b",
        re.I,
    )

    TOOL: re.Pattern = re.compile(
        r"\b(tool support|tool|replication package|replication|available|used)\b",
        re.I,
    )
