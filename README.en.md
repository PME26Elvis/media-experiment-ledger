# Media Experiment Ledger

[繁體中文](README.md) | **English**

A release-backed experiment platform for structured image and video generation runs. The repository keeps prompt banks, immutable experiment Releases, reproducible analytics, full-corpus repeatability atlases, forecasts, and an Astro/Starlight observatory without committing original result folders to Git history.

## Live repository statistics

<!-- AUTO:LEDGER_STATS_EN:START -->
> Rebuilt from all Releases by GitHub Actions. Only formal `media-exp-*` Releases are counted; `media-input-*` snapshots are excluded.

| Metric | Value |
|---|---:|
| Formal experiment Releases | 9 |
| Experiment date range | 2026-06-29 → 2026-07-13 |
| Total images | 937 |
| Total videos | 40 |
| Latest Prompt Repeatability Atlas | [media-analysis-all-f5fdcae2c78b-v1](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-f5fdcae2c78b-v1) |
<!-- AUTO:LEDGER_STATS_EN:END -->

## Prompt Repeatability Atlas history

<!-- AUTO:ATLAS_HISTORY_EN:START -->
> Every Atlas workflow rescans all Atlas Releases and rebuilds this table without incremental state.

| Published | Atlas type | Data range | Images | Videos | Comparable prompts | Release |
|---|---|---|---:|---:|---:|---|
| 2026-07-20 | Global repeatability atlas | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-f5fdcae2c78b-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-f5fdcae2c78b-v1) |
| 2026-07-19 | Global repeatability atlas | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-8b850904b063-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-8b850904b063-v1) |
| 2026-07-19 | Legacy single-release atlas | 2026-07-13 | 3 | 1 | 3 | [`media-analysis-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-2026-07-13-v1) |
<!-- AUTO:ATLAS_HISTORY_EN:END -->

## Core capabilities

- Accepts one multi-day `results.zip` as the recommended Codespaces input while retaining direct `results/` compatibility.
- Publishes one immutable `media-exp-*` Release per experiment date and supplemental Releases for genuinely new runs on an existing date.
- Stores images and videos in separate ZIP assets, split before GitHub's 2 GiB per-asset boundary.
- Keeps JSONL metadata and SHA-256 manifests available for inexpensive analytics.
- Skips identical published runs and blocks conflicting reuse of a `run_id`.
- Supports byte-verifiable `media-input-*` snapshots for store-now/promote-later uploads.
- Rebuilds one global Prompt Repeatability Atlas from **all published experiment data** after a successful publishing batch.
- Packages image Atlas output in deterministic ZIP bundles containing up to **15 prompt IDs** each.
- Publishes analytics, forecasts, searchable visual comparisons, and architecture documentation through GitHub Pages.

## Supported ingestion paths

All production paths converge on `tools/publish_results.py`, so date splitting, duplicate handling, manifests, and the final Atlas trigger stay consistent.

| Input situation | Command or workflow | Result |
|---|---|---|
| Recommended browser upload | `python tools/publish_from_archive.py results.zip` | Safely extracts one multi-day ZIP and publishes every new date/run. |
| Existing results directory | `python tools/publish_results.py --source results` | Publishes `results/YYYY-MM-DD/run_*` directly. |
| Store first | `python tools/input_snapshot.py publish results.zip` | Creates a byte-exact `media-input-*` snapshot. |
| Promote a snapshot | `python tools/input_snapshot.py promote` or **Promote input snapshot** | Reconstructs and runs the same date publisher. |
| Browser cannot transfer a 2+ GiB ZIP | Split, upload, reconstruct, then use `publish_from_archive.py` | Changes transport only. |

A single archive may contain many dates. The publisher creates all required primary and supplemental `media-exp-*` Releases, then dispatches **one** all-data Atlas only after the entire batch succeeds.

See [ZIP input and snapshot workflow](docs/INPUT_ARCHIVE_WORKFLOW.en.md) and [Codespaces publishing](docs/CODESPACES_PUBLISHING.en.md).

## Fastest publishing path

```bash
python tools/publish_from_archive.py results.zip
```

Accepted layouts include a top-level `results/`, direct `YYYY-MM-DD` directories, or one extra wrapper directory. ZIP64 archives are supported.

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

```bash
python tools/input_snapshot.py publish results.zip
python tools/input_snapshot.py promote --tag latest
```

`media-input-*` Releases are transport/storage records. They are deliberately excluded from README statistics and Atlas source data; only promoted `media-exp-*` Releases count as formal experiments.

## Experiment Release layout

```text
Tag: media-exp-2026-06-29

run_20260629_120000-images.zip
run_20260629_120000-videos.zip
run_20260629_120000-outputs.jsonl
run_20260629_120000-errors.jsonl
manifest-2026-06-29.json
```

A genuinely new run on an existing date creates an immutable supplement such as `media-exp-2026-06-29-s01`.

## Full-corpus Prompt Repeatability Atlas

For each controlled image cohort—same prompt ID, model, and appearance-relevant settings—the Atlas produces:

- a compact primary comparison card;
- an extended overview with up to 16 temporal quantiles;
- full contact-sheet pages containing every verified byte-unique sample;
- JSON sidecars and source indexes;
- deterministic ZIP bundles containing up to **15 prompt IDs**;
- complete multipart ZIP packages below the configured Release-asset boundary.

Companion tags use:

```text
media-analysis-all-<dataset-fingerprint>-vN
```

Release notes embed a small category-diverse preview set. All Release assets remain ZIP containers; inline preview images are served from versioned repository paths.

See [image Atlas specification](docs/PROMPT_REPEATABILITY_ATLAS.md) and the planned [video Prompt Repeatability Atlas](docs/VIDEO_REPEATABILITY_ATLAS.md).

## README automation

Every successful Atlas workflow:

1. rescans all formal `media-exp-*` Releases;
2. aggregates image/video counts from manifests while excluding `media-input-*` snapshots;
3. rescans every published `media-analysis-*` Release;
4. rebuilds the statistics and Atlas-history blocks in both READMEs;
5. commits the updated README, Visual Lab index, and versioned Notes previews together.

No incremental README state or cache is used.

## Analytics, forecasts, and Pages

```text
Multi-day input batch
  → immutable date-scoped experiment Releases
  → one full-corpus Prompt Repeatability Atlas
  → canonical analytics and reports
  → ensemble forecasts
  → Astro/Starlight build
  → GitHub Pages deployment
```

The site includes Overview, Analytics, Visual Lab, Forecast Lab, System Atlas, and Frontend Stack sections.

## Documentation

- [ZIP input and snapshot workflow — English](docs/INPUT_ARCHIVE_WORKFLOW.en.md)
- [Codespaces publishing — English](docs/CODESPACES_PUBLISHING.en.md)
- [Image Prompt Repeatability Atlas](docs/PROMPT_REPEATABILITY_ATLAS.md)
- [Video Prompt Repeatability Atlas plan](docs/VIDEO_REPEATABILITY_ATLAS.md)
- [繁體中文 README](README.md)

## Development

```bash
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt
python -m compileall tools tests
python -m unittest discover -s tests -v
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```
