"""Lazy CloakBrowser adapter for persistent, publisher-isolated silent sessions."""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from .config import AppConfig
from .page_state import PageAssessment, PageState, assess_page
from .publishers import PublisherProfile, build_pdf_candidates, discover_pdf_candidates
from .verify import plausible_pdf_bytes


@dataclass(slots=True)
class BrowserLanding:
    url: str
    title: str
    assessment: PageAssessment
    candidates: list[str]


@dataclass(slots=True)
class BrowserBody:
    url: str
    status_code: int
    content_type: str
    body: bytes
    detail: str = ""


class CloakPublisherSession:
    def __init__(
        self,
        profile: PublisherProfile,
        config: AppConfig,
        *,
        interactive: bool = False,
        interactive_timeout_seconds: int = 300,
    ):
        self.profile = profile
        self.config = config
        self.interactive = interactive
        self.interactive_timeout_seconds = interactive_timeout_seconds
        self.context: Any = None
        self.page: Any = None

    def __enter__(self) -> Self:
        try:
            from cloakbrowser import launch_persistent_context
        except ImportError as exc:
            raise RuntimeError(
                "CloakBrowser is not installed in this Python environment. "
                "Install the browser extra and run 'cloakbrowser install'."
            ) from exc

        profile_dir = Path(self.config.browser.profile_dir).expanduser() / self.profile.key
        profile_dir.mkdir(parents=True, exist_ok=True)
        self.context = launch_persistent_context(
            str(profile_dir),
            headless=self.config.browser.headless and not self.interactive,
            humanize=self.config.browser.humanize,
            args=list(self.config.browser.args),
        )
        pages = list(getattr(self.context, "pages", []) or [])
        self.page = pages[0] if pages else self.context.new_page()
        self.page.set_default_timeout(self.config.browser.navigation_timeout_seconds * 1000)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.context is not None:
            self.context.close()

    def land(self, doi: str, profile: PublisherProfile | None = None) -> BrowserLanding:
        active_profile = profile or self.profile
        try:
            self.page.goto(
                f"https://doi.org/{doi}",
                wait_until="domcontentloaded",
                timeout=self.config.browser.navigation_timeout_seconds * 1000,
            )
        except Exception:  # noqa: BLE001, S110 - timeout may still leave a usable page
            pass
        time.sleep(self.config.browser.settle_seconds)
        landing = self._snapshot(active_profile, doi)
        if (
            landing.assessment.state in {PageState.CHALLENGE_REQUIRED, PageState.AUTH_REQUIRED}
            and self.interactive
        ):
            print(
                f"Interactive handoff: complete {landing.assessment.state.value} in the visible browser; "
                f"waiting up to {self.interactive_timeout_seconds}s.",
                flush=True,
            )
            deadline = time.monotonic() + self.interactive_timeout_seconds
            while time.monotonic() < deadline:
                time.sleep(2)
                landing = self._snapshot(active_profile, doi)
                if landing.assessment.state == PageState.READY:
                    break
        return landing

    def fetch(self, url: str, referer: str) -> BrowserBody:
        best = BrowserBody(url, 0, "", b"", "no_fetch_attempt")
        try:
            kwargs: dict[str, object] = {
                "timeout": self.config.browser.candidate_timeout_seconds * 1000
            }
            if referer:
                kwargs["headers"] = {"Referer": referer}
            response = self.context.request.get(url, **kwargs)
            body = response.body()
            content_type = response.headers.get("content-type", "").lower()
            best = BrowserBody(url, response.status, content_type, body)
            if _is_pdf(body):
                return best
        except Exception as exc:  # noqa: BLE001 - third-party browser request errors vary by release
            request_error = f"request_context:{type(exc).__name__}:{exc}"
        else:
            request_error = f"request_context_status:{best.status_code}"

        try:
            encoded = self.page.evaluate(
                """async ({url, timeoutMs}) => {
                    const controller = new AbortController();
                    const timer = setTimeout(() => controller.abort(), timeoutMs);
                    const response = await fetch(url, {
                      credentials: 'include', signal: controller.signal
                    });
                    const bytes = new Uint8Array(await response.arrayBuffer());
                    clearTimeout(timer);
                    let binary = '';
                    const chunk = 0x8000;
                    for (let i = 0; i < bytes.length; i += chunk) {
                      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
                    }
                    return {status: response.status,
                            type: response.headers.get('content-type') || '',
                            data: btoa(binary)};
                }""",
                {"url": url, "timeoutMs": self.config.browser.candidate_timeout_seconds * 1000},
            )
            in_page = BrowserBody(
                url,
                int(encoded.get("status", 0)),
                str(encoded.get("type", "")).lower(),
                base64.b64decode(encoded.get("data", "")),
                request_error,
            )
            if _is_pdf(in_page.body):
                return in_page
            if in_page.body and in_page.status_code < 400:
                best = in_page
        except Exception as exc:  # noqa: BLE001 - page.evaluate exposes browser-native error types
            request_error += f";page_fetch:{type(exc).__name__}:{exc}"

        download_page = None
        try:
            download_page = self.context.new_page()
            response = download_page.goto(
                url,
                wait_until="commit",
                timeout=self.config.browser.candidate_timeout_seconds * 1000,
            )
            if response is not None:
                body = response.body()
                navigated = BrowserBody(
                    download_page.url,
                    response.status,
                    response.headers.get("content-type", "").lower(),
                    body,
                    request_error,
                )
                if _is_pdf(body):
                    return navigated
                if body and navigated.status_code < 400:
                    best = navigated
            time.sleep(min(1.0, self.config.browser.settle_seconds))
            html = download_page.content().encode("utf-8", errors="replace")
            if html and not best.body:
                best = BrowserBody(download_page.url, 200, "text/html", html, request_error)
        except Exception as exc:  # noqa: BLE001 - navigation fallback exposes driver-native errors
            request_error += f";navigation_fetch:{type(exc).__name__}:{exc}"
        finally:
            if download_page is not None:
                try:
                    download_page.close()
                except Exception:  # noqa: BLE001, S110 - best-effort cleanup of an owned page
                    pass
        best.detail = request_error
        return best

    def _snapshot(self, profile: PublisherProfile, doi: str) -> BrowserLanding:
        last_error: Exception | None = None
        for _ in range(6):
            try:
                title = self.page.title()
                url = self.page.url
                html = self.page.content()
                break
            except Exception as exc:
                if "session limit" in str(exc).lower():
                    raise RuntimeError(str(exc)) from exc
                last_error = exc
                time.sleep(0.5)
        else:
            raise RuntimeError(f"Unable to snapshot stable publisher page: {last_error}")
        assessment = assess_page(title, url, html)
        discovered = (
            discover_pdf_candidates(html, url) if assessment.state == PageState.READY else []
        )
        candidates = build_pdf_candidates(profile, doi, source_url=url, discovered=discovered)
        return BrowserLanding(url, title, assessment, candidates)


def _is_pdf(body: bytes) -> bool:
    return plausible_pdf_bytes(body)[0]
