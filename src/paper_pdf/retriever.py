"""Independent silent-first batch retrieval orchestration."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .browser_session import CloakPublisherSession
from .config import AppConfig
from .direct import DirectClient, HttpResult
from .doi import normalize_doi, safe_doi_name
from .manifests import read_paper_manifest, write_aggregate_manifests, write_paper_manifest
from .models import (
    Attempt,
    ConversionReport,
    PaperResult,
    RetrievalStatus,
    VerificationReport,
)
from .page_state import PageState, assess_page
from .publishers import (
    PublisherProfile,
    build_pdf_candidates,
    discover_pdf_candidates,
    infer_profile,
)
from .verify import plausible_pdf_bytes, verify_pdf_bytes


@dataclass(slots=True)
class RetrievalOptions:
    output: Path
    workers: int = 1
    interactive: bool = False
    interactive_timeout_seconds: int = 300
    browser_enabled: bool = True
    resume: bool = True
    min_pdf_bytes: int = 5_000


@dataclass(slots=True)
class PreparedPaper:
    result: PaperResult
    profile: PublisherProfile
    landing_url: str


class SilentRetriever:
    def __init__(
        self,
        config: AppConfig,
        options: RetrievalOptions,
        *,
        progress: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.options = options
        self.progress = progress or (lambda _: None)
        self.options.output.mkdir(parents=True, exist_ok=True)

    def download_many(self, dois: list[str]) -> list[PaperResult]:
        normalized = list(dict.fromkeys(normalize_doi(doi) for doi in dois))
        completed: list[PaperResult] = []
        pending: list[PreparedPaper] = []
        direct = DirectClient(self.config)
        try:
            for index, doi in enumerate(normalized, 1):
                self.progress(f"[{index}/{len(normalized)}] preflight {doi}")
                prepared = self._prepare_direct(direct, doi)
                self.progress(
                    f"[{index}/{len(normalized)}] {prepared.result.status.value} "
                    f"{prepared.profile.key} {doi}"
                )
                if prepared.result.status in {
                    RetrievalStatus.SUCCESS,
                    RetrievalStatus.SKIPPED_EXISTING,
                }:
                    completed.append(prepared.result)
                else:
                    pending.append(prepared)
        finally:
            direct.close()

        if pending and self.options.browser_enabled and self.config.browser.enabled:
            groups: dict[str, list[PreparedPaper]] = {}
            for item in pending:
                groups.setdefault(item.profile.key, []).append(item)
            workers = max(1, min(self.options.workers, len(groups)))
            if workers == 1:
                for items in groups.values():
                    completed.extend(self._browser_group(items))
            else:
                with ThreadPoolExecutor(
                    max_workers=workers, thread_name_prefix="paper-pdf"
                ) as pool:
                    futures = [pool.submit(self._browser_group, items) for items in groups.values()]
                    for future in as_completed(futures):
                        completed.extend(future.result())
        else:
            for item in pending:
                if item.result.status == RetrievalStatus.PENDING:
                    item.result.status = RetrievalStatus.UNSUPPORTED
                    item.result.detail = "No verified direct PDF and browser route disabled"
                    write_paper_manifest(item.result)
                completed.append(item.result)

        order = {doi: index for index, doi in enumerate(normalized)}
        completed.sort(key=lambda item: order[item.doi])
        # Rebuild from every bundle in the library. A targeted retry must not
        # erase aggregate rows for DOI bundles that were not part of this run.
        write_aggregate_manifests(self.options.output)
        return completed

    def _prepare_direct(self, direct: DirectClient, doi: str) -> PreparedPaper:
        profile = infer_profile(doi)
        bundle = self.options.output / profile.key / safe_doi_name(doi)
        result = PaperResult(doi=doi, publisher=profile.key, bundle_dir=bundle)

        existing = self._existing_record(bundle) if self.options.resume else None
        if existing is not None:
            result = self._restore_existing_result(result, existing)
            write_paper_manifest(result)
            return PreparedPaper(result, profile, result.source_url)

        metadata = direct.metadata(doi)
        landing_url = direct.resolve_doi(doi) or metadata.landing_url
        resolved_profile = infer_profile(doi, landing_url)
        if resolved_profile.key != profile.key:
            profile = resolved_profile
            bundle = self.options.output / profile.key / safe_doi_name(doi)
            result = PaperResult(
                doi=doi, publisher=profile.key, bundle_dir=bundle, title=metadata.title
            )
            existing = self._existing_record(bundle) if self.options.resume else None
            if existing is not None:
                result = self._restore_existing_result(result, existing)
                write_paper_manifest(result)
                return PreparedPaper(result, profile, result.source_url)
        else:
            result.title = metadata.title

        result.attempts.append(
            Attempt("doi_metadata", "resolved" if landing_url else "miss", landing_url)
        )

        api_result = direct.elsevier_api_pdf(doi)
        if api_result is not None and self._accept_http(result, api_result, route="elsevier_api"):
            write_paper_manifest(result)
            return PreparedPaper(result, profile, landing_url)

        oa_candidates = direct.unpaywall_candidates(doi)
        candidate_urls = list(oa_candidates)
        candidate_urls.extend(build_pdf_candidates(profile, doi, source_url=landing_url))
        for url in list(dict.fromkeys(candidate_urls)):
            route = "unpaywall" if url in oa_candidates else "publisher_http"
            response = direct.fetch(url, referer=landing_url)
            if self._accept_http(result, response, route=route):
                write_paper_manifest(result)
                return PreparedPaper(result, profile, landing_url)

        write_paper_manifest(result)
        return PreparedPaper(result, profile, landing_url)

    def _browser_group(self, items: list[PreparedPaper]) -> list[PaperResult]:
        profile = items[0].profile
        results: list[PaperResult] = []
        try:
            with CloakPublisherSession(
                profile,
                self.config,
                interactive=self.options.interactive,
                interactive_timeout_seconds=self.options.interactive_timeout_seconds,
            ) as session:
                for item_index, item in enumerate(items):
                    result = item.result
                    self.progress(f"[browser:{profile.key}] {result.doi}")
                    try:
                        landing = session.land(result.doi, item.profile)
                    except Exception as exc:  # noqa: BLE001 - browser drivers expose version-specific exceptions
                        result.status = _status_from_browser_exception(exc)
                        result.detail = f"browser_navigation:{type(exc).__name__}:{exc}"
                        result.attempts.append(
                            Attempt("cloakbrowser", "error", detail=result.detail)
                        )
                        write_paper_manifest(result)
                        self.progress(f"[browser:{profile.key}] {result.status.value} {result.doi}")
                        results.append(result)
                        if result.status == RetrievalStatus.SESSION_LIMIT:
                            results.extend(
                                self._mark_session_limit(
                                    items[item_index + 1 :],
                                    "CloakBrowser session limit reached before this DOI",
                                )
                            )
                            break
                        continue

                    result.source_url = landing.url
                    if landing.assessment.state != PageState.READY:
                        result.status = _status_from_page_state(landing.assessment.state)
                        result.detail = landing.assessment.marker
                        result.attempts.append(
                            Attempt(
                                "cloakbrowser_landing",
                                landing.assessment.state.value,
                                landing.url,
                                landing.assessment.marker,
                            )
                        )
                        write_paper_manifest(result)
                        self.progress(f"[browser:{profile.key}] {result.status.value} {result.doi}")
                        results.append(result)
                        continue

                    queue = list(landing.candidates)
                    seen: set[str] = set()
                    while queue and len(seen) < self.config.browser.max_candidate_urls:
                        url = queue.pop(0)
                        if url in seen:
                            continue
                        seen.add(url)
                        browser_body = session.fetch(url, landing.url)
                        response = HttpResult(
                            url=url,
                            final_url=url,
                            status_code=browser_body.status_code,
                            content_type=browser_body.content_type,
                            body=browser_body.body,
                            detail=browser_body.detail,
                        )
                        if self._accept_http(result, response, route="cloakbrowser"):
                            break
                        if _looks_like_html(browser_body.content_type, browser_body.body):
                            html = browser_body.body.decode("utf-8", errors="replace")
                            assessment = assess_page("", browser_body.url, html)
                            if assessment.state != PageState.READY:
                                result.status = _status_from_page_state(assessment.state)
                                result.detail = assessment.marker
                                break
                            discovered = discover_pdf_candidates(html, browser_body.url)
                            expanded = build_pdf_candidates(
                                item.profile,
                                result.doi,
                                source_url=browser_body.url,
                                discovered=discovered,
                            )
                            queue.extend(
                                candidate for candidate in expanded if candidate not in seen
                            )
                    if result.status == RetrievalStatus.PENDING:
                        unverified = result.bundle_dir / "unverified.pdf"
                        if unverified.exists():
                            result.status = RetrievalStatus.UNVERIFIED_PDF
                            result.detail = (
                                "PDF candidate saved but target article could not be verified"
                            )
                        else:
                            result.status = RetrievalStatus.UNSUPPORTED
                            result.detail = "No article-owned PDF candidate returned a valid PDF"
                    write_paper_manifest(result)
                    self.progress(f"[browser:{profile.key}] {result.status.value} {result.doi}")
                    results.append(result)
        except Exception as exc:  # noqa: BLE001 - session startup/teardown can raise driver-native errors
            for item in items:
                result = item.result
                if result.status == RetrievalStatus.PENDING:
                    result.status = _status_from_browser_exception(exc)
                    result.detail = f"browser_session:{type(exc).__name__}:{exc}"
                    result.attempts.append(
                        Attempt("cloakbrowser_session", "error", detail=result.detail)
                    )
                    write_paper_manifest(result)
                results.append(result)
        return results

    def _mark_session_limit(self, items: list[PreparedPaper], detail: str) -> list[PaperResult]:
        results: list[PaperResult] = []
        for item in items:
            result = item.result
            result.status = RetrievalStatus.SESSION_LIMIT
            result.detail = detail
            result.attempts.append(Attempt("cloakbrowser_session", "session_limit", detail=detail))
            write_paper_manifest(result)
            self.progress(f"[browser:{item.profile.key}] session_limit {result.doi}")
            results.append(result)
        return results

    def _accept_http(self, result: PaperResult, response: HttpResult, *, route: str) -> bool:
        plausible, reason = plausible_pdf_bytes(response.body, min_bytes=self.options.min_pdf_bytes)
        if not plausible:
            result.attempts.append(
                Attempt(
                    route,
                    reason,
                    response.final_url or response.url,
                    response.detail,
                    response.status_code,
                )
            )
            return False

        verification = verify_pdf_bytes(
            response.body,
            result.doi,
            expected_title=result.title,
            source_url=response.final_url or response.url,
            min_bytes=self.options.min_pdf_bytes,
        )
        result.attempts.append(
            Attempt(
                route,
                verification.reason,
                response.final_url or response.url,
                response.detail,
                response.status_code,
            )
        )
        if verification.is_supplement:
            result.status = RetrievalStatus.REJECTED_SUPPLEMENT
            result.verification = verification
            return False
        if not verification.verified:
            self._write_candidate(result.bundle_dir / "unverified.pdf", response.body)
            result.verification = verification
            return False

        self._write_candidate(result.bundle_dir / "paper.pdf", response.body)
        unverified = result.bundle_dir / "unverified.pdf"
        if unverified.exists():
            unverified.unlink()
        result.status = RetrievalStatus.SUCCESS
        result.pdf_path = "paper.pdf"
        result.source_route = route
        result.source_url = response.final_url or response.url
        result.verification = verification
        result.detail = verification.reason
        return True

    @staticmethod
    def _write_candidate(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".partial")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    @staticmethod
    def _existing_record(bundle: Path) -> dict[str, object] | None:
        manifest = bundle / "manifest.json"
        pdf = bundle / "paper.pdf"
        if not (manifest.exists() and pdf.exists()):
            return None
        try:
            record = read_paper_manifest(manifest)
            return record if record.get("status") in {"success", "skipped_existing"} else None
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _restore_existing_result(result: PaperResult, record: dict[str, object]) -> PaperResult:
        result.status = RetrievalStatus.SKIPPED_EXISTING
        result.pdf_path = str(record.get("pdf_path") or "paper.pdf")
        result.source_route = str(record.get("source_route") or "existing")
        result.source_url = str(record.get("source_url") or "")
        result.title = str(record.get("title") or result.title)
        result.detail = "Verified PDF already present"
        verification = record.get("verification")
        if isinstance(verification, dict):
            allowed = VerificationReport.__dataclass_fields__
            result.verification = VerificationReport(
                **{key: value for key, value in verification.items() if key in allowed}
            )
        conversion = record.get("conversion")
        if isinstance(conversion, dict):
            allowed = ConversionReport.__dataclass_fields__
            result.conversion = ConversionReport(
                **{key: value for key, value in conversion.items() if key in allowed}
            )
        attempts = record.get("attempts")
        if isinstance(attempts, list):
            allowed = Attempt.__dataclass_fields__
            result.attempts = [
                Attempt(**{key: value for key, value in item.items() if key in allowed})
                for item in attempts
                if isinstance(item, dict)
            ]
        result.attempts.append(Attempt("resume", "skipped_existing"))
        return result


def _status_from_page_state(state: PageState) -> RetrievalStatus:
    return {
        PageState.CHALLENGE_REQUIRED: RetrievalStatus.CHALLENGE_REQUIRED,
        PageState.AUTH_REQUIRED: RetrievalStatus.AUTH_REQUIRED,
        PageState.BLOCKED: RetrievalStatus.BLOCKED,
        PageState.NOT_FOUND: RetrievalStatus.NOT_FOUND,
        PageState.READY: RetrievalStatus.PENDING,
    }[state]


def _looks_like_html(content_type: str, body: bytes) -> bool:
    prefix = body[:512].lstrip().lower()
    return "html" in content_type or prefix.startswith(
        (b"<!doctype html", b"<html", b"<head", b"<body")
    )


def _status_from_browser_exception(exc: Exception) -> RetrievalStatus:
    return (
        RetrievalStatus.SESSION_LIMIT
        if "session limit" in str(exc).lower()
        else RetrievalStatus.ERROR
    )
