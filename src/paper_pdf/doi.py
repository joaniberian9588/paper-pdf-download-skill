"""DOI extraction, normalization, and safe output naming."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
DOI_URL_PREFIX_RE = re.compile(r"^(?:https?://)?(?:dx\.)?doi\.org/", re.IGNORECASE)


def normalize_doi(value: str) -> str:
    candidate = unquote(value.strip())
    candidate = DOI_URL_PREFIX_RE.sub("", candidate)
    match = DOI_RE.search(candidate)
    if not match:
        raise ValueError(f"Not a DOI: {value!r}")
    doi = match.group(0).rstrip(".,;:!?)]}").lower()
    if "/" not in doi:
        raise ValueError(f"Not a DOI: {value!r}")
    return doi


def extract_dois(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in DOI_RE.findall(unquote(text)):
        try:
            doi = normalize_doi(raw)
        except ValueError:
            continue
        if doi not in seen:
            seen.add(doi)
            result.append(doi)
    return result


def collect_dois(values: list[str], input_file: Path | None = None) -> list[str]:
    combined = "\n".join(values)
    if input_file:
        combined += "\n" + input_file.read_text(encoding="utf-8", errors="replace")
    return extract_dois(combined)


def safe_doi_name(doi: str) -> str:
    normalized = normalize_doi(doi)
    readable = re.sub(r"[^a-z0-9._-]+", "_", normalized).strip("._")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{readable[:96]}-{digest}"


def compact_doi(value: str) -> str:
    """Normalize a DOI for tolerant matching in extracted PDF text."""
    try:
        value = normalize_doi(value)
    except ValueError:
        value = value.lower()
    return re.sub(r"[\s\\]", "", unquote(value)).rstrip(".,;:!?")
