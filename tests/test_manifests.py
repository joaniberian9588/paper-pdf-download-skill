import json
from pathlib import Path

from paper_pdf.manifests import write_aggregate_manifests, write_paper_manifest
from paper_pdf.models import PaperResult, RetrievalStatus


def test_per_paper_and_aggregate_manifests(tmp_path: Path) -> None:
    bundle = tmp_path / "ieee" / "10.1109_test"
    result = PaperResult(
        "10.1109/test", "ieee", bundle, status=RetrievalStatus.SUCCESS, pdf_path="paper.pdf"
    )
    write_paper_manifest(result)
    json_path, csv_path = write_aggregate_manifests(tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["doi"] == "10.1109/test"
    assert "conversion_status" in csv_path.read_text(encoding="utf-8")


def test_aggregate_rebuild_keeps_every_existing_bundle(tmp_path: Path) -> None:
    first = PaperResult(
        "10.1109/first",
        "ieee",
        tmp_path / "ieee" / "first",
        status=RetrievalStatus.SUCCESS,
    )
    second = PaperResult(
        "10.1038/second",
        "springer-nature",
        tmp_path / "springer-nature" / "second",
        status=RetrievalStatus.CHALLENGE_REQUIRED,
    )
    write_paper_manifest(first)
    write_paper_manifest(second)

    json_path, _ = write_aggregate_manifests(tmp_path)
    records = json.loads(json_path.read_text(encoding="utf-8"))

    assert {record["doi"] for record in records} == {"10.1109/first", "10.1038/second"}
