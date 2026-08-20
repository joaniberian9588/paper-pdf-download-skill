import json

from paper_pdf.config import AppConfig
from paper_pdf.doi import safe_doi_name
from paper_pdf.models import RetrievalStatus
from paper_pdf.retriever import RetrievalOptions, SilentRetriever, _status_from_browser_exception


class NoNetworkClient:
    def metadata(self, doi):
        raise AssertionError(f"resume should not query metadata for {doi}")

    def resolve_doi(self, doi):
        raise AssertionError(f"resume should not resolve {doi}")


def test_resume_preserves_verification_and_conversion(tmp_path) -> None:
    doi = "10.1109/test.1"
    bundle = tmp_path / "ieee" / safe_doi_name(doi)
    bundle.mkdir(parents=True)
    (bundle / "paper.pdf").write_bytes(b"existing")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "doi": doi,
                "publisher": "ieee",
                "status": "success",
                "pdf_path": "paper.pdf",
                "source_route": "cloakbrowser",
                "verification": {"verified": True, "sha256": "abc123"},
                "conversion": {"requested": True, "status": "success", "markdown_path": "paper.md"},
                "attempts": [],
            }
        ),
        encoding="utf-8",
    )
    retriever = SilentRetriever(AppConfig(), RetrievalOptions(output=tmp_path))
    prepared = retriever._prepare_direct(NoNetworkClient(), doi)
    assert prepared.result.status == RetrievalStatus.SKIPPED_EXISTING
    assert prepared.result.verification.sha256 == "abc123"
    assert prepared.result.conversion.markdown_path == "paper.md"
    assert prepared.result.source_route == "cloakbrowser"


def test_browser_session_limit_has_a_distinct_status() -> None:
    status = _status_from_browser_exception(RuntimeError("CloakBrowser Pro: session limit reached"))
    assert status == RetrievalStatus.SESSION_LIMIT
