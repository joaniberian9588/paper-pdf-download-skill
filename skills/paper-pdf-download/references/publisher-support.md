# Publisher support

The catalog is a routing and detection checklist, not a universal success guarantee. Publisher pages and access policies change; a route is complete only when the saved file passes main-article verification.

| Profile | DOI/domain signal | Preferred silent candidates |
|---|---|---|
| ACS | `10.1021`, `pubs.acs.org` | `/doi/pdf/`, `/doi/epdf/` |
| ACM | `10.1145`, `dl.acm.org` | `/doi/pdf/<doi>` |
| APS | `10.1103`, `journals.aps.org` | `link.aps.org/pdf/`, abstract-to-PDF path |
| Annual Reviews | `10.1146` | `/doi/pdf/` |
| ASME | `10.1115` | landing metadata and article-owned links |
| Frontiers | `10.3389` | article `/pdf` routes |
| Wiley | `10.1002`, `10.1111` | `pdfdirect`, `pdf`, then `epdf` |
| Elsevier | `10.1016`, ScienceDirect | configured API, PII `/pdfft`, metadata links |
| IEEE | `10.1109` | document number to `stampPDF/getPDF.jsp` |
| IOP | `10.1088` | article `/pdf` |
| RSC | `10.1039` | article landing to `articlepdf` |
| Springer Nature | `10.1007`, `10.1038` | Springer encoded DOI PDF; Nature article `.pdf` |
| World Scientific | `10.1142` | `/doi/pdf/` |
| AIP | `10.1063` | `epdf`, then `pdf` |
| AMS | `10.1175` | `epdf`, `pdf`, XML-to-download path |
| Copernicus | `10.5194` | DOI-derived journal article PDF |
| MDPI | `10.3390` | resolved landing `/pdf` and metadata |
| Oxford Academic | `10.1093` | `/doi/pdf/`, `/doi/epdf/`, article metadata |
| PLOS | `10.1371` | printable article file |
| PNAS | `10.1073` | `epdf`, then download PDF |
| Royal Society | `10.1098` | `/doi/pdf/` |
| Science | `10.1126` | `epdf`, then download PDF |
| SAGE | `10.1177` | `/doi/pdf/` |
| Taylor & Francis | `10.1080` | `/doi/pdf/?download=true` |
| Cambridge | `10.1017` | landing metadata and article-owned links |
| Emerald | `10.1108` | landing metadata and article-owned links |

## Candidate filters

- Reject URL markers such as `supplement`, `supporting-information`, `suppl_file`, and Elsevier `-mmcN` assets.
- If a candidate URL embeds a DOI, that DOI must equal the requested DOI.
- For ScienceDirect signed assets, match the candidate PII to the landing-page PII.
- Extract `citation_pdf_url`, PDF anchors, PDF embeds, viewer `defaultUrl`, and nested `file=`/`pdf=` query parameters.

## Page states

- `challenge_required`: Cloudflare Turnstile, hCaptcha, reCAPTCHA, or equivalent human-verification page remains.
- `auth_required`: the page resolved to SSO, OpenAthens, Shibboleth, EZproxy, or a login route.
- `blocked`: access-denied, unusual-traffic, incident-ID, or automated-access prohibition response.
- `session_limit`: the local CloakBrowser plan has no free browser seat; retry only after the existing session closes.
- `not_found`: article/DOI not found.
- `unverified_pdf`: bytes parse as a PDF but DOI/title or main-article identity did not pass.

Default silent mode records these states and continues. Only explicit `--interactive` permits a user-operated visible handoff.
