from io import BytesIO

from pypdf import PdfWriter

from paper_pdf.verify import plausible_pdf_bytes, verify_pdf_bytes


def make_pdf(*, title: str = "", subject: str = "") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    metadata = {}
    if title:
        metadata["/Title"] = title
    if subject:
        metadata["/Subject"] = subject
    if metadata:
        writer.add_metadata(metadata)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_html_is_not_a_pdf() -> None:
    valid, reason = plausible_pdf_bytes(b"<html>access denied</html>" * 1000, min_bytes=100)
    assert not valid
    assert reason == "html_response"


def test_pdf_verifies_by_doi_metadata() -> None:
    report = verify_pdf_bytes(
        make_pdf(subject="doi:10.1000/example.1"),
        "10.1000/example.1",
        min_bytes=100,
    )
    assert report.structurally_valid
    assert report.verified
    assert report.verification_method == "doi"


def test_pdf_verifies_by_title_when_doi_absent() -> None:
    title = "Reliable Silent Retrieval of Authorized Research Articles"
    report = verify_pdf_bytes(
        make_pdf(title=title), "10.1000/missing", expected_title=title, min_bytes=100
    )
    assert report.verified
    assert report.verification_method == "title"


def test_supplementary_pdf_is_rejected_even_with_doi() -> None:
    report = verify_pdf_bytes(
        make_pdf(title="Supplementary Information", subject="10.1000/example.1"),
        "10.1000/example.1",
        min_bytes=100,
    )
    assert report.is_supplement
    assert not report.verified
