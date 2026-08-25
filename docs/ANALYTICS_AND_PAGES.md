# Analytics and GitHub Pages

## Automatic flow

Publishing a tag matching `media-exp-YYYY-MM-DD` or `media-exp-YYYY-MM-DD-sNN` triggers the analytics workflow. The workflow downloads only:

- `manifest-*.json`;
- `run_*-outputs.jsonl`;
- `run_*-errors.jsonl`.

The workflow is deliberately split into three jobs:

1. **build** — regenerates canonical analytics and forecasts, stages all browser JSON, builds Astro, removes repository-backed binary preview mirrors from the ephemeral Pages payload, validates every primary route/data artifact, uploads the Pages artifact, and uploads a short-lived analytics writeback artifact;
2. **deploy** — deploys the already-validated `github-pages` artifact and is not blocked by repository writeback races;
3. **writeback** — downloads only `analytics/` and `forecasts/`, commits them to `main`, and uses fetch/rebase/push retries when another bot workflow updates `main` concurrently.

The compiled `site/` directory is an ephemeral runner output and is **not committed to Git**.

## Repository preview evidence versus Pages payload

Atlas, combined-detector, and legacy YOLO representative previews are versioned repository evidence. Their published JSON and Release Notes URLs deliberately use `raw.githubusercontent.com/.../main/web/public/...`; the live Labs load those exact URLs rather than needing a second binary copy inside GitHub Pages.

Astro naturally copies `web/public/` into `site/`. Without an explicit deployment boundary that would duplicate every historical preview into the Pages artifact, even though those bytes are never needed from the Pages origin. Repeated Atlas builds can also produce byte-identical preview trees under different historical batch paths. The repository keeps those paths intact so historical evidence links remain valid, while `tools/prepare_pages_artifact.py` removes only these **ephemeral Pages mirrors** after Astro build:

- `site/data/visual-analysis/previews/`;
- `site/data/detection/previews/`;
- `site/data/yolo/previews/`.

Tracked files under `web/public/` are never deleted by this preparation step. JSON indexes, UI routes, Release assets, and raw-GitHub preview URLs remain unchanged. `tools/validate_site_build.py` fails if any of these binary mirrors survive into the deployable artifact.

The repository keeps a 1 GB total Pages artifact guard and 100 MB per-file guard. The total guard intentionally tracks the officially supported GitHub Pages artifact size rather than the larger best-effort transport ceiling.

## One-time Pages setting

Open **Settings → Pages** and set **Source** to **GitHub Actions**. No custom domain is required.

## Manual analytics modes

Open **Actions → Build analytics, forecasts, and Pages → Run workflow**.

### `new_only`

Processes release tags not present in `analytics/state/processed-releases.json`.

### `latest_n`

Processes the latest N experiment releases and merges them into the canonical dataset.

### `date_range`

Processes releases whose Taipei experiment date falls within the inclusive input range.

### `exact_tag`

Processes one tag, including supplemental tags.

### `rebuild_all`

Clears generated analytics data and reconstructs the complete dataset from every canonical experiment Release manifest after applying the quarantine policy.

## Deep media verification

Set `verify_media` to `true` only for a targeted or deliberate verification run. This downloads Release ZIP assets and runs `ZipFile.testzip()` against each archive. Normal analysis avoids downloading media.

## Generated data

Tracked canonical data:

- `analytics/data/runs.json` and `runs.csv`: one normalized record per run;
- `analytics/data/daily.*`: daily aggregates;
- `analytics/data/monthly.*`: monthly aggregates;
- `analytics/data/errors.*`: normalized error records;
- `analytics/data/categories.json`: completed-output category totals;
- `analytics/charts/`: SVG and PNG plots;
- `analytics/daily/`, `monthly/`, `runs/`, `errors/`: readable Markdown reports;
- `forecasts/`: forecast JSON, reports, model cards, charts, and compact history.

Ephemeral build inputs/outputs:

- `site/data.json`: temporary dashboard dataset produced before Astro build;
- `web/public/data/analytics.json`: temporary staged browser artifact;
- `web/public/data/forecast.json`: temporary staged browser artifact;
- `site/`: Astro output after repository-backed preview mirrors are pruned, validated, uploaded by `actions/upload-pages-artifact`, and discarded with the runner workspace.

## Deploy reliability contract

- Pages deployment depends only on the successful build artifact, not on a Git push.
- Analytics writeback runs independently after build and cannot block Pages.
- Writeback commits only `analytics/` and `forecasts/`; it never commits `site/`.
- Versioned preview evidence remains tracked under `web/public/` and served through raw GitHub URLs; only the duplicate copies inside the ephemeral Pages payload are excluded.
- PR validation and production deployment both run `tools/prepare_pages_artifact.py` before `tools/validate_site_build.py`, so CI measures the artifact that would actually be uploaded.
- Writeback retries after fetching and rebasing against the latest `main`.
- A writeback failure is visible and actionable, but does not invalidate a successfully deployed, validated Pages artifact.
