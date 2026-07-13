# Media Experiment Ledger

A release-backed ledger for structured media-generation runs. The repository keeps source code, prompt banks, immutable release metadata, generated analytics, and a static dashboard in one place without committing large result folders to Git history.

## What this repository does

- Packages `results/YYYY-MM-DD/run_*` directories from a temporary Codespaces workspace.
- Publishes one immutable GitHub Release per experiment date.
- Stores images and videos in separate ZIP assets, split automatically before the 2 GiB asset boundary.
- Keeps `outputs.jsonl` and `errors.jsonl` inside every media ZIP part and also publishes them as standalone assets, alongside a SHA-256 manifest.
- Skips runs that were already published with identical content.
- Builds daily, monthly, per-run, category, latency, and error analytics.
- Commits Markdown, CSV, JSON, SVG, and PNG reports to `analytics/`.
- Publishes an interactive static dashboard through GitHub Pages.

## Fastest publishing path

1. Open this repository in GitHub Codespaces.
2. Drag the complete local `results/` folder into the repository workspace.
3. In the Codespaces terminal, run:

```bash
python tools/publish_results.py --source results
```

The command scans every date folder, packages only runs not already present in Releases, creates date-scoped Releases, verifies each ZIP, and removes temporary ZIP files after successful publication. The uploaded `results/` folder remains in the Codespace until the Codespace is deleted.

For a packaging-only check:

```bash
python tools/publish_results.py --source results --dry-run
```

For one date only:

```bash
python tools/publish_results.py --source results --date 2026-06-29
```

See [Codespaces publishing](docs/CODESPACES_PUBLISHING.md) for the full operational flow.

## Release layout

A primary release uses:

```text
Tag:   media-exp-2026-06-29
Title: Media Experiment — 2026-06-29
```

Assets are structured as:

```text
run_20260629_120000-images.zip
run_20260629_120000-videos.zip
run_20260629_120000-outputs.jsonl
run_20260629_120000-errors.jsonl
manifest-2026-06-29.json
```

If a date was already published and genuinely receives a new run later, the tool creates a supplement such as `media-exp-2026-06-29-s01`. Existing releases are not overwritten.

## Analytics

Every published experiment release triggers `.github/workflows/analytics.yml`. Normal analysis downloads only manifests and JSONL metadata. A manual workflow run can:

- process only unseen releases;
- process the latest N releases;
- process a date range;
- process one exact tag;
- rebuild all reports;
- optionally download and verify media ZIP files.

Generated outputs appear under:

```text
analytics/
  overview.md
  daily/
  monthly/
  runs/
  errors/
  data/
  charts/
site/
```

The dashboard is deployed from `site/` with GitHub Pages. See [Analytics and Pages](docs/ANALYTICS_AND_PAGES.md).

## Existing runner

The existing generation runner and prompt banks remain available in this repository. Its execution behavior is unchanged by the ledger tooling. Large local outputs, logs, state, secrets, and release staging directories are excluded by `.gitignore`.

## Development

```bash
python -m pip install -r requirements-analytics.txt
python -m compileall tools tests
python -m unittest discover -s tests -v
```
