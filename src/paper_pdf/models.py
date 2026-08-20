"""Shared result models and stable machine-readable status values."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class RetrievalStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    SKIPPED_EXISTING = "skipped_existing"
    UNVERIFIED_PDF = "unverified_pdf"
    REJECTED_SUPPLEMENT = "rejected_supplement"
    CHALLENGE_REQUIRED = "challenge_required"
    AUTH_REQUIRED = "auth_required"
    BLOCKED = "blocked"
    SESSION_LIMIT = "session_limit"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(slots=True)
class Attempt:
    route: str
    outcome: str
    url: str = ""
    detail: str = ""
    http_status: int | None = None


@dataclass(slots=True)
class VerificationReport:
    structurally_valid: bool = False
    verified: bool = False
    verification_method: str = "none"
    doi_match: bool = False
    title_similarity: float = 0.0
    is_supplement: bool = False
    page_count: int | None = None
    size_bytes: int = 0
    sha256: str = ""
    extracted_text_chars: int = 0
    reason: str = ""


@dataclass(slots=True)
class ConversionReport:
    requested: bool = False
    status: str = "not_requested"
    mode: str = ""
    markdown_path: str = ""
    assets_path: str = ""
    markdown_chars: int = 0
    detail: str = ""


@dataclass(slots=True)
class PaperResult:
    doi: str
    publisher: str
    bundle_dir: Path
    status: RetrievalStatus = RetrievalStatus.PENDING
    pdf_path: str = ""
    source_route: str = ""
    source_url: str = ""
    title: str = ""
    verification: VerificationReport = field(default_factory=VerificationReport)
    conversion: ConversionReport = field(default_factory=ConversionReport)
    attempts: list[Attempt] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bundle_dir"] = str(self.bundle_dir)
        data["status"] = self.status.value
        return data
