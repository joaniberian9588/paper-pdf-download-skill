"""Declarative publisher coverage and article-owned PDF candidate routing.

The routes are ordinary publisher URL patterns and HTML metadata conventions.
They are intentionally separate from browser automation so coverage can be
tested without contacting publisher sites.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

SUPPLEMENT_MARKERS = (
    "supplement",
    "supplementary",
    "supporting-information",
    "supporting_information",
    "suppl_file",
    "mmc1",
    "mmc2",
    "mmc3",
)
PDF_URL_MARKERS = (".pdf", "/pdf", "/epdf", "/pdfdirect", "/pdfft", "download=true")
TRUSTED_ASSET_DOMAINS = {
    "elsevier": ("sciencedirectassets.com", "els-cdn.com"),
    "frontiers": ("frontiersin.org",),
    "ieee": ("ieee.org",),
    "mdpi": ("mdpi-res.com",),
    "springer-nature": ("springer.com", "nature.com"),
}


@dataclass(frozen=True, slots=True)
class PublisherProfile:
    key: str
    name: str
    prefixes: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    templates: tuple[str, ...] = ()
    pdf_markers: tuple[str, ...] = PDF_URL_MARKERS
    supplement_markers: tuple[str, ...] = SUPPLEMENT_MARKERS
    aliases: tuple[str, ...] = field(default_factory=tuple)

    def template_urls(self, doi: str) -> list[str]:
        suffix = doi.split("/", 1)[-1]
        values = {
            "doi": doi,
            "doi_quoted": quote(doi, safe=""),
            "suffix": suffix,
            "suffix_quoted": quote(suffix, safe=""),
        }
        return [template.format(**values) for template in self.templates]


PROFILES = (
    PublisherProfile(
        "acs",
        "American Chemical Society",
        ("10.1021",),
        ("pubs.acs.org",),
        (
            "https://pubs.acs.org/doi/pdf/{doi}?ref=article_openPDF",
            "https://pubs.acs.org/doi/epdf/{doi}",
        ),
    ),
    PublisherProfile(
        "acm", "ACM", ("10.1145", "10.5555"), ("dl.acm.org",), ("https://dl.acm.org/doi/pdf/{doi}",)
    ),
    PublisherProfile(
        "aps",
        "American Physical Society",
        ("10.1103",),
        ("journals.aps.org", "link.aps.org"),
        ("https://link.aps.org/pdf/{doi}",),
    ),
    PublisherProfile(
        "annual-reviews",
        "Annual Reviews",
        ("10.1146",),
        ("annualreviews.org",),
        ("https://www.annualreviews.org/doi/pdf/{doi}",),
    ),
    PublisherProfile("asme", "ASME", ("10.1115",), ("asmedigitalcollection.asme.org",), ()),
    PublisherProfile(
        "frontiers",
        "Frontiers",
        ("10.3389",),
        ("frontiersin.org",),
        (
            "https://www.frontiersin.org/journals/articles/{doi}/pdf",
            "https://www.frontiersin.org/articles/{doi}/pdf",
        ),
    ),
    PublisherProfile(
        "wiley",
        "Wiley",
        ("10.1002", "10.1111"),
        ("onlinelibrary.wiley.com",),
        (
            "https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
            "https://onlinelibrary.wiley.com/doi/pdf/{doi}",
            "https://onlinelibrary.wiley.com/doi/epdf/{doi}",
        ),
    ),
    PublisherProfile(
        "elsevier",
        "Elsevier / ScienceDirect",
        ("10.1016",),
        ("sciencedirect.com", "linkinghub.elsevier.com", "elsevier.com"),
        (),
    ),
    PublisherProfile("ieee", "IEEE", ("10.1109",), ("ieeexplore.ieee.org",), ()),
    PublisherProfile(
        "iop",
        "IOP Publishing",
        ("10.1088",),
        ("iopscience.iop.org",),
        ("https://iopscience.iop.org/article/{doi}/pdf",),
    ),
    PublisherProfile(
        "rsc",
        "Royal Society of Chemistry",
        ("10.1039",),
        ("pubs.rsc.org",),
        ("https://pubs.rsc.org/en/content/articlepdf/{doi}",),
    ),
    PublisherProfile(
        "springer-nature",
        "Springer Nature",
        ("10.1007", "10.1038"),
        ("link.springer.com", "nature.com"),
        (
            "https://link.springer.com/content/pdf/{doi_quoted}.pdf",
            "https://www.nature.com/articles/{suffix}.pdf",
        ),
        aliases=("springer", "nature"),
    ),
    PublisherProfile(
        "world-scientific",
        "World Scientific",
        ("10.1142",),
        ("worldscientific.com",),
        ("https://www.worldscientific.com/doi/pdf/{doi}",),
    ),
    PublisherProfile(
        "aip",
        "AIP Publishing",
        ("10.1063",),
        ("pubs.aip.org",),
        (
            "https://pubs.aip.org/doi/epdf/{doi}",
            "https://pubs.aip.org/doi/pdf/{doi}",
        ),
    ),
    PublisherProfile(
        "ams",
        "American Meteorological Society",
        ("10.1175",),
        ("journals.ametsoc.org",),
        (
            "https://journals.ametsoc.org/doi/epdf/{doi}",
            "https://journals.ametsoc.org/doi/pdf/{doi}",
        ),
    ),
    PublisherProfile(
        "copernicus", "Copernicus Publications", ("10.5194",), ("copernicus.org",), ()
    ),
    PublisherProfile("mdpi", "MDPI", ("10.3390",), ("mdpi.com",), ()),
    PublisherProfile(
        "oxford",
        "Oxford Academic",
        ("10.1093",),
        ("academic.oup.com",),
        (
            "https://academic.oup.com/doi/pdf/{doi}",
            "https://academic.oup.com/doi/epdf/{doi}",
        ),
        aliases=("oup", "oxford-academic"),
    ),
    PublisherProfile("plos", "PLOS", ("10.1371",), ("journals.plos.org",), ()),
    PublisherProfile(
        "pnas",
        "PNAS",
        ("10.1073",),
        ("pnas.org",),
        (
            "https://www.pnas.org/doi/epdf/{doi}",
            "https://www.pnas.org/doi/pdf/{doi}?download=true",
        ),
    ),
    PublisherProfile(
        "royal-society",
        "Royal Society Publishing",
        ("10.1098",),
        ("royalsocietypublishing.org",),
        ("https://royalsocietypublishing.org/doi/pdf/{doi}",),
    ),
    PublisherProfile(
        "science",
        "AAAS / Science",
        ("10.1126",),
        ("science.org",),
        (
            "https://www.science.org/doi/epdf/{doi}",
            "https://www.science.org/doi/pdf/{doi}?download=true",
        ),
    ),
    PublisherProfile(
        "sage",
        "SAGE",
        ("10.1177",),
        ("journals.sagepub.com",),
        ("https://journals.sagepub.com/doi/pdf/{doi}",),
    ),
    PublisherProfile(
        "taylor-francis",
        "Taylor & Francis",
        ("10.1080",),
        ("tandfonline.com",),
        ("https://www.tandfonline.com/doi/pdf/{doi}?download=true",),
        aliases=("tandf",),
    ),
    PublisherProfile(
        "cambridge", "Cambridge University Press", ("10.1017",), ("cambridge.org",), ()
    ),
    PublisherProfile("emerald", "Emerald", ("10.1108",), ("emerald.com",), ()),
    PublisherProfile("generic", "Other publisher"),
)

PROFILE_BY_KEY = {profile.key: profile for profile in PROFILES}
for _profile in PROFILES:
    for _alias in _profile.aliases:
        PROFILE_BY_KEY[_alias] = _profile


def get_profile(name: str) -> PublisherProfile:
    try:
        return PROFILE_BY_KEY[name.strip().lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown publisher profile: {name}") from exc


def infer_profile(doi: str, url: str = "") -> PublisherProfile:
    normalized = doi.lower()
    host = urlparse(url).hostname or ""
    host = host.lower()
    if host:
        for profile in PROFILES:
            if any(host == domain or host.endswith(f".{domain}") for domain in profile.domains):
                return profile
    for profile in PROFILES:
        if any(normalized.startswith(prefix) for prefix in profile.prefixes):
            return profile
    return PROFILE_BY_KEY["generic"]


def is_supplementary_url(profile: PublisherProfile, url: str) -> bool:
    lower = unquote(url).lower()
    return any(marker in lower for marker in profile.supplement_markers)


def is_pdf_candidate_url(profile: PublisherProfile, url: str) -> bool:
    lower = unquote(url).lower()
    return any(marker.lower() in lower for marker in profile.pdf_markers)


def discover_pdf_candidates(html: str, source_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    candidates: list[str] = []

    for meta in soup.find_all("meta"):
        key = str(meta.get("name") or meta.get("property") or meta.get("itemprop") or "").lower()
        content = str(meta.get("content") or "").strip()
        if content and ("citation_pdf_url" in key or key.endswith("pdf_url") or key == "pdf_url"):
            _append(candidates, content, source_url)

    for tag in soup.find_all(["a", "embed", "iframe", "object", "source"]):
        target = str(tag.get("href") or tag.get("src") or tag.get("data") or "").strip()
        label = " ".join(tag.stripped_strings).lower()
        content_type = str(tag.get("type") or "").lower()
        if target and (
            any(marker in target.lower() for marker in PDF_URL_MARKERS)
            or "pdf" in label
            or "pdf" in content_type
        ):
            _append(candidates, target, source_url)
            _append_query_embeds(candidates, target, source_url)

    script_text = "\n".join(node.get_text(" ", strip=True) for node in soup.find_all("script"))
    for raw in re.findall(
        r"(?:https?:)?//[^\s'\"<>]+?(?:\.pdf|/pdfft)[^\s'\"<>]*", script_text, re.IGNORECASE
    ):
        _append(candidates, raw, source_url)
    for raw in re.findall(r"defaultUrl['\"]?\s*[,=:]\s*['\"]([^'\"]+)", script_text, re.IGNORECASE):
        _append(candidates, raw, source_url)
    return candidates


def build_pdf_candidates(
    profile: PublisherProfile,
    doi: str,
    *,
    source_url: str = "",
    discovered: list[str] | None = None,
) -> list[str]:
    candidates: list[str] = []
    _append_special_routes(candidates, profile, doi, source_url)
    for url in profile.template_urls(doi):
        _append(candidates, url, source_url)
    for url in discovered or []:
        if is_supplementary_url(profile, url):
            continue
        if not is_pdf_candidate_url(profile, url):
            continue
        if belongs_to_current_article(profile, url, doi=doi, source_url=source_url):
            _append(candidates, url, source_url)
    return [url for url in candidates if not is_supplementary_url(profile, url)]


def belongs_to_current_article(
    profile: PublisherProfile,
    url: str,
    *,
    doi: str,
    source_url: str = "",
) -> bool:
    lower = unquote(url).lower()
    if is_supplementary_url(profile, lower):
        return False
    doi_lower = doi.lower()
    embedded_dois = [
        match.rstrip(".,;:!?)]}").lower()
        for match in re.findall(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", lower, re.IGNORECASE)
    ]
    if embedded_dois and doi_lower not in embedded_dois:
        return False
    candidate_host = (urlparse(url).hostname or "").lower()
    if profile.key != "generic" and candidate_host:
        trusted_domains = (*profile.domains, *TRUSTED_ASSET_DOMAINS.get(profile.key, ()))
        trusted_host = any(
            candidate_host == domain or candidate_host.endswith(f".{domain}")
            for domain in trusted_domains
        )
        if not trusted_host and doi_lower not in embedded_dois:
            return False
    if "/doi/" in lower and any(marker in lower for marker in ("/pdf", "/epdf", "/pdfdirect")):
        return doi_lower in lower or quote(doi_lower, safe="").lower() in lower
    source_pii = _extract_elsevier_pii(source_url)
    candidate_pii = _extract_elsevier_pii(url)
    if source_pii and candidate_pii:
        return source_pii.lower() == candidate_pii.lower()
    return True


def _append_special_routes(
    candidates: list[str], profile: PublisherProfile, doi: str, source_url: str
) -> None:
    parsed = urlparse(source_url)
    path = parsed.path
    if profile.key == "elsevier":
        pii = _extract_elsevier_pii(source_url)
        if pii:
            _append(candidates, f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft")
    elif profile.key == "ieee":
        match = re.search(r"/(?:document|abstract/document)/(\d+)", source_url)
        if match:
            arnumber = match.group(1)
            _append(
                candidates,
                f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&isnumber=&arnumber={arnumber}",
            )
    elif profile.key == "rsc" and "/articlelanding/" in path:
        _append(
            candidates,
            urlunparse(
                parsed._replace(path=path.replace("/articlelanding/", "/articlepdf/"), query="")
            ),
        )
    elif profile.key == "aps" and "/abstract/" in path:
        _append(
            candidates,
            urlunparse(parsed._replace(path=path.replace("/abstract/", "/pdf/"), query="")),
        )
    elif profile.key == "plos":
        journal = _plos_journal(doi, source_url)
        _append(
            candidates, f"https://journals.plos.org/{journal}/article/file?id={doi}&type=printable"
        )
    elif profile.key == "copernicus":
        match = re.match(r"10\.5194/([a-z0-9-]+)-(\d+)-(\d+)-(\d{4})", doi, re.IGNORECASE)
        if match:
            journal, volume, page, year = match.groups()
            _append(
                candidates,
                f"https://{journal}.copernicus.org/articles/{volume}/{page}/{year}/{doi.split('/', 1)[1]}.pdf",
            )
    elif profile.key == "mdpi" and source_url:
        clean_path = path.rstrip("/")
        if clean_path and not clean_path.endswith("/pdf"):
            _append(candidates, urlunparse(parsed._replace(path=f"{clean_path}/pdf", query="")))
    elif profile.key == "ams" and path.endswith(".xml") and "/view/journals/" in path:
        _append(
            candidates, urlunparse(parsed._replace(path=f"/downloadpdf{path[:-4]}.pdf", query=""))
        )


def _plos_journal(doi: str, source_url: str) -> str:
    host = (urlparse(source_url).hostname or "").lower()
    if host.startswith("journals.plos.org"):
        first = urlparse(source_url).path.strip("/").split("/", 1)[0]
        if first:
            return first
    match = re.match(r"10\.1371/journal\.([a-z0-9]+)\.", doi, re.IGNORECASE)
    return match.group(1) if match else "plosone"


def _extract_elsevier_pii(url: str) -> str:
    match = re.search(r"(?:pii/|retrieve/pii/|1-s2\.0-)([A-Z0-9]+)", url, re.IGNORECASE)
    return match.group(1) if match else ""


def _append(candidates: list[str], candidate: str, source_url: str = "") -> None:
    value = candidate.strip()
    if not value:
        return
    if value.startswith("//"):
        value = "https:" + value
    value = urljoin(source_url, value)
    if value.startswith(("http://", "https://")) and value not in candidates:
        candidates.append(value)


def _append_query_embeds(candidates: list[str], candidate: str, source_url: str) -> None:
    absolute = urljoin(source_url, candidate)
    for key, values in parse_qs(urlparse(absolute).query).items():
        if key.lower() not in {"file", "pdf", "src", "url"}:
            continue
        for value in values:
            if any(marker in value.lower() for marker in PDF_URL_MARKERS):
                _append(candidates, value, absolute)


def list_profiles() -> list[PublisherProfile]:
    return [profile for profile in PROFILES if profile.key != "generic"]
