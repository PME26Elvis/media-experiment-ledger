# Prompt Repeatability Atlas

## Purpose

The production Prompt Repeatability Atlas turns the complete release-backed media ledger into controlled image and video comparisons. Both renderers share the same corpus, fingerprint, workflow, report, companion Release, README refresh, and Visual Lab index.

The Atlas is a **global snapshot**. It scans every currently published `media-exp-*` Release, not only the Release that triggered the workflow.

Detailed video behavior is documented in [VIDEO_REPEATABILITY_ATLAS.md](VIDEO_REPEATABILITY_ATLAS.md).

## Batch boundary and triggers

All supported input paths eventually call `tools/publish_results.py`:

1. upload one multi-day `results.zip` and run `tools/publish_from_archive.py`;
2. publish a complete local `results/` directory directly;
3. store a large `media-input-*` snapshot and promote it later from Codespaces;
4. promote that snapshot through **Actions → Promote input snapshot**;
5. reconstruct a browser-uploaded split ZIP and use the normal archive publisher.

One invocation may create many date-scoped primary or supplemental Releases. After all dates have been evaluated, the publisher dispatches **one** Atlas workflow only when the whole batch succeeds and at least one formal experiment Release was added.

The workflow also supports manual execution and forced rebuilds after implementation or policy changes. Individual Release events are not the authoritative batch boundary.

## Full-corpus identity

The dataset fingerprint contains:

- every published `media-exp-*` tag;
- each Release publication timestamp;
- the complete `visual-analysis/config.json` policy;
- the Atlas dataset schema version.

No local processing state or cache is used. Repeated dispatches over the same immutable corpus and policy may reuse an existing fingerprint Release; a forced code/configuration rebuild creates the next `-vN` version.

```text
media-analysis-all-<12-character-dataset-fingerprint>-vN
```

Raw experiment Releases and `media-input-*` snapshots remain immutable. Snapshots do not enter the Atlas until promotion creates formal `media-exp-*` Releases.

## Shared media rules

Image and video cohorts never mix. Every entry has an explicit `media_type`.

For both media types:

- `prompt_id` is canonical prompt identity;
- model and generation settings remain part of the cohort key;
- transport-only fields are excluded;
- metadata alone is insufficient: the actual ZIP member must be found and decoded;
- exact byte duplicates are removed with SHA-256;
- at least two verified unique samples are required;
- primary selections use temporal anchors and always include the latest sample;
- all verified unique samples remain represented in full evidence pages and sidecars;
- raw media is not copied into the companion Release.

## Controlled image cohorts

An image cohort is keyed by:

1. `media_type = image`;
2. `prompt_id`;
3. model;
4. normalized appearance-relevant settings.

Prompt text is excluded because `prompt_id` is canonical. Transport fields such as `response_format` are excluded. Dimensions, quality, sampler, guidance, negative prompt, model revision, input/reference hashes, and future appearance-relevant fields remain when present.

### Image validation

A row becomes usable only when:

- event is `image_completed`;
- `prompt_id` exists;
- an image member with the same prompt stem exists under a ZIP `images` path;
- Pillow can decode and verify it.

### Image outputs

| Unique samples | Primary layout |
|---:|---|
| 0–1 | no entry |
| 2 | `1 × 2` |
| 3 | `2 × 2` with one explicit empty cell |
| 4+ | deterministic `2 × 2` |

When at least five samples exist, an extended sheet contains up to 16 temporal quantiles. Full contact sheets contain every verified byte-unique image in chronological order, paginated at 16 per page.

Rendering uses contain rather than cover, 960 px primary cells, 640 px extended/full cells, progressive JPEG quality 90, and Noto Sans CJK with portable fallbacks.

## Controlled video cohorts

A video cohort is keyed by:

1. `media_type = video`;
2. `prompt_id`;
3. model;
4. normalized non-random generation settings such as frame count, requested frame rate, dimensions, negative prompt, motion/camera/quality controls, model revision, and conditioning media hashes.

### Seed policy

The harvester intentionally generates a new random seed for each video run. Seed is preserved in each sample sidecar as evidence, but excluded from cohort identity. Including seed would turn every real run into a singleton and prevent repeatability analysis.

### Video validation

A row becomes usable only when:

- event is `video_completed`;
- `prompt_id` exists;
- a matching member exists under a ZIP `videos` path;
- `ffprobe` finds a video stream and valid duration/dimensions;
- FFmpeg decodes frames near the start, midpoint, and end;
- SHA-256 completes successfully.

Supported containers include MP4, MOV, M4V, WebM, MKV, and AVI.

### Video outputs

Primary GIF layouts follow the same 2/3/4-sample policy as images. Every tile begins at `t=0`; long clips are trimmed to the configured preview duration, short clips freeze on their final frame, and contain/letterbox is used without cropping.

Defaults:

- 6 seconds;
- 6 FPS;
- 128 colors;
- `480 × 270` per primary tile;
- infinite GIF loop.

Cohorts with at least five samples receive an extended GIF with up to eight temporal quantiles. Full keyframe pages include every verified unique video, with frames at 10%, 50%, and 90%, paginated at 16 videos per page.

## ZIP-only Release assets

The companion Release uploads **only `.zip` assets**. No JPEG, GIF, JSON, MP4, or HTML file appears naked in the asset list.

### Image bundles

Prompt IDs are sorted deterministically. Up to 15 distinct image prompt IDs are placed in each bundle, and every cohort for one prompt stays together.

