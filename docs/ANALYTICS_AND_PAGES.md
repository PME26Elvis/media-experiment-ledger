# Analytics and GitHub Pages

## Automatic flow

Publishing a tag matching `media-exp-YYYY-MM-DD` or `media-exp-YYYY-MM-DD-sNN` triggers the analytics workflow. The workflow downloads only:

- `manifest-*.json`;
- `run_*-outputs.jsonl`;
- `run_*-errors.jsonl`.

It then updates canonical JSON and CSV data, regenerates Markdown reports and charts, commits the generated files to `main`, and deploys `site/` to GitHub Pages.

## One-time Pages setting

Open **Settings → Pages** and set **Source** to **GitHub Actions**. No custom domain is required.

## Manual analytics modes

Open **Actions → Build analytics and dashboard → Run workflow**.

### `new_only`

Processes release tags not present in `analytics/state/processed-releases.json`.

### `latest_n`

Processes the latest N experiment releases and merges them into the canonical dataset.

### `date_range`

Processes releases whose Taipei experiment date falls within the inclusive input range.

### `exact_tag`

Processes one tag, including supplemental tags.

### `rebuild_all`

Clears generated analytics data and reconstructs the complete dataset from every experiment release manifest.

## Deep media verification

Set `verify_media` to `true` only for a targeted or deliberate verification run. This downloads release ZIP assets and runs `ZipFile.testzip()` against each archive. Normal analysis avoids downloading media.

## Generated data

- `analytics/data/runs.json` and `runs.csv`: one normalized record per run.
- `analytics/data/daily.*`: daily aggregates.
- `analytics/data/monthly.*`: monthly aggregates.
- `analytics/data/errors.*`: normalized error records.
- `analytics/data/categories.json`: completed-output category totals.
- `analytics/charts/`: SVG and PNG plots.
- `analytics/daily/`, `monthly/`, `runs/`, `errors/`: readable Markdown reports.
- `site/data.json`: dashboard dataset.
- `site/index.html`: dependency-free interactive dashboard.
