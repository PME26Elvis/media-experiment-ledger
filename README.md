# Media Experiment Ledger

A release-backed ledger for structured media-generation runs. The repository keeps source code, prompt banks, immutable release metadata, generated analytics, and a static dashboard in one place without committing large result folders to Git history.

## What this repository does

- Accepts one uploaded `results.zip` as the primary Codespaces input while retaining direct `results/` compatibility.
- Publishes one immutable GitHub Release per experiment date.
- Stores images and videos in separate ZIP assets, split automatically before the 2 GiB asset boundary.
- Keeps `outputs.jsonl` and `errors.jsonl` inside every media ZIP part and also publishes them as standalone assets, alongside a SHA-256 manifest.
- Skips runs that were already published with identical content.
- Can store a large input archive immediately as split, byte-verifiable snapshot assets and promote it later.
- Builds daily, monthly, per-run, category, latency, and error analytics.
- Commits Markdown, CSV, JSON, SVG, and PNG reports to `analytics/`.
- Publishes an interactive static dashboard through GitHub Pages.

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

An exact tag remains supported through `--tag`, but example SHA text in documentation is not a literal tag. The resolver validates the requested tag and lists available snapshots when it cannot choose safely.

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

## Analytics

Every manually published experiment release triggers `.github/workflows/analytics.yml`. The snapshot-promotion workflow explicitly dispatches analytics after it creates final Releases. Normal analysis downloads only manifests and JSONL metadata. A manual workflow run can:

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

The existing generation runner and prompt banks remain available in this repository. Its execution behavior is unchanged by the ledger tooling. Large local outputs, input archives, logs, state, secrets, extraction directories, and release staging directories are excluded by `.gitignore`.

## Development

```bash
python -m pip install -r requirements-analytics.txt
python -m compileall tools tests
python -m unittest discover -s tests -v
```
