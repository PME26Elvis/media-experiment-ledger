# Prompt Repeatability Atlas

## Purpose

The Prompt Repeatability Atlas turns release-backed image runs into controlled visual comparisons. It answers a narrow question: when the same prompt is sent to the same model with the same appearance-relevant settings on different runs, how much does the generated image change?

The feature creates every eligible comparison card, embeds only a small representative set in a companion Release description, stores the complete atlas as Release assets, and publishes a searchable Visual Lab page on GitHub Pages.

## Source and publication model

- Source releases use `media-exp-*` tags and remain immutable raw experiment records.
- Derived releases use `media-analysis-<date>[-sNN]-vN` tags.
- A new analysis version is selected from existing Release tags; no processing state or cache is required.
- Rebuilding unchanged data creates the next analysis version instead of overwriting a previous report.
- The workflow artifact is retained for 14 days as a fallback even if the final Pages-index push races with another workflow.

## Controlled cohort definition

A cohort is keyed by:

1. `prompt_id`
2. image media type
3. model name
4. normalized appearance-relevant request settings

Prompt text is excluded from the settings fingerprint because `prompt_id` is the canonical identity. Response transport fields such as `response_format` are also excluded because they do not change image appearance. Model, size, and future generation parameters present in the payload remain part of the fingerprint.

Different models or settings never appear in the same controlled repeatability card. They can be analyzed later as model or parameter comparisons, but must not be mislabeled as stochastic run variation.

## Sample validation and deduplication

Metadata is collected first from standalone `run_*-outputs.jsonl` assets. The workflow then downloads only image ZIP assets belonging to releases needed by candidate cohorts.

A metadata row becomes a usable sample only when:

- its event is `image_completed`;
- its `prompt_id` is present;
- an actual image member with the same prompt stem exists under a ZIP `images` path;
- Pillow can decode and verify the image.

Exact duplicate bytes are removed using SHA-256. If a current source image is byte-identical to a historical image, the current sample is retained as the representative. The atlas never duplicates a picture merely to fill an empty grid position. Metadata-only dry-run rows therefore cannot masquerade as real visual samples.

## Dynamic layouts

| Usable unique samples | Primary card | Extended card |
|---:|---|---|
| 0–1 | No card | None |
| 2 | 1 × 2 | None |
| 3 | 2 × 2 with one explicit empty cell | None |
| 4 | 2 × 2 | None |
| 5–7 | 2 × 2 | Up to 4 × 2 temporal sheet |
| 8+ | 2 × 2 | 4 × 2, capped at eight temporal samples |

Images use `contain` rather than `cover`: the full generated frame is preserved and neutral padding is preferable to hiding artifacts through cropping.

## Deterministic selection

### Primary card

For four or more usable samples, the primary card contains:

1. earliest usable sample;
2. temporal middle of history;
3. latest prior historical sample;
4. latest sample from the source Release.

With two or three samples the layout contracts dynamically. All selection is deterministic, so rerunning unchanged data produces the same card contents.

### Extended card

When five or more unique samples exist, the extended card selects up to eight evenly spaced temporal quantiles. Extended cards and all JSON sidecars are included in the complete ZIP.

### Release-description highlights

The workflow renders every eligible prompt. Release notes embed four highlights by default. Selection first maximizes category diversity, then fills remaining slots by sample depth and stable prompt ordering. The complete package remains available regardless of what is embedded.

## Rendering specification

- Primary grid: two columns, up to two rows.
- Extended grid: up to four columns and two rows.
- Cell size: 960 px.
- Outer margin: 48 px.
- Gutter: 24 px.
- Header: prompt ID, category, model, cohort fingerprint, and up to three prompt lines.
- Tile footer: historical/current role, experiment date, run ID, source dimensions, and seed availability.
- Output: progressive optimized JPEG at quality 90.
- Font: free Noto Sans CJK installed during the workflow; DejaVu/Pillow fallback keeps local tests portable.

## Release assets

Each companion analysis Release contains:

- every primary comparison JPEG as an individually addressable asset;
- `atlas-report.json` with all cohorts and selected samples;
- `index.html` for an offline gallery after extraction;
- `prompt-repeatability-atlas.zip` containing primary cards, extended cards, all sidecars, report, and gallery;
- Release notes with four embedded primary cards and links to the complete package.

Uploading every primary JPEG separately allows both GitHub Release Markdown and the Pages Visual Lab to display images directly. Extended sheets and sidecars stay in the ZIP to avoid approaching GitHub's per-Release asset-count limit as the prompt bank grows.

## Workflow reliability and timeout strategy

The job has a 90-minute hard timeout and performs no long polling or sleep loops. It has discrete observable stages: metadata collection, selective ZIP download, verification and extraction, rendering, draft Release creation, asset upload, Release publication, and Pages-index publication.

The analysis Release is created as a draft, assets are uploaded, their final browser URLs are queried, and only then are notes finalized and the Release published. This avoids broken image URLs.

The final `web/public/data/visual-analysis.json` push may race with the existing analytics workflow. The workflow handles this with up to three immediate fetch/rebase/push attempts rather than sleeping. The complete output also exists in both the analysis Release and a short-lived Actions artifact, so an index-push race cannot destroy the generated atlas.

## Manual execution

From the Actions tab, run **Publish Prompt Repeatability Atlas** with an exact `media-exp-*` tag or `latest`.

Codespaces equivalent:

```bash
python -m pip install -r requirements-visual-analysis.txt
python tools/build_prompt_atlas.py \
  --source-tag latest \
  --repo PME26Elvis/media-experiment-ledger \
  --publish
```

`gh auth status` must succeed and the token needs `contents: write` permission.

## Files

- `.github/workflows/visual-analysis.yml` — orchestration, publication, fallback artifact, and conflict-safe index push.
- `tools/prompt_atlas_core.py` — cohort identity, dynamic selection, deduplication, and rendering.
- `tools/prompt_atlas_github.py` — Release metadata/media access and companion Release publication.
- `tools/build_prompt_atlas.py` — complete build, package, report, and Pages-index command.
- `visual-analysis/config.json` — small stable policy surface.
- `tests/test_prompt_atlas.py` — cohort, selection, deduplication, layout, versioning, and rendering tests.
- `web/src/content/docs/visual-lab.mdx` and `web/src/components/VisualAtlas.astro` — searchable Pages experience.
