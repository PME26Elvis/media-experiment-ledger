# Codespaces publishing

## One-time preparation

Open the repository page and select **Code → Codespaces → Create codespace on main**. Codespaces already includes Python, Git, and GitHub CLI authentication for the current repository.

The repository ignores `results/`, `.release-staging/`, logs, state, and environment files, so uploading a local result tree does not add it to Git history.

## Routine operation

### 1. Upload the local folder

Drag the complete local `results/` directory into the Codespaces Explorer at the repository root. The expected structure is:

```text
results/
  2026-06-29/
    run_20260629_120000/
      outputs.jsonl
      errors.jsonl
      media/
        images/
        videos/
  2026-06-30/
    run_20260630_090000/
      ...
```

It is safe to upload dates that were already published. The publisher compares every `run_id` and SHA-256 content digest against remote manifests.

### 2. Optional validation pass

```bash
python tools/publish_results.py --source results --dry-run
```

This validates JSONL, scans metadata for obvious secret patterns, hashes source files, builds ZIP packages, and tests ZIP integrity without creating releases.

### 3. Publish every new run

```bash
python tools/publish_results.py --source results
```

The publisher:

1. scans each `YYYY-MM-DD` directory;
2. loads all existing primary and supplemental manifests for that date;
3. skips identical `run_id` plus digest pairs;
4. blocks only a conflicting `run_id` whose content changed;
5. packages images and videos separately with ZIP store mode;
6. splits a media group near 1.8 GiB;
7. includes the run JSONL files in every media ZIP part and also uploads JSONL and manifest assets separately;
8. creates an immutable date release;
9. verifies command completion;
10. removes `.release-staging/` after a fully successful batch.

The original `results/` directory remains in the Codespace.

### 4. Review the result

Open **Releases** and confirm the new date tags. Publishing a release automatically starts the analytics workflow.

### 5. Delete the Codespace when finished

The Codespace is only a temporary staging environment. Deleting it removes the uploaded local result tree and any temporary workspace content without touching release assets.

## Useful options

Publish selected dates:

```bash
python tools/publish_results.py --source results \
  --date 2026-06-29 \
  --date 2026-06-30
```

Retain temporary packages for inspection:

```bash
python tools/publish_results.py --source results --keep-staging
```

Use a lower part boundary:

```bash
python tools/publish_results.py --source results --max-part-gib 1.5
```

## Duplicate and conflict behavior

| Local state | Remote state | Result |
|---|---|---|
| New `run_id` | Missing | Publish |
| Same `run_id` and same digest | Present | Skip |
| Same `run_id` and different digest | Present | Stop that date and report conflict |
| New run on an already published date | Primary release exists | Create supplement `-sNN` |

A failure on one date does not prevent other dates in the same uploaded folder from being evaluated.
