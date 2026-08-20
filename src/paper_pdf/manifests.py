"""Atomic per-paper and aggregate manifests for resumable batches."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Iterable
from pathlib import Path

from .models import PaperResult


def write_paper_manifest(result: PaperResult) -> Path:
    result.bundle_dir.mkdir(parents=True, exist_ok=True)
    path = result.bundle_dir / "manifest.json"
    _atomic_json(path, result.to_dict())
    return path


def read_paper_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_aggregate_manifests(
    root: Path, results: Iterable[PaperResult] | None = None
) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    if results is None:
        records = []
        for path in sorted(root.glob("*/*/manifest.json")):
            try:
                records.append(read_paper_manifest(path))
            except (OSError, ValueError):
                continue
    else:
        records = [result.to_dict() for result in results]

    json_path = root / "manifest.json"
    csv_path = root / "manifest.csv"
    _atomic_json(json_path, records)
    fields = [
        "doi",
        "publisher",
        "status",
        "pdf_path",
        "source_route",
        "source_url",
        "title",
        "detail",
        "verification_method",
        "sha256",
        "conversion_status",
        "markdown_path",
    ]
    tmp = csv_path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            verification = record.get("verification") or {}
            conversion = record.get("conversion") or {}
            writer.writerow(
                {
                    "doi": record.get("doi", ""),
                    "publisher": record.get("publisher", ""),
                    "status": record.get("status", ""),
                    "pdf_path": record.get("pdf_path", ""),
                    "source_route": record.get("source_route", ""),
                    "source_url": record.get("source_url", ""),
                    "title": record.get("title", ""),
                    "detail": record.get("detail", ""),
                    "verification_method": verification.get("verification_method", ""),
                    "sha256": verification.get("sha256", ""),
                    "conversion_status": conversion.get("status", ""),
                    "markdown_path": conversion.get("markdown_path", ""),
                }
            )
    os.replace(tmp, csv_path)
    return json_path, csv_path


def _atomic_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
