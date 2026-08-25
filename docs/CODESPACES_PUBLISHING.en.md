# Codespaces publishing

## One-time preparation

Open the repository page and select **Code → Codespaces → Create codespace on main**. Codespaces includes Python, Git, and GitHub CLI authentication for the repository.

The repository ignores original result trees, uploaded archives, extraction directories, release staging, logs, state, and secrets.

## Recommended operation: one multi-day archive

### 1. Upload

Create `results.zip` locally and upload that single file. It may contain many `YYYY-MM-DD` directories and many runs per date. Supported layouts are documented in [ZIP input and snapshot workflow](INPUT_ARCHIVE_WORKFLOW.en.md).

Update an older Codespace first:

```bash
git pull --ff-only
```

### 2. Publish the complete batch

```bash
python tools/publish_from_archive.py results.zip
```

The shared publisher:

1. scans every date directory;
2. loads primary and supplemental manifests for each date;
3. skips identical `run_id` plus digest pairs;
4. blocks conflicting changed content under the same `run_id`;
5. packages images and videos separately with ZIP store mode;
6. splits media near 1.8 GiB;
7. publishes standalone JSONL/manifest metadata;
8. creates as many immutable date Releases as required;
9. waits until the entire date loop is complete;
10. dispatches one Prompt Repeatability Atlas over **all published experiment data**;
11. removes temporary extraction and package files after a successful batch.

The Atlas therefore aligns with the completed upload package, not with an arbitrary individual date Release created midway through processing.

### 3. Review

Open **Releases** and verify:

- the expected new `media-exp-*` primary/supplemental tags;
- one new or reused `media-analysis-all-<fingerprint>-vN` Atlas;
- a small set of inline Atlas previews in the analysis Notes;
- ZIP-only Atlas assets, including deterministic bundles of up to 15 prompt IDs and complete multipart packages.

For **Actions → Promote input snapshot**, also verify:

- `Audit experiment Releases` refreshed the full integrity report;
- when at least one new `media-exp-*` Release was created, YOLOX-Tiny and NanoDet-Plus ran with one shared `promotion-<run-id>` batch ID;
- Promotion recorded the exact two detector workflow run IDs, waited for both to succeed, and dispatched the comparison publisher with that exact pair;
- the comparison publisher created a new `media-detection-*` Release and refreshed Detector Lab indexes;
- detectors cover the canonical image corpus only; videos remain part of Atlas and general Analytics rather than the YOLOX/NanoDet corpus.

This Action detector path uses explicit A/B/C orchestration rather than chained `workflow_run` pairing. Both full-corpus inference workflows and the comparison publisher are `workflow_dispatch` only, so ordinary main pushes, workflow edits, or documentation changes cannot accidentally start an expensive detector rebuild.

Direct Codespaces use of `publish_from_archive.py`, `publish_results.py`, or CLI promotion still creates formal Releases, triggers release-based Analytics, and dispatches the Atlas. It does not additionally dispatch Audit or Detector workflows; launch those manually from Actions when needed.

If both detector inference runs succeeded but comparison publication was interrupted, manually run **Publish YOLOX + NanoDet comparison** with those existing run IDs while their short-lived artifacts are retained. Do not rerun the complete inference corpus merely to recover publication.

### 4. Cleanup

Delete the Codespace when finished. Releases remain intact.

## Immediate storage fallback

```bash
python tools/input_snapshot.py publish results.zip
python tools/input_snapshot.py promote --tag latest
```

Promotion reconstructs the original archive and calls the same common publisher. `media-input-*` snapshots are excluded from the corpus totals and Atlas source data in [`PROJECT_STATUS.en.md`](PROJECT_STATUS.en.md) until promotion produces formal `media-exp-*` Releases. The Action path also dispatches the full audit and, when the corpus changed, completes the shared-batch YOLOX/NanoDet → exact-run comparison publisher handoff.

## Direct folder compatibility

```bash
python tools/publish_results.py --source results
```

Including already published dates is safe. Remote manifests determine whether each run is new, identical, or conflicting. A successful invocation dispatches one full-corpus Atlas after all date Releases finish.

## Useful archive options

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

Keep extracted files:

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

Use a lower media-part boundary:

```bash
python tools/publish_from_archive.py results.zip --max-part-gib 1.5
```

Skip the automatic Atlas only for exceptional maintenance:

```bash
python tools/publish_results.py \
  --source results \
  --skip-atlas-dispatch
```

## Atlas execution policy

- Primary trigger: one workflow dispatch after a successful common-publisher batch.
- Manual trigger: **Publish Prompt Repeatability Atlas** with optional `force`.
- Code/configuration trigger: Atlas implementation changes on `main` force a new version.
- Scope: all published `media-exp-*` Releases every time.
- Cache/state: none.
- Repository timeout: no 90-minute limit.
- Assets: ZIP-only; image bundles contain up to 15 prompt IDs, and inline Notes previews use versioned repository paths.
- Project status: every successful Atlas run rescans formal experiment and Atlas Releases, then rebuilds the bilingual statistics/history blocks in [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and [`PROJECT_STATUS.en.md`](PROJECT_STATUS.en.md); the root README remains a stable landing page.