```text
prompt-atlas-bundle-001-i0001-to-i0015.zip
  primary/*.jpg
  extended/*.jpg
  full/<prompt>-<cohort>/page-*.jpg
  sidecars/*.json
  bundle-manifests/prompt-bundle-001.json
```

### Video bundles

Video prompts use the same 15-prompt policy but remain in separate assets.

```text
video-atlas-bundle-001-v0001-to-v0015.zip
  video/primary/*.gif
  video/extended/*.gif
  video/keyframes/<prompt>-<cohort>/page-*.jpg
  video/sidecars/*.json
  video-bundle-manifests/video-prompt-bundle-001.json
```

### Global packages

- `atlas-metadata.zip` — combined report, image/video sidecars, and bundle manifests.
- `offline-gallery.zip` — offline index plus image JPEG and video GIF primary previews.
- `prompt-repeatability-atlas-complete-partNNN.zip` — ZIP_STORED transport containers holding all image/video bundles and global packages below the configured asset boundary.

## Release-note previews

Release Notes default to:

- four category-diverse image JPEG highlights;
- two category-diverse video GIF highlights.

Versioned previews are committed under:

```text
web/public/data/visual-analysis/previews/<fingerprint>/<batch-id>/<media-type>/
```

Stable raw-repository URLs allow inline previews while Release assets remain ZIP-only. Every preview links to the grouped bundle that contains its prompt.

If no comparable video cohort exists, the image Atlas still publishes normally and no blank video placeholder is added to Notes.

## Visual Lab index

Schema version 3 includes:

- `media_type`;
- `preview_format` (`jpeg` or `gif`);
- image/video comparable cohort totals;
- metadata image/video sample totals;
- preview URL;
- grouped bundle URL;
- full image-page or video-keyframe-page count.

The Visual Lab supports image/video filtering, animated GIF cards, search, category filtering, and direct bundle downloads.

## README statistics and Atlas history

Every successful Atlas workflow runs `tools/update_readme_summary.py` after publication. It:

1. rescans all Releases;
2. counts images and videos only from formal `media-exp-*` manifests;
3. excludes `media-input-*` snapshots;
4. reads every published `media-analysis-*` report;
5. rebuilds the marked blocks in `README.md` and `README.en.md`;
6. commits README files together with the Visual Lab index and JPEG/GIF previews.

Historical totals use the `release_tags` captured in each report, so later experiment data is not added retroactively to older rows.

## Workflow reliability

The production workflow explicitly installs FFmpeg, FFprobe, Pillow, and Noto Sans CJK. The validation workflow also installs FFmpeg and runs real synthetic MP4 regression tests.

There is no repository-specific 90-minute timeout, Actions processing cache, persistent Atlas state, long polling loop, or background daemon.

Observable stages:

1. enumerate all formal experiment Releases;
2. download output metadata;
3. resolve image and video cohorts;
4. download required image/video ZIPs;
5. decode, verify, and deduplicate media;
6. render image cards, video GIFs, and full evidence pages;
7. create image/video grouped bundles and global packages;
8. create or resume a draft companion Release;
9. upload ZIP-only assets;
10. publish Notes with JPEG/GIF previews;
11. verify the published asset set;
12. rebuild bilingual README statistics/history;
13. commit README, Visual Lab index, and versioned previews.

A failure-only Actions artifact is retained for seven days. Successful builds rely on the immutable analysis Release.

## Manual execution

From **Actions → Publish Prompt Repeatability Atlas**, run the workflow with an optional batch label. Enable `force` only when a new version is required for an unchanged corpus fingerprint.

Codespaces equivalent:

```bash
python -m pip install -r requirements-visual-analysis.txt
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk
python tools/build_prompt_atlas.py \
  --scope all \
  --batch-id manual \
  --repo PME26Elvis/media-experiment-ledger \
  --publish
python tools/update_readme_summary.py \
  --repo PME26Elvis/media-experiment-ledger
```

`gh auth status` must succeed. Publishing needs `contents: write`; batch dispatch also needs permission to run Actions workflows.

## Files

- `.github/workflows/visual-analysis.yml` — global image/video orchestration, publication, README refresh, and writeback.
- `.github/workflows/validate.yml` — Python, real FFmpeg, Astro, and route validation.
- `tools/publish_results.py` — authoritative batch-completion dispatch.
- `tools/prompt_atlas_core.py` — image cohort, selection, deduplication, and rendering primitives.
- `tools/prompt_atlas_data.py` — corpus discovery and image extraction.
- `tools/prompt_atlas_video.py` — video metadata, validation, GIF, keyframes, and sidecars.
- `tools/prompt_atlas_build.py` — combined full-corpus build and index.
- `tools/prompt_atlas_packages.py` — image/video bundles and global packages.
- `tools/prompt_atlas_publish.py` — draft recovery, ZIP upload, combined Notes, and verification.
- `tools/update_readme_summary.py` — full Release rescan and bilingual README generation.
- `visual-analysis/config.json` — image/video rendering and packaging policy.
- `tests/test_prompt_atlas.py` and `tests/test_prompt_atlas_video.py` — image and real FFmpeg video regressions.
- `web/src/components/VisualAtlas.astro` — searchable image/video Visual Lab.

## Synchronized project contract

This is a **full-corpus** analysis over non-quarantined formal runs. Release assets remain **ZIP-only**, and image/video outputs remain in deterministic bundles containing up to **15 prompt** IDs. The machine-readable values live in `project-contract.json`; the canonical quarantine is `config/release-quarantine.json`.
