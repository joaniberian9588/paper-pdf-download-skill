# Security and privacy

## Report a vulnerability

Open a private GitHub security advisory for vulnerabilities. Do not include live credentials, cookies, publisher tokens, campus IP addresses, or subscription PDFs in public issues.

## Secrets

- Keep Elsevier and other API values in environment variables.
- Keep institution routing in a gitignored local TOML file.
- Never commit browser profiles, cookies, SSO screenshots, conversion work directories, or downloaded papers.
- `paper-pdf doctor` reports only availability booleans; it does not print secret values.

## Human verification

Default mode is headless and does not operate CAPTCHA controls. `--interactive` is an explicit user-controlled handoff for the user to personally complete CAPTCHA, SSO, or OTP in a visible persistent browser.

## Cloud conversion

MinerU Open API mode is guarded by `--allow-upload`. Local MinerU is the default because institutional PDFs may be confidential or licensed.
