# Prompt Repeatability Atlas

## Purpose

The Prompt Repeatability Atlas turns the complete release-backed media ledger into controlled visual comparisons. The current production renderer handles images; the planned video renderer is specified in [VIDEO_REPEATABILITY_ATLAS.md](VIDEO_REPEATABILITY_ATLAS.md) and will share the same corpus, workflow, report, companion Release, and README refresh.

The production Atlas is a **global snapshot**. It scans every currently published `media-exp-*` Release, not only the Release that happened to trigger the workflow.

## Batch boundary and triggers

All supported input paths eventually call `tools/publish_results.py`:

1. upload one multi-day `results.zip` and run `tools/publish_from_archive.py`;
2. publish a complete local `results/` directory directly;
3. store a large `media-input-*` snapshot and promote it later from Codespaces;
4. promote that snapshot through **Actions → Promote input snapshot**;
5. reconstruct a browser-uploaded split ZIP and use the normal archive publisher.

`publish_results.py` may create many date-scoped primary or supplemental Releases during one invocation. After every date has been evaluated, it dispatches **one** Atlas workflow only when:

- at least one new `media-exp-*` Release was published;
- the whole batch completed without a date failure;
- the operation was not a dry run;
- `--skip-atlas-dispatch` was not explicitly selected.

The Atlas workflow also supports manual execution and rebuilds after Atlas code/configuration changes. Individual Release events are not the authoritative batch boundary.

## Full-corpus identity

The dataset fingerprint contains:

- every published `media-exp-*` tag;
- each Release publication timestamp;
- the complete `visual-analysis/config.json` policy;
- the Atlas dataset schema version.

No local processing state or cache is used. Repeated dispatches over the same immutable corpus and policy reuse the existing published fingerprint Release. A forced code/configuration rebuild creates the next `-vN` version for the same fingerprint.

Global derived tags use:

```text
media-analysis-all-<12-character-dataset-fingerprint>-vN
```

Raw experiment Releases and `media-input-*` snapshots remain immutable. Snapshots are transport/storage records and never enter the Atlas corpus until promotion creates formal `media-exp-*` Releases.

## Controlled image cohort definition

An image cohort is keyed by:

1. `prompt_id`;
2. `media_type = image`;
3. model name;
4. normalized appearance-relevant request settings.

Prompt text is excluded from the settings fingerprint because `prompt_id` is canonical. Transport-only fields such as `response_format` are excluded. Model, dimensions, quality, sampler, guidance, negative prompt, model revision, input/reference hashes, and future appearance-relevant payload fields remain part of the fingerprint when present.

Different models or settings never appear in the same repeatability card.

## Sample validation and deduplication

Metadata is collected first from standalone `run_*-outputs.jsonl` assets. The workflow then downloads the image ZIPs needed by candidate cohorts.

A metadata row becomes usable only when:

- its event is `image_completed`;
- `prompt_id` exists;
- an image member with the same prompt stem exists under a ZIP `images` path;
- Pillow can decode and verify it.

Exact duplicate bytes are removed using SHA-256. Metadata-only test rows and broken media cannot appear as visual evidence. A picture is never duplicated to fill a layout.

## Three image output levels

### 1. Primary card

| Usable unique samples | Primary layout |
|---:|---|
| 0–1 | no card |
| 2 | `1 × 2` |
| 3 | `2 × 2` with one explicit empty cell |
| 4+ | deterministic `2 × 2` |

For four or more samples, the card selects the earliest sample, temporal history anchors, and the latest sample in the cohort.

### 2. Extended temporal overview

When at least five unique samples exist, the prompt receives an extended sheet containing up to **16 temporal quantiles**. The default layout uses at most four columns and four rows.

### 3. Full contact sheets

Every verified byte-unique sample is included in chronological order. Samples are paginated at **16 per page** by default. A prompt with 49 valid results therefore receives four pages: `16 + 16 + 16 + 1`.

## Rendering

- Images use `contain`, never `cover`, so presentation does not hide generated artifacts.
- Primary cell size: 960 px.
- Extended/full-page cell size: 640 px.
- Outer margin: 48 px.
- Gutter: 24 px.
- Header includes prompt ID, category, model, cohort fingerprint, and up to three prompt lines.
- Tile footer includes temporal role, experiment date, run ID, source dimensions, and seed availability.
- Output is progressive optimized JPEG at quality 90.
- The workflow installs Noto Sans CJK with portable fallbacks for local tests.

## ZIP-only Release assets

The companion Release uploads **only `.zip` assets**. No JPG, JSON, GIF, or HTML file appears naked in the Release asset list.

### Grouped prompt packages

Prompt IDs are sorted deterministically. Up to **15 distinct prompt IDs** are placed in each bundle. Every controlled cohort belonging to one prompt stays in the same bundle, so a prompt is never split because it was generated with multiple models or settings.

Example:

```text
prompt-atlas-bundle-001-i0001-to-i0015.zip
  primary/...
  extended/...
  full/i0001-<cohort>/page-001-of-...jpg
  ...
  sidecars/...
  bundle-manifests/prompt-bundle-001.json

prompt-atlas-bundle-002-i0016-to-i0030.zip
  ...
```

The bundle manifest records:

