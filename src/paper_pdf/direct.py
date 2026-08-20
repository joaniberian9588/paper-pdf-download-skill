"""Silent HTTP, metadata, OA, and publisher-API preflight routes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from .config import AppConfig, configured_elsevier_credentials
from .verify import plausible_pdf_bytes


@dataclass(slots=True)
class PaperMetadata:
    title: str = ""
    publisher: str = ""
    landing_url: str = ""


@dataclass(slots=True)
class HttpResult:
    url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    detail: str = ""


class DirectClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.network.user_agent})

    def close(self) -> None:
        self.session.close()

    def metadata(self, doi: str) -> PaperMetadata:
        metadata = PaperMetadata()
        try:
            response = self.session.get(
                f"https://api.crossref.org/works/{quote(doi, safe='')}",
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
            if response.ok:
                message = response.json().get("message", {})
                titles = message.get("title") or []
                metadata.title = str(titles[0]).strip() if titles else ""
                metadata.publisher = str(message.get("publisher") or "").strip()
                metadata.landing_url = str(message.get("URL") or "").strip()
        except (requests.RequestException, ValueError, TypeError):
            pass
        return metadata

    def resolve_doi(self, doi: str) -> str:
        try:
            response = self.session.get(
                f"https://doi.org/{quote(doi, safe='/')}",
                allow_redirects=True,
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
            return response.url if response.url else ""
        except requests.RequestException:
            return ""

    def unpaywall_candidates(self, doi: str) -> list[str]:
        email = self.config.apis.unpaywall_email.strip()
        if not email:
            return []
        try:
            response = self.session.get(
                f"https://api.unpaywall.org/v2/{quote(doi, safe='')}",
                params={"email": email},
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        locations: list[dict[str, Any]] = []
        best = payload.get("best_oa_location")
        if isinstance(best, dict):
            locations.append(best)
        locations.extend(item for item in payload.get("oa_locations", []) if isinstance(item, dict))
        urls: list[str] = []
        for location in locations:
            for key in ("url_for_pdf", "url"):
                value = str(location.get(key) or "").strip()
                if value and value not in urls:
                    urls.append(value)
        return urls

    def fetch(self, url: str, *, referer: str = "") -> HttpResult:
        headers = {"Referer": referer} if referer else None
        try:
            response = self.session.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
            return HttpResult(
                url=url,
                final_url=response.url,
                status_code=response.status_code,
                content_type=response.headers.get("content-type", "").lower(),
                body=response.content,
            )
        except requests.RequestException as exc:
            return HttpResult(url, "", 0, "", b"", f"{type(exc).__name__}:{exc}")

    def elsevier_api_pdf(self, doi: str) -> HttpResult | None:
        api_key, inst_token = configured_elsevier_credentials(self.config)
        if not api_key or not doi.startswith("10.1016/"):
            return None
        headers = {
            "X-ELS-APIKey": api_key,
            "Accept": "application/pdf, application/xml;q=0.8",
        }
        if inst_token:
            headers["X-ELS-Insttoken"] = inst_token
        article_url = f"https://api.elsevier.com/content/article/doi/{quote(doi, safe='')}"
        try:
            response = self.session.get(
                article_url,
                params={"view": "FULL"},
                headers=headers,
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
        except requests.RequestException as exc:
            return HttpResult(article_url, "", 0, "", b"", f"{type(exc).__name__}:{exc}")

        plausible, _ = plausible_pdf_bytes(response.content)
        if plausible:
            return HttpResult(
                article_url,
                response.url,
                response.status_code,
                response.headers.get("content-type", "").lower(),
                response.content,
            )

        text = response.text[:1_000_000]
        match = re.search(r"<(?:dc:identifier|eid)[^>]*>(?:EID:)?([^<]+)</", text, re.IGNORECASE)
        if not match:
            return HttpResult(
                article_url,
                response.url,
                response.status_code,
                response.headers.get("content-type", "").lower(),
                response.content,
                "elsevier_fulltext_not_pdf_and_no_eid",
            )

        eid = match.group(1).strip()
        object_url = f"https://api.elsevier.com/content/object/eid/{quote(eid, safe='')}"
        try:
            pdf_response = self.session.get(
                object_url,
                headers={**headers, "Accept": "application/pdf"},
                timeout=self.config.network.timeout_seconds,
                verify=self.config.network.verify_tls,
            )
            return HttpResult(
                object_url,
                pdf_response.url,
                pdf_response.status_code,
                pdf_response.headers.get("content-type", "").lower(),
                pdf_response.content,
            )
        except requests.RequestException as exc:
            return HttpResult(object_url, "", 0, "", b"", f"{type(exc).__name__}:{exc}")
