from pathlib import Path

import pytest

from paper_pdf.doi import collect_dois, extract_dois, normalize_doi, safe_doi_name


def test_normalize_doi_url_and_punctuation() -> None:
    assert (
        normalize_doi("https://doi.org/10.1038/S41586-020-2649-2.") == "10.1038/s41586-020-2649-2"
    )


def test_extract_dois_deduplicates_case_insensitively() -> None:
    text = "10.1109/ABC.123 and https://doi.org/10.1109/abc.123; then 10.1021/acstest.1"
    assert extract_dois(text) == ["10.1109/abc.123", "10.1021/acstest.1"]


def test_collect_dois_reads_bib_like_input(tmp_path: Path) -> None:
    source = tmp_path / "refs.bib"
    source.write_text("doi = {10.1007/s00134-020-00001-2}", encoding="utf-8")
    assert collect_dois([], source) == ["10.1007/s00134-020-00001-2"]


def test_safe_name_is_stable_and_filesystem_safe() -> None:
    name = safe_doi_name("10.1000/ABC(1):2")
    assert name == safe_doi_name("10.1000/abc(1):2")
    assert all(char.isalnum() or char in "._-" for char in name)


def test_invalid_doi_raises() -> None:
    with pytest.raises(ValueError):
        normalize_doi("not-a-doi")
