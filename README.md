# Media Experiment Ledger

A release-backed experiment platform for structured media-generation runs. The repository keeps source code, prompt banks, immutable Release metadata, reproducible analytics, machine-learning forecasts, and a polished GitHub Pages observatory without committing large result folders to Git history.

## What this repository does

- Accepts one uploaded `results.zip` as the primary Codespaces input while retaining direct `results/` compatibility.
- Publishes one immutable GitHub Release per experiment date.
- Stores images and videos in separate ZIP assets, split automatically before the 2 GiB asset boundary.
- Keeps `outputs.jsonl` and `errors.jsonl` inside every media ZIP part and also publishes them as standalone assets, alongside a SHA-256 manifest.
- Skips runs that were already published with identical content.
- Can store a large input archive immediately as split, byte-verifiable snapshot assets and promote it later.
- Builds daily, monthly, per-run, category, latency, error, and integrity analytics.
- Runs an ensemble forecasting laboratory for the next active experiment day and the next calendar month.
- Publishes an Astro Starlight site with extensible navigation, interactive ECharts, Mermaid system diagrams, search, responsive layouts, and theme support.

## Fastest publishing path

1. Open this repository in GitHub Codespaces.
2. Upload one local `results.zip` file to the repository workspace.
3. In the Codespaces terminal, run:

```bash
python tools/publish_from_archive.py results.zip
```

The archive may contain a top-level `results/`, direct `YYYY-MM-DD` directories, or one additional wrapper directory. The command extracts to a temporary ignored directory, invokes the duplicate-aware date publisher, removes temporary extraction and package files, and leaves the original ZIP untouched.

For a validation-only pass:

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

The previous folder command remains supported:

```bash
python tools/publish_results.py --source results
```

See [ZIP input and snapshot workflow](docs/INPUT_ARCHIVE_WORKFLOW.md) and [Codespaces publishing](docs/CODESPACES_PUBLISHING.md).

## Store first, process later

When the immediate goal is simply to place the completed upload into Release storage:

```bash
python tools/input_snapshot.py publish results.zip
```

This creates a `media-input-...` Release containing sub-1.8-GiB byte parts and a SHA-256 manifest. Later, use the **Promote input snapshot** Actions workflow with its default `latest` value, or run:

```bash
python tools/input_snapshot.py promote
```

An exact tag remains supported through `--tag`. The resolver validates the requested tag and lists available snapshots when it cannot choose safely.

Input snapshots are separate from final experiment Releases and are ignored by normal analytics until promoted.

## Release layout

A primary experiment release uses:

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

## Analytics, forecasting, and Pages

Every formal `media-exp-*` Release enters the analytics pipeline. Snapshot promotion explicitly dispatches the same workflow after creating final Releases. A manual workflow run can process unseen releases, select the latest N, use a date range, ingest one exact tag, rebuild everything, or optionally verify media ZIPs.

The pipeline now performs three stages:

```text
Release metadata
  → canonical analytics and reports
  → ensemble machine-learning forecasts
  → Astro Starlight production build
  → GitHub Pages deployment
```

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
forecasts/
  forecast.json
  report.md
  model-card.md
  history.jsonl
  logs/
site/
  built Astro/Starlight website
```

The Pages experience contains top-level tabs for:

- **Overview** — portfolio status and experiment navigation.
- **Analytics** — interactive output, quality, category, error, monthly, and run-ledger views.
- **Forecast Lab** — next-active-day forecasts, next-month Monte Carlo projections, confidence intervals, regimes, backtests, and ensemble weights.
- **System Atlas** — detailed tool logic and Mermaid process diagrams with zoom, pan, reset, and fullscreen controls.

Adding another primary page requires one navigation registry entry and one MDX page. See [Web experience and forecasts](docs/WEB_EXPERIENCE_AND_FORECASTS.md).

## Forecasting design

`tools/forecast_experiments.py` trains multiple lightweight CPU models on active experiment dates rather than assuming every calendar day is observed. It forecasts runs, images, videos, errors, success rate, and latency using transformed features, lags, rolling statistics, cyclic calendar features, rolling-origin validation, weighted ensembles, residual bootstrap intervals, and a 10,000-simulation next-month Monte Carlo model.

This is deliberately presented as an experimental forecasting laboratory. With a small and irregular dataset, uncertainty bands, backtest error, regime labels, and confidence diagnostics are more informative than a single point estimate.

## Existing runner

The existing generation runner and prompt banks remain available in this repository. Its execution behavior is unchanged by the ledger, forecast, and web tooling. Large local outputs, input archives, logs, state, secrets, extraction directories, and release staging directories are excluded by `.gitignore`.

## Development

Python validation:

```bash
python -m pip install -r requirements-analytics.txt -r requirements-forecast.txt
python -m compileall tools tests
python -m unittest discover -s tests -v
```

Web build:

```bash
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```
