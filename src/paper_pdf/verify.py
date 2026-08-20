"""Structural, DOI/title, and supplementary-material PDF verification."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from pypdf import PdfReader

from .doi import compact_doi, normalize_doi
from .models import VerificationReport

SUPPLEMENT_TITLE_RE = re.compile(
    r"^\s*(?:electronic\s+)?(?:supplementary|supplemental|supporting)\s+"
    r"(?:material|materials|information|data|file|files)\b",
    re.IGNORECASE,
)


def plausible_pdf_bytes(data: bytes, min_bytes: int = 5_000) -> tuple[bool, str]:
    if not isinstance(data, (bytes, bytearray)):
        return False, "not_bytes"
    body = bytes(data)
    if not body:
        return False, "empty"
    prefix = body[:512].lstrip().lower()
    if prefix.startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
        return False, "html_response"
    if len(body) <= min_bytes:
        return False, "too_small"
    header_at = body[:1024].find(b"%PDF-")
    if header_at < 0:
        return False, "missing_pdf_header"
    eof = body.rfind(b"%%EOF")
    if eof != -1 and eof < max(0, len(body) - 8192):
        return False, "early_eof_with_trailing_payload"
    return True, "plausible"


def verify_pdf_bytes(
    data: bytes,
    doi: str,
    *,
    expected_title: str = "",
    source_url: str = "",
    min_bytes: int = 5_000,
) -> VerificationReport:
    report = VerificationReport(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    plausible, reason = plausible_pdf_bytes(data, min_bytes=min_bytes)
    if not plausible:
        report.reason = reason
        return report

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        report.page_count = len(reader.pages)
        metadata = reader.metadata or {}
        metadata_text = "\n".join(str(value) for value in metadata.values() if value)
        chunks: list[str] = []
        for page in reader.pages[: min(5, len(reader.pages))]:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001, S112 - retain usable pages if one extractor fails
                continue
        extracted = "\n".join(chunks)
        report.extracted_text_chars = len(extracted)
    except Exception as exc:  # noqa: BLE001 - malformed PDFs can raise heterogeneous pypdf errors
        report.reason = f"pdf_parse_error:{type(exc).__name__}"
        return report

    report.structurally_valid = True
    document_text = f"{metadata_text}\n{extracted}"
    report.is_supplement = _looks_like_supplement(metadata_text, extracted, source_url)
    if report.is_supplement:
        report.reason = "supplementary_or_supporting_material"
        return report

    target = compact_doi(normalize_doi(doi))
    haystack = re.sub(r"[\s\\]", "", document_text.lower())
    report.doi_match = target in haystack
    if report.doi_match:
        report.verified = True
        report.verification_method = "doi"
        report.reason = "verified_doi_match"
        return report

    report.title_similarity = title_similarity(expected_title, document_text)
    if expected_title and report.title_similarity >= 0.72:
        report.verified = True
        report.verification_method = "title"
        report.reason = "verified_title_match"
    else:
        report.reason = "target_doi_or_title_not_verified"
    return report


def verify_pdf_path(
    path: Path,
    doi: str,
    *,
    expected_title: str = "",
    source_url: str = "",
    min_bytes: int = 5_000,
) -> VerificationReport:
    return verify_pdf_bytes(
        path.read_bytes(),
        doi,
        expected_title=expected_title,
        source_url=source_url,
        min_bytes=min_bytes,
    )


def title_similarity(expected: str, document_text: str) -> float:
    expected_tokens = _title_tokens(expected)
    if len(expected_tokens) < 4:
        return 0.0
    document_tokens = _title_tokens(document_text[:10_000])
    if not document_tokens:
        return 0.0
    overlap = expected_tokens & document_tokens
    return len(overlap) / len(expected_tokens)


def _title_tokens(text: str) -> set[str]:
    stop = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "the",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in stop
    }


def _looks_like_supplement(metadata_text: str, extracted: str, source_url: str) -> bool:
    lower_url = source_url.lower()
    if any(
        marker in lower_url
        for marker in ("supplement", "supporting-information", "suppl_file", "-mmc")
    ):
        return True
    first = (metadata_text + "\n" + extracted[:1_500]).strip()
    lines = [line.strip() for line in first.splitlines() if line.strip()]
    return any(SUPPLEMENT_TITLE_RE.search(line) for line in lines[:8])
