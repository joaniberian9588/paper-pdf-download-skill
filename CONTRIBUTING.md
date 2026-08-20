# Contributing

Contributions are welcome, especially reproducible publisher-route fixes, stricter verification tests, and privacy improvements.

## Rules

1. Do not submit copyrighted paper PDFs, cookies, access tokens, institution credentials, or browser profiles.
2. Use synthetic PDFs and offline HTML in tests. Live publisher tests must be opt-in and disabled in CI.
3. Do not describe CAPTCHA solving, paywall breaking, or unauthorized access as a project capability.
4. A new publisher route needs an offline routing test, supplementary-file filter, and explicit status behavior for challenges and authentication.

## Development checks

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests scripts
python -m build
```
