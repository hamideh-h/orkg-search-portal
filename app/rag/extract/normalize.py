# app/rag/extract/normalize.py
import re


URL_RE = re.compile(r"https?://", re.I)

NOISE_OBJECT_LABEL = re.compile(
    r"^(true|false|evaluation|input data|tool support|evaluation method list|list|none|null|n/a)$",
    re.I,
)

NOISE_CONTAINING = re.compile(
    r"(list of entities|evaluation method entity|^entity$|^property$|^sub-property$|^properties$)",
    re.I,
)


def looks_like_url(s: str | None) -> bool:
    if not s:
        return False
    return bool(URL_RE.search(s))


def is_noise_value(v: str | None) -> bool:
    if not v:
        return True

    v2 = v.strip()
    if len(v2) <= 2:
        return True

    if NOISE_OBJECT_LABEL.match(v2):
        return True

    if NOISE_CONTAINING.search(v2):
        return True

    return False
