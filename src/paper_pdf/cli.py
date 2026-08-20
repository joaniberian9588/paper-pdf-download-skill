"""Command-line interface for retrieval, verification, and conversion."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .config import AppConfig, load_config
from .conversion import ConversionError, convert_library
from .doi import collect_dois
from .publishers import list_profiles
from .retriever import RetrievalOptions, SilentRetriever
from .verify import verify_pdf_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-pdf",
        description="Silently retrieve authorized paper PDFs, verify the main article, and optionally convert with MinerU.",
    )
    parser.add_argument(
        "--config", type=Path, help="TOML local override (never commit credentials)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Batch-download and verify PDFs")
    _add_subcommand_config(download)
    _add_download_arguments(download)

    run = subparsers.add_parser("run", help="Download verified PDFs, then batch-convert them")
    _add_subcommand_config(run)
    _add_download_arguments(run)
    _add_conversion_arguments(run)

    convert = subparsers.add_parser(
        "convert", help="Batch-convert verified PDFs already in a library"
    )
    _add_subcommand_config(convert)
    convert.add_argument("root", type=Path, help="Library root containing publisher/DOI bundles")
    _add_conversion_arguments(convert)

    verify = subparsers.add_parser("verify", help="Verify a local PDF against a DOI")
    _add_subcommand_config(verify)
    verify.add_argument("pdf", type=Path)
    verify.add_argument("doi")
    verify.add_argument("--title", default="")

    publishers = subparsers.add_parser("publishers", help="List built-in publisher profiles")
    _add_subcommand_config(publishers)
    doctor = subparsers.add_parser(
        "doctor", help="Report dependency availability without exposing secrets"
    )
    _add_subcommand_config(doctor)
    return parser


def _add_subcommand_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)


def _add_download_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("dois", nargs="*", help="One or more DOIs or DOI URLs")
    parser.add_argument("--file", type=Path, help="Text, BibTeX, CSV, or Markdown containing DOIs")
    parser.add_argument("--output", type=Path, default=Path("library"))
    parser.add_argument(
        "--workers", type=int, default=1, help="Concurrent publisher sessions (default: 1)"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Allow a visible manual challenge/login handoff"
    )
    parser.add_argument("--interactive-timeout", type=int, default=300)
    parser.add_argument(
        "--no-browser", action="store_true", help="Use only silent HTTP/OA/API routes"
    )
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--min-pdf-bytes", type=int, default=5_000)


def _add_conversion_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=("local", "api"), default="local")
    parser.add_argument(
        "--allow-upload", action="store_true", help="Required consent gate for API mode"
    )
    parser.add_argument("--mineru-command", help="Override mineru or mineru-open-api executable")
    parser.add_argument("--backend", help="Local MinerU backend (default from config)")
    parser.add_argument("--language", help="Local MinerU OCR language hint")
    parser.add_argument("--keep-conversion-work", action="store_true")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(getattr(args, "config", None))

    if args.command == "publishers":
        for profile in list_profiles():
            print(f"{profile.key:20} {profile.name}")
        return 0
    if args.command == "doctor":
        report = {
            "python": sys.version.split()[0],
            "cloakbrowser_module": importlib.util.find_spec("cloakbrowser") is not None,
            "mineru_command": bool(shutil.which(config.conversion.mineru_command)),
            "mineru_open_api_command": bool(
                shutil.which(config.conversion.mineru_open_api_command)
            ),
            "config_path": str(config.config_path) if config.config_path else "",
        }
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "verify":
        report = verify_pdf_path(args.pdf, args.doi, expected_title=args.title)
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        return 0 if report.verified else 2
    if args.command == "convert":
        return _convert(args.root, args, config)

    dois = collect_dois(args.dois, args.file)
    if not dois:
        parser.error("No DOI found. Pass DOI arguments or --file.")
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    options = RetrievalOptions(
        output=args.output,
        workers=args.workers,
        interactive=args.interactive,
        interactive_timeout_seconds=args.interactive_timeout,
        browser_enabled=not args.no_browser,
        resume=not args.no_resume,
        min_pdf_bytes=args.min_pdf_bytes,
    )
    results = SilentRetriever(
        config, options, progress=lambda line: print(line, flush=True)
    ).download_many(dois)
    successes = sum(result.status.value in {"success", "skipped_existing"} for result in results)
    print(f"PDF completion: {successes}/{len(results)} -> {args.output.resolve()}")
    for result in results:
        print(f"{result.status.value:20} {result.publisher:20} {result.doi}")

    if args.command == "run" and successes:
        conversion_code = _convert(args.output, args, config)
        if conversion_code:
            return conversion_code
    return 0 if successes == len(results) else 2


def _convert(root: Path, args: argparse.Namespace, config: AppConfig) -> int:
    try:
        outcomes = convert_library(
            root,
            config,
            mode=args.mode,
            allow_upload=args.allow_upload,
            command=args.mineru_command,
            backend=args.backend,
            language=args.language,
            keep_work=args.keep_conversion_work,
        )
    except ConversionError as exc:
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 2
    successes = sum(outcome.status == "success" for outcome in outcomes)
    print(f"Markdown completion: {successes}/{len(outcomes)} -> {root.resolve()}")
    return 0 if successes == len(outcomes) else 2


def download_entry() -> int:
    return main(["download", *sys.argv[1:]])


def convert_entry() -> int:
    return main(["convert", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
