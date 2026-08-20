# Authorized Paper Retrieval

`paper-pdf-download-skill` packages an independent, silent-first public agent workflow that retrieves research papers the user is entitled to access, verifies the main article, and optionally converts it into Markdown.

## Identity

- GitHub repository name: `paper-pdf-download-skill`
- Retrieval skill name: `paper-pdf-download`
- Optional conversion skill name: `paper-pdf-to-markdown`
- Project license: MIT
- Documentation: English primary README plus a complete Simplified Chinese README
- GitHub target: `wxt18757928900-lgtm/paper-pdf-download-skill`
- Runtime packaging: installable Python CLI package (`pipx`/`uv tool`) with two thin agent skills

## Language

**Authorized full-text retrieval**:
Obtaining an open-access paper or a paper covered by the user's existing institution, campus, library, or publisher-API entitlement.
_Avoid_: Paywall bypass, universal download, CAPTCHA cracking

**Verified main article**:
A structurally valid PDF whose DOI or equivalent metadata matches the requested paper and which is not labelled as supplementary/supporting material.
_Avoid_: Downloaded PDF, first PDF, successful response

**Manual challenge handoff**:
An explicitly enabled interactive mode that preserves a live browser profile while the user personally completes a CAPTCHA, SSO, OTP, or similar gate. It is never triggered in the default silent mode.
_Avoid_: CAPTCHA bypass, automated verification

**Conversion bundle**:
The optional output for one verified paper containing the original PDF, Markdown, extracted assets, conversion metadata, and any conversion error record.
_Avoid_: Markdown file

**PDF-only completion**:
A paper outcome in which the verified main-article PDF is saved locally and Markdown conversion was not requested.

**PDF+Markdown completion**:
A paper outcome in which both the verified main-article PDF and a validated conversion bundle are saved locally.

**Paper bundle**:
A DOI-keyed directory containing `paper.pdf`, optional `paper.md`, optional `assets/`, and `manifest.json`. A batch root also contains a machine-readable aggregate manifest.
_Avoid_: Flat download folder

## Relationships

- An **Authorized full-text retrieval** produces zero or one **Verified main article** per requested DOI.
- A **Verified main article** may produce one **Conversion bundle**.
- Every requested DOI owns one **Paper bundle**, including failed and partial outcomes so provenance is not lost.
- A **Manual challenge handoff** may pause an **Authorized full-text retrieval** without changing its entitlement boundary.
- A run has either **PDF-only completion** or **PDF+Markdown completion**, according to the user's selected output mode.

## Product Boundary

The repository is a complete safe project, not a raw dump of the current local skill. It includes two independently installable, composable agent skills: `paper-pdf-download` for silent, verified retrieval and `paper-pdf-to-markdown` for MinerU conversion. An end-to-end workflow can invoke both, while PDF-only users do not need MinerU. It also includes a rewritten standalone downloader/orchestrator, publisher-specific routing and detection, documentation, and tests.

InstSci is neither bundled nor invoked and its skill is not part of this repository. Its breadth of publisher coverage, layered detection, batching, and verification may inform the independent design, with attribution wherever code or distinctive implementation is actually reused. MinerU remains an external CLI dependency. The project owns silent browser orchestration, verification, manifests, resumption, and user-facing skill instructions. Markdown conversion is opt-in.

It does not claim to break paywalls, solve CAPTCHAs, or guarantee access to every publisher. The current experimental downloader is reference material only and is not releasable as-is because it lacks DOI/main-article verification, publisher profile isolation, and reliable network-route enforcement.

Retrieval is silent by default: no browser window and no human action. Persistent challenges are recorded as `challenge_required` or `auth_required`, and the batch continues. A visible **Manual challenge handoff** is available only when the user explicitly enables interactive mode; automated CAPTCHA operation is outside the public project boundary.

MinerU conversion is local-first. Uploading a PDF to MinerU Open API requires explicit user selection; subscription PDFs are never uploaded silently.

Output is organized as one **Paper bundle** per DOI. Conversion failure retains the verified PDF and records a partial outcome instead of deleting or misreporting it. The batch root contains an aggregate manifest for resuming and auditing work.

Institutional access configuration is public-template/private-override: the repository contains a generic documented example, while institution names, campus/VPN routing rules, credentials, API keys, browser profiles, and machine-specific paths live only in a gitignored local override. Tsinghua is not a built-in public default.

## Example dialogue

> **User:** "Download these ten papers and turn them into Markdown."
> **Agent:** "I will perform silent **Authorized full-text retrieval**, retain only each **Verified main article**, and then create a **Conversion bundle** locally. Any challenge that cannot be handled silently will be classified explicitly rather than counted as a download."

## Flagged ambiguities

- "Success" previously meant any response beginning with `%PDF-`; resolved: use **PDF-only completion** or **PDF+Markdown completion**.
- "Bypass" previously mixed stealth-based challenge prevention with CAPTCHA solving; resolved: automated solving is outside the product boundary.
