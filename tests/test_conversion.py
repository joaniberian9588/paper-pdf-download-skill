import json
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from paper_pdf.config import AppConfig
from paper_pdf.conversion import ConversionError, convert_library


def make_library(root: Path, doi: str = "10.1000/example.1") -> Path:
    bundle = root / "generic" / "paper"
    bundle.mkdir(parents=True)
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    (bundle / "paper.pdf").write_bytes(output.getvalue())
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "doi": doi,
                "publisher": "generic",
                "status": "success",
                "pdf_path": "paper.pdf",
                "conversion": {"requested": False, "status": "not_requested"},
            }
        ),
        encoding="utf-8",
    )
    return bundle


def test_api_mode_requires_explicit_upload_consent(tmp_path: Path) -> None:
    make_library(tmp_path)
    with pytest.raises(ConversionError, match="--allow-upload"):
        convert_library(tmp_path, AppConfig(), mode="api")


def test_local_batch_reconciles_markdown_and_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = make_library(tmp_path)

    monkeypatch.setattr("paper_pdf.conversion._resolve_command", lambda command: ["fake-mineru"])

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        input_dir = Path(cmd[cmd.index("-p") + 1])
        raw_dir = Path(cmd[cmd.index("-o") + 1])
        stem = next(input_dir.glob("*.pdf")).stem
        result_dir = raw_dir / stem
        (result_dir / "images").mkdir(parents=True)
        (result_dir / "images" / "figure.png").write_bytes(b"png")
        (result_dir / f"{stem}.md").write_text(
            "# Parsed paper\n\n" + ("Research text. " * 20) + "\n![Figure](images/figure.png)\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr("paper_pdf.conversion.subprocess.run", fake_run)
    outcomes = convert_library(tmp_path, AppConfig(), mode="local")
    assert outcomes[0].status == "success"
    markdown = (bundle / "paper.md").read_text(encoding="utf-8")
    assert "assets/mineru/images/figure.png" in markdown
    assert (bundle / "assets" / "mineru" / "images" / "figure.png").exists()
    record = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert record["conversion"]["status"] == "success"
