---
name: paper-pdf-to-markdown
description: Batch-convert locally downloaded and verified research-paper PDFs into Markdown and extracted assets with MinerU, updating each DOI bundle manifest. Local conversion is the privacy-preserving default; MinerU Open API requires explicit upload consent. Use when the user asks to turn downloaded papers, a verified paper library, or paper PDFs into Markdown for reading, RAG, summarization, or analysis.
---

# Paper PDF to Markdown

Convert verified `paper.pdf` bundles produced by `paper-pdf-download`. Preserve the PDF even when conversion fails.

If the console-script directory is not on `PATH`, replace `paper-pdf` in the examples with `python -m paper_pdf`.

## Local-first workflow

1. Run `paper-pdf doctor` and confirm `mineru_command` is available.
2. Use one directory batch so MinerU does not restart its model for every paper:

   ```bash
   paper-pdf convert ./library --mode local --backend pipeline
   ```

3. Confirm each successful bundle contains `paper.md`, any referenced files under `assets/mineru/`, and `conversion.status=success` in `manifest.json`.
4. Report PDF completion and Markdown completion separately. A verified PDF with failed conversion is a partial outcome, not a lost download.

The end-to-end command is:

```bash
paper-pdf run --file dois.txt --output ./library --mode local
```

## Cloud API privacy gate

Never select cloud conversion merely because local MinerU is missing or slow. API mode may upload subscription PDFs to a third party and therefore requires the user's explicit permission plus the command-line gate:

```bash
paper-pdf convert ./library --mode api --allow-upload
```

If consent is absent, stop before upload and offer local MinerU installation instead.

Read [mineru.md](references/mineru.md) for installation, batch reconciliation, output validation, and troubleshooting.