- bundle index;
- prompt count and ordered prompt IDs;
- configured `prompts_per_bundle` policy;
- every cohort, model, sample count, card, sidecar, and full-page path.

The current policy is stored in `visual-analysis/config.json` as:

```json
{
  "prompts_per_bundle": 15
}
```

### Global packages

- `atlas-metadata.zip` — corpus report and all cohort sidecars.
- `offline-gallery.zip` — offline gallery plus primary cards.
- `prompt-repeatability-atlas-complete-partNNN.zip` — ZIP_STORED transport containers holding grouped prompt bundles and global packages, partitioned below the configured 1.75 GiB boundary.

With the present low-volume free-API workload, 15 prompts per asset substantially reduces the Release asset count while remaining far below GitHub's per-asset size limit.

## Release-note previews

Release notes embed a small category-diverse set, four by default. Preview JPEGs are versioned under:

```text
web/public/data/visual-analysis/previews/<fingerprint>/<batch-id>/
```

They use stable raw-repository URLs, allowing inline images while the Release asset list stays ZIP-only. Each preview links to the grouped bundle that contains that prompt.

The Visual Lab indexes every cohort. Only the highlight set has inline preview files; all cohorts expose their containing grouped-bundle URL and full-page count.

## README statistics and Atlas history

Every successful Atlas workflow runs `tools/update_readme_summary.py` after publication. The command:

1. rescans all published Releases;
2. counts images and videos only from formal `media-exp-*` manifests;
3. excludes `media-input-*` snapshots;
4. reads every published `media-analysis-*` report, including legacy single-Release Atlases;
5. rebuilds marked statistics and Atlas-history blocks in `README.md` and `README.en.md`;
6. commits the README files together with the Visual Lab index and versioned previews.

Atlas-history totals use the `release_tags` captured in each report, so later experiment data is not retroactively added to older Atlas rows. No incremental README state or cache is used.

## Planned video integration

Video repeatability will not use a separate workflow or companion Release. It will extend the same pipeline with:

- `video_completed` metadata and selective `run_*-videos*.zip` downloads;
- `ffprobe` validation and actual FFmpeg decoding;
- exact SHA-256 deduplication;
- synchronized tiled GIF previews for Release Notes;
- keyframe contact sheets and video sidecars;
- grouped video ZIP bundles, also up to 15 prompt IDs;
- shared image/video counts in the report, README, and Visual Lab.

The complete validation, GIF, FFmpeg, packaging, and milestone plan is in [VIDEO_REPEATABILITY_ATLAS.md](VIDEO_REPEATABILITY_ATLAS.md).

## Workflow reliability

The repository-specific 90-minute timeout is removed. The workflow still obeys GitHub-hosted runner platform limits but does not terminate a valid full-corpus job at 90 minutes.

No Actions cache, processing-state file, long polling loop, or background daemon is used. Observable stages are:

1. enumerate all experiment Releases;
2. download standalone output metadata;
3. resolve global cohorts;
4. download required media ZIPs;
5. verify and deduplicate media;
6. render primary, extended, and full outputs;
7. create grouped prompt and global ZIP packages;
8. create or resume a draft companion Release;
9. upload ZIP-only assets;
10. publish Notes with inline previews;
11. verify the published asset set;
12. rebuild bilingual README statistics/history;
13. commit README, Visual Lab index, and versioned preview files.

A failure-only Actions artifact is retained for seven days. Successful builds rely on the immutable analysis Release rather than duplicating the entire output as an Actions artifact.

## Manual execution

From **Actions → Publish Prompt Repeatability Atlas**, run the workflow with an optional batch label. Enable `force` only when a new version is required for an unchanged corpus fingerprint.

Codespaces equivalent:

```bash
python -m pip install -r requirements-visual-analysis.txt
python tools/build_prompt_atlas.py \
  --scope all \
  --batch-id manual \
  --repo PME26Elvis/media-experiment-ledger \
  --publish
python tools/update_readme_summary.py \
  --repo PME26Elvis/media-experiment-ledger
```

`gh auth status` must succeed. Publishing needs `contents: write`; dispatching from `publish_results.py` also needs permission to run Actions workflows.

## Files

- `.github/workflows/visual-analysis.yml` — global orchestration, publication, README refresh, and repository writeback.
- `tools/publish_results.py` — authoritative batch-completion dispatch.
- `tools/prompt_atlas_core.py` — cohort identity, selection, deduplication, and image rendering.
- `tools/prompt_atlas_data.py` and `tools/prompt_atlas_publish.py` — corpus collection and ZIP-only publication.
- `tools/prompt_atlas_build.py`, `tools/prompt_atlas_packages.py`, and `tools/build_prompt_atlas.py` — rendering, full pages, grouped packaging, previews, and CLI orchestration.
- `tools/update_readme_summary.py` — full Release rescan and bilingual README block generation.
- `visual-analysis/config.json` — stable rendering and packaging policy.
- `tests/test_prompt_atlas.py`, `tests/test_publish_results.py`, and `tests/test_readme_summary.py` — scope, trigger, packaging, statistics, and rendering regressions.
- `web/src/components/VisualAtlas.astro` — searchable global index and grouped-bundle access.
