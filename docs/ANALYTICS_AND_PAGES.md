# Analytics and GitHub Pages

## Automatic flow

Publishing a tag matching `media-exp-YYYY-MM-DD` or `media-exp-YYYY-MM-DD-sNN` triggers the analytics workflow. The workflow downloads only:

- `manifest-*.json`;
- `run_*-outputs.jsonl`;
- `run_*-errors.jsonl`.

The workflow is deliberately split into three jobs:

1. **build** — regenerates canonical analytics and forecasts, stages all browser JSON, builds Astro, validates every primary route/data artifact, uploads the Pages artifact, and uploads a short-lived analytics writeback artifact;
2. **deploy** — deploys the already-validated `github-pages` artifact and is not blocked by repository writeback races;
3. **writeback** — downloads only `analytics/` and `forecasts/`, commits them to `main`, and uses fetch/rebase/push retries when another bot workflow updates `main` concurrently.

The compiled `site/` directory is an ephemeral runner output and is **not committed to Git**. This avoids duplicating every versioned Atlas GIF/JPEG and YOLO preview under both `web/public/` and `site/`.

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
- `site/`: final Astro output uploaded by `actions/upload-pages-artifact`, then discarded with the runner workspace.

## Deploy reliability contract

- Pages deployment depends only on the successful build artifact, not on a Git push.
- Analytics writeback runs independently after build and cannot block Pages.
- Writeback commits only `analytics/` and `forecasts/`; it never commits `site/`.
- Writeback retries after fetching and rebasing against the latest `main`.
- A writeback failure is visible and actionable, but does not invalidate a successfully deployed, validated Pages artifact.
