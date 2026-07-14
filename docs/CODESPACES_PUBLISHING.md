# Codespaces publishing

## One-time preparation

Open the repository page and select **Code → Codespaces → Create codespace on main**. Codespaces includes Python, Git, and GitHub CLI authentication for the current repository.

The repository ignores `results/`, `results*.zip`, extraction directories, release staging, logs, state, and environment files, so the uploaded inputs do not enter Git history.

## Recommended routine operation

### 1. Upload one archive

Create `results.zip` locally and upload that single file to the Codespaces Explorer. This avoids the browser's less reliable large-directory upload path. Supported archive layouts are documented in [ZIP input and snapshot workflow](INPUT_ARCHIVE_WORKFLOW.md).

If the Codespace was opened before the latest repository changes, run:

```bash
git pull --ff-only
```

The ignored `results.zip` does not block this update.

### 2. Publish every new run

```bash
python tools/publish_from_archive.py results.zip
```

The wrapper validates the ZIP, extracts it temporarily, detects the results root, and invokes the existing publisher. The publisher then:

1. scans each `YYYY-MM-DD` directory;
2. loads all existing primary and supplemental manifests for that date;
3. skips identical `run_id` plus digest pairs;
4. blocks only a conflicting `run_id` whose content changed;
5. packages images and videos separately with ZIP store mode;
6. splits a media group near 1.8 GiB;
7. includes the run JSONL files in every media ZIP part and also uploads JSONL and manifest assets separately;
8. creates an immutable date release;
9. verifies command completion;
10. removes temporary extraction and package files after a successful batch.

The original `results.zip` remains in the Codespace.

### 3. Review the result

Open **Releases** and confirm the new date tags. Manually created experiment Releases start the analytics workflow automatically.

### 4. Delete the Codespace when finished

Deleting the Codespace removes the uploaded input and temporary workspace without touching Release assets.

## Immediate storage fallback

When a single large ZIP has finished uploading but you prefer to store it before running the full date pipeline:

```bash
python tools/input_snapshot.py publish results.zip
```

The file is split below the Release asset boundary and uploaded with a SHA-256 manifest. Promote it later through **Actions → Promote input snapshot**, or from a Codespace with:

```bash
python tools/input_snapshot.py promote --tag media-input-YYYY-MM-DD-SHA12
```

## Direct folder compatibility

A complete folder already available through terminal transfer or another method can still be used:

```bash
python tools/publish_results.py --source results
```

It is safe to include dates that were already published. The publisher compares every `run_id` and SHA-256 content digest against remote manifests.

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

Keep extracted files for inspection:

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

Use a lower final media part boundary:

```bash
python tools/publish_from_archive.py results.zip --max-part-gib 1.5
```

## Duplicate and conflict behavior

| Local state | Remote state | Result |
|---|---|---|
| New `run_id` | Missing | Publish |
| Same `run_id` and same digest | Present | Skip |
| Same `run_id` and different digest | Present | Stop that date and report conflict |
| New run on an already published date | Primary release exists | Create supplement `-sNN` |

A failure on one date does not prevent other dates in the same input archive from being evaluated.
