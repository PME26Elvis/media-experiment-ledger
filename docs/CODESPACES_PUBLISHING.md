# Codespaces publishing

## One-time preparation

Open the repository page and select **Code → Codespaces → Create codespace on main**. Codespaces includes Python, Git, and GitHub CLI authentication for the repository.

The repository ignores original result trees, uploaded archives, extraction directories, release staging, logs, state, and secrets.

## Recommended operation: one multi-day archive

### 1. Upload

Create `results.zip` locally and upload that single file. It may contain many `YYYY-MM-DD` directories and many runs per date. Supported layouts are documented in [ZIP input and snapshot workflow](INPUT_ARCHIVE_WORKFLOW.md).

Update an older Codespace first:

```bash
git pull --ff-only
```

### 2. Publish the complete batch

```bash
python tools/publish_from_archive.py results.zip
```

The wrapper validates and extracts the archive, then calls the shared publisher. The shared publisher:

1. scans every date directory;
2. loads all primary and supplemental manifests for each date;
3. skips identical `run_id` plus digest pairs;
4. blocks conflicting changed content under the same `run_id`;
5. packages images and videos separately with ZIP store mode;
6. splits media near 1.8 GiB;
7. publishes standalone JSONL/manifest metadata for inexpensive analytics;
8. creates as many immutable date Releases as the archive requires;
9. waits until the entire date loop is complete;
10. dispatches one Prompt Repeatability Atlas over **all published experiment data**;
11. removes temporary extraction and package files after a successful batch.

The Atlas is therefore aligned with the uploaded package, not with an arbitrary individual date Release created midway through processing.

### 3. Review

Open **Releases** and verify:

- the expected new `media-exp-*` primary/supplemental tags;
- one new or reused `media-analysis-all-<fingerprint>-vN` Atlas;
- a small set of inline Atlas previews in the analysis Notes;
- ZIP-only Atlas assets, including one prompt bundle per prompt and complete multipart packages.

### 4. Cleanup

Delete the Codespace when finished. Releases remain intact.

## Immediate storage fallback

Store the uploaded archive before processing:

```bash
python tools/input_snapshot.py publish results.zip
```

Promote later through **Actions → Promote input snapshot**, or from Codespaces:

```bash
python tools/input_snapshot.py promote --tag latest
```

Promotion reconstructs the original archive and calls the same common publisher, so the final full-corpus Atlas behavior is identical.

## Direct folder compatibility

A complete local directory remains supported:

```bash
python tools/publish_results.py --source results
```

Including dates already published is safe. Remote manifests determine whether each run is new, identical, or conflicting. A successful invocation dispatches one full-corpus Atlas after all date Releases are finished.

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

Use a lower final media-part boundary:

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

- Primary trigger: one workflow dispatch at the end of a successful common-publisher batch.
- Manual trigger: **Publish Prompt Repeatability Atlas** with optional `force`.
- Code/configuration trigger: Atlas implementation changes on `main` force a new version.
- Fallback trigger: manual full-corpus run after any externally created or repaired experiment Release.
- Scope: all published `media-exp-*` Releases every time.
- Cache/state: none.
- Repository timeout: no 90-minute limit.
- Assets: ZIP-only; inline Notes previews use versioned repository/Pages paths.
