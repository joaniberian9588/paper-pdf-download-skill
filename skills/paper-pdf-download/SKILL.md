---
name: paper-pdf-download
description: Silently batch-download research-paper PDFs by DOI from major publishers using authorized open, institutional, campus, library, or publisher-API access. Verifies the requested main article, rejects supplements, records challenge/auth states, resumes batches, and can hand verified PDFs to the optional paper-pdf-to-markdown skill. Use when the user asks to download, fetch, save, or batch-retrieve paper PDFs or DOI lists.
---

# Paper PDF Download

Use the `paper-pdf` CLI to retrieve papers independently and silently. Do not invoke or require InstSci.

If the console-script directory is not on `PATH`, replace `paper-pdf` in the examples with `python -m paper_pdf`.

## Default workflow

1. Collect DOI values from the request, text file, BibTeX, CSV, Markdown, or prior search result.
2. Run `paper-pdf doctor`. If CloakBrowser is missing, explain the browser-extra installation instead of substituting an unverified generic scraper.
3. Start with the silent resumable route:

   ```bash
   paper-pdf download --file dois.txt --output ./library --workers 1
   ```

4. Treat only `success` and `skipped_existing` as PDF completion. A file named `unverified.pdf` is evidence for review, not success.
5. Report the completion count, status count, and absolute output directory. Name any `challenge_required`, `auth_required`, `blocked`, `session_limit`, or `unverified_pdf` items explicitly.
6. If Markdown was requested, invoke the `paper-pdf-to-markdown` skill only after retrieval has produced verified `paper.pdf` files.

## Silent and interactive modes

- Default mode is headless. It never operates CAPTCHA controls and continues to the next DOI when a challenge persists.
- Add `--interactive` only when the user explicitly permits a visible manual handoff. The user personally completes CAPTCHA, SSO, or OTP; then the persistent publisher profile resumes.
- Do not loop challenges, claim universal bypass, or call an unverified response a PDF.

## Batch and publisher behavior

- The downloader first tries eligible silent HTTP, OA, and configured publisher-API routes, then reuses one persistent CloakBrowser profile per publisher.
- `--workers` controls concurrent publisher sessions. Keep `1` unless the local CloakBrowser license and the institution's policy allow more sessions.
- The downloader isolates publishers so cookies, anti-bot state, and institutional sessions do not leak across unrelated sites.
- Mixed DOI files are accepted directly; the CLI performs publisher grouping.

Read [publisher-support.md](references/publisher-support.md) when diagnosing a site or explaining coverage. Read [configuration.md](references/configuration.md) when institution routing, VPN interaction, Elsevier API, profiles, or private overrides are relevant.

## Verification contract

A `paper.pdf` must:

- contain a structurally parseable PDF;
- match the requested DOI or a high-confidence expected title;
- not be labelled supplementary, supplemental, or supporting material;
- have its SHA-256, size, page count, route, and verification method recorded in `manifest.json`.

Keep the user's authorized-access boundary. Do not request passwords, export cookies, redistribute subscription files, automate human verification, or describe the workflow as paywall breaking.
