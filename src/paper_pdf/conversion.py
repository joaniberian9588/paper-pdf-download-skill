"""Local-first MinerU batch conversion and explicit-upload API adapter."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from .config import AppConfig
from .doi import safe_doi_name
from .manifests import write_aggregate_manifests


class ConversionError(RuntimeError):
    pass


@dataclass(slots=True)
class ConversionOutcome:
    doi: str
    bundle_dir: Path
    status: str
    markdown_path: str = ""
    detail: str = ""


def convert_library(
    root: Path,
    config: AppConfig,
    *,
    mode: str = "local",
    allow_upload: bool = False,
    command: str | None = None,
    backend: str | None = None,
    language: str | None = None,
    keep_work: bool = False,
) -> list[ConversionOutcome]:
    root = root.expanduser().resolve()
    records = _eligible_records(root)
    if not records:
        return []
    if mode == "api" and not allow_upload:
        raise ConversionError(
            "API mode uploads PDFs to a third party. Re-run with --allow-upload only after explicit consent."
        )
    if mode not in {"local", "api"}:
        raise ConversionError(f"Unsupported conversion mode: {mode}")

    run_dir = root / ".conversion-work" / uuid.uuid4().hex[:12]
    input_dir = run_dir / "input"
    raw_dir = run_dir / "raw"
    input_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)

    mapping: dict[str, tuple[Path, dict[str, object], Path]] = {}
    for manifest_path, record, pdf_path in records:
        stem = safe_doi_name(str(record["doi"]))
        staged = input_dir / f"{stem}.pdf"
        _link_or_copy(pdf_path, staged)
        mapping[stem] = (manifest_path, record, pdf_path)

    resolved_command = command or (
        config.conversion.mineru_command
        if mode == "local"
        else config.conversion.mineru_open_api_command
    )
    prefix = _resolve_command(resolved_command)
    if mode == "local":
        cmd = prefix + [
            "-p",
            str(input_dir),
            "-o",
            str(raw_dir),
            "-b",
            backend or config.conversion.backend,
        ]
        selected_language = language or config.conversion.language
        if selected_language:
            cmd.extend(["-l", selected_language])
    else:
        list_path = run_dir / "files.txt"
        list_path.write_text(
            "\n".join(str(input_dir / f"{stem}.pdf") for stem in mapping) + "\n",
            encoding="utf-8",
        )
        cmd = prefix + ["extract", "--list", str(list_path), "-o", str(raw_dir), "-f", "md"]

    process = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    outcomes: list[ConversionOutcome] = []
    if process.returncode != 0:
        detail = _process_detail(process)
        for manifest_path, record, _ in mapping.values():
            _update_conversion(record, mode, "failed", detail=detail)
            _write_json(manifest_path, record)
            outcomes.append(
                ConversionOutcome(str(record["doi"]), manifest_path.parent, "failed", detail=detail)
            )
        write_aggregate_manifests(root)
        raise ConversionError(detail)

    for stem, (manifest_path, record, _) in mapping.items():
        bundle = manifest_path.parent
        markdown = _find_markdown(raw_dir, stem)
        if markdown is None:
            detail = "MinerU completed but no matching Markdown output was found"
            _update_conversion(record, mode, "failed", detail=detail)
            _write_json(manifest_path, record)
            outcomes.append(ConversionOutcome(str(record["doi"]), bundle, "failed", detail=detail))
            continue

        raw_text = markdown.read_text(encoding="utf-8", errors="replace")
        assets_root = bundle / "assets" / "mineru"
        rewritten = _copy_assets_and_rewrite(raw_text, markdown.parent, markdown, assets_root)
        if len(re.sub(r"\s+", "", rewritten)) < config.conversion.min_markdown_chars:
            detail = "MinerU Markdown output is empty or too short"
            _update_conversion(record, mode, "failed", detail=detail)
            _write_json(manifest_path, record)
            outcomes.append(ConversionOutcome(str(record["doi"]), bundle, "failed", detail=detail))
            continue

        paper_md = bundle / "paper.md"
        tmp = paper_md.with_suffix(".md.partial")
        tmp.write_text(rewritten.rstrip() + "\n", encoding="utf-8")
        os.replace(tmp, paper_md)
        _update_conversion(
            record,
            mode,
            "success",
            markdown_path="paper.md",
            assets_path="assets/mineru" if assets_root.exists() else "",
            markdown_chars=len(rewritten),
        )
        _write_json(manifest_path, record)
        outcomes.append(ConversionOutcome(str(record["doi"]), bundle, "success", "paper.md"))

    write_aggregate_manifests(root)
    if not keep_work and all(outcome.status == "success" for outcome in outcomes):
        _remove_owned_work_dir(root, run_dir)
    return outcomes


def _eligible_records(root: Path) -> list[tuple[Path, dict[str, object], Path]]:
    records: list[tuple[Path, dict[str, object], Path]] = []
    for manifest_path in sorted(root.glob("*/*/manifest.json")):
        try:
            record = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("status") not in {"success", "skipped_existing"}:
            continue
        pdf_name = str(record.get("pdf_path") or "paper.pdf")
        pdf_path = manifest_path.parent / pdf_name
        if pdf_path.exists():
            records.append((manifest_path, record, pdf_path))
    return records


def _find_markdown(raw_dir: Path, stem: str) -> Path | None:
    exact = sorted(raw_dir.rglob(f"{stem}.md"))
    if exact:
        return exact[0]
    candidates = [
        path
        for path in raw_dir.rglob("*.md")
        if stem in path.stem or any(stem == part for part in path.parts)
    ]
    return min(candidates) if candidates else None


MARKDOWN_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")


def _copy_assets_and_rewrite(text: str, source_dir: Path, markdown: Path, assets_root: Path) -> str:
    copied: dict[str, str] = {}
    for path in source_dir.rglob("*"):
        if not path.is_file() or path == markdown:
            continue
        relative = path.relative_to(source_dir)
        destination = assets_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied[relative.as_posix()] = f"assets/mineru/{relative.as_posix()}"

    def replace(match: re.Match[str]) -> str:
        raw_target = match.group(2).strip()
        if raw_target.startswith(("http://", "https://", "data:", "#")):
            return match.group(0)
        target = raw_target.strip("<>").split(" ", 1)[0]
        decoded = unquote(target).replace("\\", "/")
        replacement = copied.get(decoded)
        if replacement:
            suffix = raw_target[len(target) :]
            return f"{match.group(1)}{replacement}{suffix}{match.group(3)}"
        return match.group(0)

    return MARKDOWN_LINK_RE.sub(replace, text)


def _resolve_command(command: str) -> list[str]:
    resolved = shutil.which(command)
    if not resolved and Path(command).expanduser().exists():
        resolved = str(Path(command).expanduser().resolve())
    if not resolved:
        raise ConversionError(f"Command not found: {command}")
    if resolved.lower().endswith(".ps1"):
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            raise ConversionError(f"PowerShell is required to run {resolved}")
        return [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
    return [resolved]


def _link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _update_conversion(
    record: dict[str, object],
    mode: str,
    status: str,
    *,
    markdown_path: str = "",
    assets_path: str = "",
    markdown_chars: int = 0,
    detail: str = "",
) -> None:
    record["conversion"] = {
        "requested": True,
        "status": status,
        "mode": mode,
        "markdown_path": markdown_path,
        "assets_path": assets_path,
        "markdown_chars": markdown_chars,
        "detail": detail,
    }


def _write_json(path: Path, record: dict[str, object]) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _process_detail(process: subprocess.CompletedProcess[str]) -> str:
    tail = (process.stderr or process.stdout or "").strip().splitlines()[-8:]
    return f"MinerU exited with code {process.returncode}: " + " | ".join(tail)


def _remove_owned_work_dir(root: Path, run_dir: Path) -> None:
    work_root = (root / ".conversion-work").resolve()
    target = run_dir.resolve()
    if target.parent == work_root and target.exists():
        shutil.rmtree(target)
