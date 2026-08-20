# Retrieval configuration

Start from the repository's `paper-pdf.example.toml`. Keep the active file outside version control and pass it using `--config` or `PAPER_PDF_CONFIG`.

## Institutional networking

The public project has no school preset. If your subscription depends on a campus IP, confirm the child browser uses the entitled route. A system-wide VPN may change the exit even when its TUN mode is disabled; test routing outside the repository and add only the minimal browser flags to the private config.

Example direct-browser override:

```toml
[browser]
args = ["--no-proxy-server", "--proxy-bypass-list=*"]
```

This is a generic example, not a safe default for every institution. Do not change system proxy or VPN settings from the downloader.

## Publisher profiles

Profiles live under the configured `profile_dir`, one directory per publisher. They can contain cookies, localStorage, IndexedDB, cache, and anti-bot state. Never commit, upload, or share them.

## Elsevier API

The config stores only environment-variable names:

```toml
[apis]
elsevier_api_key_env = "ELSEVIER_API_KEY"
elsevier_inst_token_env = "ELSEVIER_INST_TOKEN"
```

Set the API key in the process environment. Set an institutional token only if your library explicitly issued one. The downloader never writes either value to logs or manifests.

## Optional Unpaywall route

Unpaywall requires an email identifier. Setting `unpaywall_email` enables OA lookup; leaving it empty skips the request.

## Concurrency

`--workers N` opens up to N publisher-isolated browser sessions. A single CloakBrowser seat supports only one session. Same-publisher DOIs are intentionally processed serially in their shared profile.
