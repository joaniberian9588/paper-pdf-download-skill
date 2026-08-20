from paper_pdf.publishers import (
    build_pdf_candidates,
    discover_pdf_candidates,
    get_profile,
    infer_profile,
)


def test_infer_major_publishers() -> None:
    assert infer_profile("10.1109/5.771073").key == "ieee"
    assert infer_profile("10.1016/j.energy.2024.1").key == "elsevier"
    assert infer_profile("10.1021/acs.test.1").key == "acs"
    assert (
        infer_profile("10.1000/example", "https://www.nature.com/articles/example").key
        == "springer-nature"
    )


def test_html_discovery_collects_meta_embed_and_nested_query() -> None:
    html = """
      <meta name="citation_pdf_url" content="/main.pdf">
      <a href="/viewer?file=https%3A%2F%2Fcdn.example.org%2Fpaper.pdf">PDF</a>
      <embed type="application/pdf" src="/embedded.pdf">
    """
    candidates = discover_pdf_candidates(html, "https://example.org/article")
    assert candidates[0] == "https://example.org/main.pdf"
    assert "https://cdn.example.org/paper.pdf" in candidates
    assert "https://example.org/embedded.pdf" in candidates


def test_elsevier_filters_supplement_and_keeps_matching_pii() -> None:
    profile = get_profile("elsevier")
    source = "https://www.sciencedirect.com/science/article/pii/S1234567890123456"
    candidates = build_pdf_candidates(
        profile,
        "10.1016/j.example.2026.1",
        source_url=source,
        discovered=[
            "https://ars.els-cdn.com/content/image/1-s2.0-S1234567890123456-mmc1.pdf",
            "https://www.sciencedirect.com/science/article/pii/S1234567890123456/pdfft?download=true",
        ],
    )
    assert candidates[0].endswith("/S1234567890123456/pdfft")
    assert not any("mmc1" in candidate for candidate in candidates)


def test_ieee_and_copernicus_special_routes() -> None:
    ieee = build_pdf_candidates(
        get_profile("ieee"),
        "10.1109/test.1",
        source_url="https://ieeexplore.ieee.org/document/9876543",
    )
    assert "arnumber=9876543" in ieee[0]
    copernicus = build_pdf_candidates(get_profile("copernicus"), "10.5194/acp-24-1-2024")
    assert copernicus[0] == "https://acp.copernicus.org/articles/24/1/2024/acp-24-1-2024.pdf"


def test_discovered_doi_pdf_for_other_article_is_rejected() -> None:
    profile = get_profile("aps")
    candidates = build_pdf_candidates(
        profile,
        "10.1103/physrevlett.128.161102",
        discovered=[
            "https://journals.aps.org/prl/pdf/10.1103/physrevlett.999.1",
            "https://journals.aps.org/prl/pdf/10.1103/physrevlett.128.161102",
        ],
    )
    assert not any("999.1" in candidate for candidate in candidates)
    assert any("128.161102" in candidate for candidate in candidates)


def test_unrelated_cross_domain_pdf_is_rejected() -> None:
    profile = get_profile("mdpi")
    candidates = build_pdf_candidates(
        profile,
        "10.3390/foods10081757",
        source_url="https://www.mdpi.com/2304-8158/10/8/1757",
        discovered=[
            "https://unrelated.example.org/manual.pdf",
            "https://mdpi-res.com/article/foods10081757/main.pdf",
        ],
    )
    assert not any("unrelated.example.org" in candidate for candidate in candidates)
    assert any("mdpi-res.com" in candidate for candidate in candidates)
