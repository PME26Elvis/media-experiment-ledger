# Prompt Repeatability Atlas

## Purpose

The Prompt Repeatability Atlas turns the complete release-backed image ledger into controlled visual comparisons. It answers one narrow question: when the same `prompt_id` is sent to the same model with the same appearance-relevant settings across different runs, how much does the result vary?

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

The Atlas workflow also supports manual execution and rebuilds after Atlas code/configuration changes. It no longer uses every individual Release event as the authoritative batch boundary.

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

Raw experiment Releases remain immutable.

## Controlled cohort definition

A cohort is keyed by:

1. `prompt_id`;
2. image media type;
3. model name;
4. normalized appearance-relevant request settings.

Prompt text is excluded from the settings fingerprint because `prompt_id` is the canonical prompt identity. Transport-only fields such as `response_format` are excluded. Model, dimensions, quality, sampler, guidance, negative prompt, model revision, and any future appearance-relevant payload fields remain part of the fingerprint when present.

Different models or settings never appear in the same repeatability card.

## Sample validation and deduplication

Metadata is collected first from standalone `run_*-outputs.jsonl` assets. The workflow then downloads the image ZIPs needed by all candidate cohorts.

A metadata row becomes usable only when:

- its event is `image_completed`;
- `prompt_id` exists;
- an image member with the same prompt stem exists under a ZIP `images` path;
- Pillow can decode and verify it.

Exact duplicate bytes are removed using SHA-256. Metadata-only test rows and broken media therefore cannot appear as visual evidence. A picture is never duplicated to fill a layout.

## Three output levels

### 1. Primary card

The compact card used for Release-note previews:

| Usable unique samples | Primary layout |
|---:|---|
| 0–1 | no card |
| 2 | `1 × 2` |
| 3 | `2 × 2` with one explicit empty cell |
| 4+ | deterministic `2 × 2` |

For four or more samples, the card selects the earliest sample, temporal history anchors, and the latest sample in that cohort.

### 2. Extended temporal overview

When at least five unique samples exist, the prompt receives an extended sheet containing up to **16 temporal quantiles**. The default layout uses at most four columns and four rows.

### 3. Full contact sheets

Every verified byte-unique sample is included in chronological order. Samples are paginated at **16 per page** by default. A prompt with 49 valid results therefore receives four full pages: `16 + 16 + 16 + 1`.

This full level is not a sample. It is the complete usable cohort history.

## Rendering

- Images use `contain`, never `cover`, so generated artifacts are not hidden by cropping.
- Primary cell size: 960 px.
- Extended/full-page cell size: 640 px.
- Outer margin: 48 px.
- Gutter: 24 px.
- Header includes prompt ID, category, model, cohort fingerprint, and up to three prompt lines.
- Tile footer includes temporal role, experiment date, run ID, source dimensions, and seed availability.
- Output is progressive optimized JPEG at quality 90.
- The workflow installs the free Noto Sans CJK font, with portable fallbacks for local tests.

## ZIP-only Release assets

The companion Release uploads **only `.zip` assets**. No JPG, JSON, or HTML file appears naked in the Release asset list.

### Per-prompt package

Each prompt receives one package such as:

```text
prompt-i0001-atlas.zip
  primary/...
  extended/...
  full/i0001-<cohort>/page-001-of-...jpg
  sidecars/...
  bundle-manifests/prompt-i0001.json
```

If one prompt has multiple controlled cohorts, they share the prompt package but remain separated by cohort ID inside it.

### Global packages

- `atlas-metadata.zip` — corpus report and all cohort sidecars.
- `offline-gallery.zip` — offline gallery plus primary cards.
- `prompt-repeatability-atlas-complete-partNNN.zip` — ZIP_STORED bundles of all prompt packages and global packages, partitioned below the configured 1.75 GiB boundary.

The design stays below GitHub's per-asset limit while allowing hundreds of prompt packages. The complete parts are transport containers; prompt ZIPs are the natural unit for selective download.

## Release-note previews

Release notes embed a small category-diverse set, four by default. These preview JPEGs are versioned under:

```text
web/public/data/visual-analysis/previews/<fingerprint>/<batch-id>/
```

They are referenced through stable raw-repository URLs. This permits inline images while keeping the Release asset list ZIP-only. Every preview also links to its prompt ZIP.

The Visual Lab indexes every cohort. Only the Release-note highlights have inline preview images; all cohorts expose their prompt-bundle download URL and full-page count.

## Workflow reliability

The repository-specific 90-minute timeout has been removed. The workflow still obeys GitHub-hosted runner platform limits, but the repository no longer terminates a valid full-corpus job at 90 minutes.

No Actions cache, processing-state file, long polling loop, or background daemon is used. The observable stages are:

1. enumerate all experiment Releases;
2. download all standalone output metadata;
3. resolve global cohorts;
4. download required image ZIPs;
5. verify and deduplicate media;
6. render primary, extended, and all full pages;
7. create per-prompt and global ZIP packages;
8. create/resume a draft companion Release;
9. upload ZIP-only assets;
10. publish notes with inline previews;
11. verify the published asset set;
12. commit the Visual Lab index and versioned preview files.

A failure-only Actions artifact is retained for seven days as a recovery aid. Successful builds rely on the immutable analysis Release rather than duplicating the entire output as an Actions artifact.

## Manual execution

From **Actions → Publish Prompt Repeatability Atlas**, run the workflow with an optional batch label. Enable `force` only when a new version is desired for an unchanged corpus fingerprint.

Codespaces equivalent:

```bash
python -m pip install -r requirements-visual-analysis.txt
python tools/build_prompt_atlas.py \
  --scope all \
  --batch-id manual \
  --repo PME26Elvis/media-experiment-ledger \
  --publish
```

`gh auth status` must succeed. Publishing needs `contents: write`; dispatching from `publish_results.py` also needs permission to run Actions workflows.

## Files

- `.github/workflows/visual-analysis.yml` — global orchestration and index publication.
- `tools/publish_results.py` — authoritative batch-completion dispatch.
- `tools/release_packaging.py` and `tools/release_publishing.py` — raw Release packaging and batch publication.
- `tools/prompt_atlas_core.py` — cohort identity, selection, deduplication, and rendering.
- `tools/prompt_atlas_data.py` and `tools/prompt_atlas_publish.py` — corpus collection and ZIP-only Release publication.
- `tools/prompt_atlas_build.py`, `tools/prompt_atlas_packages.py`, and `tools/build_prompt_atlas.py` — full-corpus rendering, full pages, packaging, previews, and CLI orchestration.
- `visual-analysis/config.json` — stable rendering and packaging policy.
- `tests/test_prompt_atlas.py` and `tests/test_publish_results.py` — global-scope, trigger, packaging, selection, and rendering regressions.
- `web/src/components/VisualAtlas.astro` — searchable global index and prompt-ZIP access.
