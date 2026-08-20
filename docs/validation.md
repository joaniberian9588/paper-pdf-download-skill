# Validation status

Last live run: 2026-08-20. This is a dated smoke test, not a permanent availability promise. Publisher pages, institutional entitlements, and anti-bot behavior change independently of this project.

## What was tested

- 27/27 offline tests passed for DOI handling, publisher routing, page-state detection, PDF verification, resumable manifests, session-limit classification, and batch conversion reconciliation.
- 21 representative publisher profiles were exercised against real DOI landing pages.
- A download counts as `success` only when the saved file is structurally parseable, is not a supplement, and matches the requested DOI or a high-confidence title.
- The test used authorized access available to the operator. No credentials, cookies, institution settings, browser profiles, or downloaded PDFs are part of the repository.

## Live publisher matrix

| Profile | Sample DOI | Result | Successful route | Evidence or blocker |
|---|---|---|---|---|
| ACM | `10.1145/3448016.3452834` | success | CloakBrowser | DOI match, 13 pages |
| ACS | `10.1021/acs.est.6c00693` | success | CloakBrowser | DOI match, 22 pages |
| AIP | `10.1063/5.0237567` | challenge required | — | Cloudflare challenge marker |
| AMS | `10.1175/aies-d-23-0093.1` | success | CloakBrowser | DOI match, 19 pages |
| Annual Reviews | `10.1146/annurev-phyto-011325-012824` | inconclusive | — | CloakBrowser plan session limit |
| APS | `10.1103/PhysRevLett.128.161102` | challenge required | — | Cloudflare challenge marker |
| Copernicus | `10.5194/acp-24-1-2024` | success | publisher HTTP | DOI match, 21 pages |
| Elsevier | `10.1016/j.watres.2024.121507` | success | official publisher API | DOI match, 11 pages |
| Frontiers | `10.3389/fmicb.2026.1831710` | success | publisher HTTP | DOI match, 14 pages |
| IEEE | `10.1109/JSTQE.2026.3687110` | success | publisher HTTP | DOI match, 10 pages |
| IOP | `10.1088/1361-648X/ae72dd` | challenge required | — | hCaptcha marker |
| MDPI | `10.3390/foods10081757` | inconclusive | — | CloakBrowser plan session limit |
| Oxford Academic | `10.1093/nar/gkaa892` | challenge required | — | Cloudflare challenge marker |
| PLOS | `10.1371/journal.pone.0000001` | success | CloakBrowser | DOI match, 11 pages |
| PNAS | `10.1073/pnas.2309123120` | inconclusive | — | CloakBrowser plan session limit |
| Royal Society | `10.1098/rsos.150470` | inconclusive | — | CloakBrowser plan session limit |
| RSC | `10.1039/d5cp03829d` | challenge required | — | Cloudflare challenge marker |
| Science | `10.1126/sciadv.adp3964` | inconclusive | — | CloakBrowser plan session limit |
| Springer Nature | `10.1038/s41586-020-2649-2` | success | publisher HTTP | DOI match, 6 pages |
| Wiley | `10.1002/adfm.202525261` | inconclusive | — | CloakBrowser plan session limit |
| World Scientific | `10.1142/S0218194026500348` | challenge required | — | reCAPTCHA marker |

Observed outcome: 9 verified PDF downloads, 6 correctly classified challenge pages, and 6 inconclusive runs caused by the local CloakBrowser plan's session limit. ASME, SAGE, Taylor & Francis, Cambridge, and Emerald profiles were covered by routing/detection tests but were not part of this live matrix.

Challenge classification is a safe stop state, not a claimed CAPTCHA bypass. Interactive mode exists only for an explicit, user-operated handoff.

## MinerU status

The batch wrapper and result reconciliation passed offline tests with a synthetic MinerU-compatible output tree. A live local-model conversion was not claimed in this run because the optional local MinerU runtime and models were not installed. Cloud conversion was not used because it would upload PDFs and requires separate, explicit consent.
