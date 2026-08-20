# Paper PDF Download Skill

[简体中文](README.zh-CN.md)

An independent, silent-first agent skill and Python CLI for retrieving research-paper PDFs that you are authorized to access, verifying that each file is the requested main article, and optionally batch-converting the verified library to Markdown with MinerU.

This project does **not** bundle or invoke InstSci. It is a standalone silent downloader. Its broad publisher catalog, layered result classification, and verification discipline were informed by public academic-retrieval tools including [InstSci](https://github.com/Rimagination/instsci).

## Why this project

- Silent by default: CloakBrowser runs headlessly with one persistent profile per publisher.
- Strict completion: `%PDF-` alone is not success. The CLI parses the PDF, rejects supporting files, and verifies the target DOI or title.
- Broad routing: built-in profiles cover ACS, ACM, APS, Annual Reviews, ASME, Frontiers, Wiley, Elsevier/ScienceDirect, IEEE, IOP, RSC, Springer Nature, World Scientific, AIP, AMS, Copernicus, MDPI, Oxford Academic, PLOS, PNAS, Royal Society, Science, SAGE, Taylor & Francis, Cambridge, and Emerald.
- Resumable batches: every DOI has a manifest; the library root has JSON and CSV aggregate manifests.
- Local-first Markdown: MinerU runs locally by default. Uploading to MinerU Open API requires both `--mode api` and `--allow-upload`.
- Two composable skills: PDF retrieval works without MinerU; conversion can be installed and invoked separately.

## Access and safety boundary

Use this project only for open-access content or content covered by your own campus, library, institution, or publisher-API entitlement. Follow the publisher's terms and do not redistribute subscription PDFs.

The default silent mode never operates CAPTCHAs. Persistent challenges are recorded as `challenge_required`, `auth_required`, or `blocked`, and the batch continues. `--interactive` is an explicit opt-in that opens the persistent browser profile so the user can personally finish CAPTCHA, SSO, or OTP steps.

## Install

Python 3.11 or newer is required.

```bash
git clone https://github.com/wxt18757928900-lgtm/paper-pdf-download-skill.git
cd paper-pdf-download-skill
python -m pip install -e ".[browser]"
cloakbrowser install
```

For an isolated command-line installation after the repository is published:

```bash
pipx install "paper-pdf-download-skill[browser] @ git+https://github.com/wxt18757928900-lgtm/paper-pdf-download-skill.git"
```

Install both agent skills with a compatible Agent Skills installer, or copy the two directories under [`skills/`](skills/) into your agent's skills directory.

```bash
npx skills add wxt18757928900-lgtm/paper-pdf-download-skill
```

MinerU is optional. For private, offline conversion, follow the [official MinerU installation guide](https://github.com/opendatalab/MinerU/blob/master/docs/en/quick_start/index.md); the typical local install is:

```bash
python -m pip install -U "mineru[all]"
```

## Quick start

Check the environment without printing secrets:

```bash
paper-pdf doctor
```

Download one or more papers silently:

```bash
paper-pdf download 10.1038/s41586-020-2649-2 10.1109/5.771073 --output ./library
paper-pdf download --file ./dois.txt --output ./library --workers 1
```

The worker count means concurrent **publisher sessions**, not concurrent tabs in one profile. Keep `--workers 1` unless your CloakBrowser license and institutional access policy allow more sessions.

Allow a visible manual handoff only when desired:

```bash
paper-pdf download --file ./retry.txt --output ./library --interactive
```

Download and then convert every verified PDF in one MinerU batch:

```bash
paper-pdf run --file ./dois.txt --output ./library --mode local --backend pipeline
```

Convert an existing verified library:

```bash
paper-pdf convert ./library --mode local
```

Cloud conversion is never selected automatically:

```bash
paper-pdf convert ./library --mode api --allow-upload
```

## Output contract

```text
library/
├── manifest.json
├── manifest.csv
└── ieee/
    └── 10.1109_5.771073-<hash>/
        ├── paper.pdf
        ├── paper.md                 # only after requested conversion
        ├── assets/mineru/           # images/tables/other MinerU artifacts
        └── manifest.json
```

An unverified candidate is saved as `unverified.pdf` and is never promoted to `paper.pdf`. Conversion failure retains the verified PDF and records a partial outcome.

## Configuration

Copy [`paper-pdf.example.toml`](paper-pdf.example.toml) to a private location and use `paper-pdf --config /path/to/config.toml ...` or set `PAPER_PDF_CONFIG`. API keys are read from environment variables named by the config; their values are never written to manifests.

Institution-specific routes belong in local configuration. The public repository intentionally contains no school name, campus IP, VPN rule, credential, cookie, browser profile, or machine-specific path.

See [publisher support](skills/paper-pdf-download/references/publisher-support.md), [retrieval configuration](skills/paper-pdf-download/references/configuration.md), and [MinerU conversion](skills/paper-pdf-to-markdown/references/mineru.md).

The dated [live validation matrix](docs/validation.md) separates verified downloads from challenge pages, tool-session limits, and profiles not yet live-tested. Offline CI tests do not count as publisher-download successes.

## Development

Live publisher requests are not run in CI. The test suite uses synthetic PDFs and offline HTML fixtures.

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests scripts
python -m build
```

The project is licensed under [MIT](LICENSE). External tools remain governed by their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
