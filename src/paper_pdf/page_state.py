"""Pure publisher page-state classification used by silent browser sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class PageState(StrEnum):
    READY = "ready"
    CHALLENGE_REQUIRED = "challenge_required"
    AUTH_REQUIRED = "auth_required"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class PageAssessment:
    state: PageState
    marker: str = ""


CHALLENGE_MARKERS = (
    "verify you are human",
    "checking your browser",
    "just a moment",
    "cf-chl-",
    "cf-turnstile",
    "cloudflare turnstile",
    "hcaptcha",
    "g-recaptcha",
    "recaptcha",
    "human verification",
    "security verification",
)
BLOCKED_MARKERS = (
    "access denied",
    "request rejected",
    "unusual traffic",
    "automated access is prohibited",
    "incident id",
    "temporarily blocked",
)
NOT_FOUND_MARKERS = ("page not found", "article not found", "doi not found", "404 not found")
AUTH_HOST_MARKERS = ("login.", "idp.", "shibboleth", "openathens", "ezproxy")
AUTH_PATH_MARKERS = (
    "/login",
    "/signin",
    "/sign-in",
    "/saml",
    "/authenticate",
    "/institutional-login",
)


def assess_page(title: str, url: str, text_or_html: str) -> PageAssessment:
    haystack = f"{title}\n{text_or_html[:200_000]}".lower()
    for marker in CHALLENGE_MARKERS:
        if marker in haystack:
            return PageAssessment(PageState.CHALLENGE_REQUIRED, marker)
    for marker in BLOCKED_MARKERS:
        if marker in haystack:
            return PageAssessment(PageState.BLOCKED, marker)
    for marker in NOT_FOUND_MARKERS:
        if marker in haystack:
            return PageAssessment(PageState.NOT_FOUND, marker)

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if any(marker in host for marker in AUTH_HOST_MARKERS) or any(
        marker in path for marker in AUTH_PATH_MARKERS
    ):
        return PageAssessment(PageState.AUTH_REQUIRED, host or path)
    return PageAssessment(PageState.READY)
