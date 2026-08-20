# MinerU conversion

## Local mode

Install MinerU independently using its official documentation. The current local CLI accepts a file or directory:

```bash
mineru -p <input_path> -o <output_path>
```

The wrapper stages verified PDFs with collision-safe DOI names, calls MinerU once on the directory, reconciles each Markdown result back into its DOI bundle, copies generated resources under `assets/mineru/`, rewrites relative Markdown links, and updates manifests.

CPU-oriented example:

```bash
paper-pdf convert ./library --mode local --backend pipeline
```

Local MinerU can require substantial disk and memory for packages and models. Consult the current upstream requirements before installation; the downloader itself does not bundle those models.

## API mode

`mineru-open-api extract --list ...` is supported as an explicit alternative. It sends PDFs to an external service, so both flags are mandatory:

```bash
paper-pdf convert ./library --mode api --allow-upload
```

Do not infer consent from a general request to convert. Never silently fall back from local mode to API mode.

## Completion checks

- `paper.md` contains at least the configured minimum meaningful characters.
- referenced local resources are copied under `assets/mineru/` and links are rewritten.
- `manifest.json` records mode, status, Markdown path, asset path, text length, and any error.
- `paper.pdf` remains untouched on success or failure.

Raw work is kept after a failed conversion for diagnosis. A fully successful run removes only its own uniquely named directory under `.conversion-work`.
