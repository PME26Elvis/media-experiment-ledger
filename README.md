# Media Experiment Ledger

A release-backed experiment platform for structured media-generation runs. The repository keeps source code, prompt banks, immutable Release metadata, reproducible analytics, full-corpus prompt-repeatability atlases, machine-learning forecasts, and a polished GitHub Pages observatory without committing original result folders to Git history.

## What this repository does

- Accepts one uploaded multi-day `results.zip` as the primary Codespaces input while retaining direct `results/` compatibility.
- Publishes one immutable GitHub Release per experiment date and supplemental Releases for genuinely new runs on an existing date.
- Stores images and videos in separate ZIP assets, split automatically before the 2 GiB asset boundary.
- Keeps `outputs.jsonl` and `errors.jsonl` inside every media ZIP part and also publishes them as standalone assets, alongside a SHA-256 manifest.
- Skips runs already published with identical content and blocks conflicting reuse of a `run_id`.
- Can store a large input archive immediately as split, byte-verifiable `media-input-*` snapshot assets and promote it later.
- Builds daily, monthly, per-run, category, latency, error, and integrity analytics.
- Rebuilds one global Prompt Repeatability Atlas from **all currently published experiment data** after a successful publisher batch.
- Runs an ensemble forecasting laboratory for the next active experiment day and next calendar month.
- Publishes an Astro Starlight site with extensible navigation, interactive ECharts, searchable visual comparisons, Mermaid diagrams, responsive layouts, and theme support.

## Supported ingestion paths

All supported publication routes converge on `tools/publish_results.py`, so duplicate handling, date splitting, manifest generation, and the final full-corpus Atlas trigger are consistent.

| Input situation | Command or workflow | Result |
|---|---|---|
| Recommended browser upload | `python tools/publish_from_archive.py results.zip` | Safely extracts one multi-day ZIP and publishes every new date/run. |
| Existing local directory | `python tools/publish_results.py --source results` | Publishes the complete `results/YYYY-MM-DD/run_*` tree directly. |
| Store first, process later | `python tools/input_snapshot.py publish results.zip` | Creates a byte-exact `media-input-*` snapshot. |
| Promote stored snapshot | `python tools/input_snapshot.py promote` or **Promote input snapshot** Action | Reconstructs the archive and uses the same normal date publisher. |
| Browser cannot transfer 2+ GiB ZIP | Split locally, upload parts, reconstruct `results.zip`, then use `publish_from_archive.py` | Changes transport only; final Releases are identical. |

A single archive may contain many dates. The common publisher creates the necessary primary and supplemental `media-exp-*` Releases one by one, then dispatches **one** all-data Atlas only after the entire batch succeeds.

See [ZIP input and snapshot workflow](docs/INPUT_ARCHIVE_WORKFLOW.md) and [Codespaces publishing](docs/CODESPACES_PUBLISHING.md).

## Fastest publishing path

1. Open this repository in GitHub Codespaces.
2. Upload one local `results.zip` file to the workspace.
3. Run:

```bash
python tools/publish_from_archive.py results.zip
```

Accepted archive layouts include:

```text
results.zip
  results/
    2026-06-29/
      run_20260629_120000/...
    2026-06-30/
      run_20260630_120000/...
```

or direct date directories, with one additional wrapper directory tolerated.

Validation only:

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

Selected dates:

```bash
python tools/publish_from_archive.py results.zip \
  --date 2026-06-29 \
  --date 2026-06-30
```

## Store first, process later

When the immediate goal is to secure a completed upload in Release storage:

```bash
python tools/input_snapshot.py publish results.zip
```

This creates a `media-input-...` Release with sub-1.8-GiB byte parts and a SHA-256 manifest. Later, use **Actions → Promote input snapshot** with `latest`, or run:

```bash
python tools/input_snapshot.py promote
```

Input snapshots are neutral storage records. Normal analytics and Atlas generation begin only after promotion creates final `media-exp-*` Releases.

## Experiment Release layout

A primary date Release uses:

```text
Tag:   media-exp-2026-06-29
Title: Media Experiment — 2026-06-29
```

Typical assets:

```text
run_20260629_120000-images.zip
run_20260629_120000-videos.zip
run_20260629_120000-outputs.jsonl
run_20260629_120000-errors.jsonl
manifest-2026-06-29.json
```

If an already published date receives a new run, the tool creates a supplement such as `media-exp-2026-06-29-s01`. Existing Releases are never overwritten.

## Full-corpus Prompt Repeatability Atlas

The Atlas is no longer scoped to whichever individual experiment Release happened to trigger a workflow. After a successful multi-date publishing batch, the common publisher dispatches one rebuild over **every currently published `media-exp-*` Release**.

For each controlled cohort—same prompt ID, model, and appearance-relevant settings—the Atlas produces:

- a compact primary card for notes and quick review;
- an extended overview with up to 16 temporal quantiles;
- paginated full contact sheets containing every verified byte-unique sample;
- JSON sidecars and source indexes;
- one dedicated ZIP per prompt;
- complete Atlas ZIP parts below the configured 1.75 GiB asset boundary.

Companion tags use:

```text
media-analysis-all-<dataset-fingerprint>-vN
```

Release notes contain a small category-diverse preview set. **Every companion Release asset is a ZIP container**; inline preview images are served from versioned repository/Pages paths rather than uploaded as naked JPG assets.

The workflow uses no processing cache or persistent state. The repository-specific 90-minute timeout has been removed. Manual execution remains available for externally created or repaired Releases.

See [Prompt Repeatability Atlas](docs/PROMPT_REPEATABILITY_ATLAS.md).

## Analytics, forecasting, and Pages

Every formal `media-exp-*` Release enters the analytics pipeline. Snapshot promotion explicitly refreshes analytics after creating final Releases. A manual analytics run can process unseen releases, select the latest N, use a date range, ingest an exact tag, rebuild everything, or optionally verify media ZIPs.

```text
Multi-day input batch
  → duplicate-aware date-scoped experiment Releases
  → one full-corpus Prompt Repeatability Atlas
  → canonical analytics and reports
  → ensemble machine-learning forecasts
  → Astro Starlight production build
  → GitHub Pages deployment
```

Generated repository outputs include:

```text
analytics/
forecasts/
visual-analysis/config.json
site/
web/public/data/visual-analysis.json
web/public/data/visual-analysis/previews/
```

The Pages experience contains top-level tabs for:

- **Overview** — portfolio status and navigation.
- **Analytics** — output, quality, category, error, monthly, and run-ledger views.
- **Visual Lab** — searchable global cohort index with prompt-ZIP downloads.
- **Forecast Lab** — next-active-day and next-month probabilistic projections.
- **System Atlas** — tool logic and Mermaid process diagrams.
- **Frontend Stack** — web framework, routing, visualization, build, and deployment architecture.

## Forecasting design

`tools/forecast_experiments.py` trains multiple lightweight CPU models on active experiment dates rather than assuming every calendar day is observed. It forecasts runs, images, videos, errors, success rate, and latency using transformed features, lags, rolling statistics, cyclic calendar features, rolling-origin validation, weighted ensembles, residual bootstrap intervals, and a 10,000-simulation next-month Monte Carlo model.

With a small and irregular dataset, uncertainty bands, backtest error, regime labels, and confidence diagnostics are more informative than a single point estimate.

## Development

Python validation:

```bash
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt
python -m compileall tools tests
python -m unittest discover -s tests -v
```

Web build:

```bash
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```
