# ZIP input and snapshot workflow

The browser-based Codespaces Explorer can be unreliable when a large directory contains many media files. The recommended input is therefore one `results.zip`. Direct `results/` input remains supported, and an input-snapshot route is available when storage should happen before processing.

## One common publishing core

All production paths converge on `tools/publish_results.py`:

```text
multi-day results.zip ─┐
direct results/ ───────┼─→ publish_results.py
media-input promotion ─┘     ├─ one immutable Release per new date
                              ├─ supplements for new runs on old dates
                              └─ one full-corpus Atlas dispatch after batch success
```

The final Atlas dispatch happens once after the whole batch, not once per date Release. It scans all currently published `media-exp-*` data.

## Primary path: upload one ZIP and publish every date

Create a ZIP locally with either layout:

```text
results.zip
  results/
    2026-06-29/
      run_20260629_120000/
        outputs.jsonl
        errors.jsonl
        media/images/...
        media/videos/...
    2026-06-30/
      run_20260630_120000/...
```

or:

```text
results.zip
  2026-06-29/
    run_20260629_120000/...
  2026-06-30/
    run_20260630_120000/...
```

One extra wrapper directory is accepted. ZIP64 archives larger than 2 GiB are supported.

1. Open a Codespace on `main`.
2. Upload `results.zip`.
3. Update tracked code when the Codespace predates the latest repository changes:

```bash
git pull --ff-only
```

4. Publish every new date and run:

```bash
python tools/publish_from_archive.py results.zip
```

The command:

- rejects unsafe or incomplete ZIP members;
- checks whether the upload changes during inspection or extraction;
- estimates required disk space;
- extracts temporarily under `.archive-imports/`;
- accepts a top-level `results/`, direct date directories, or one wrapper;
- invokes the SHA-256 duplicate-aware date publisher;
- creates as many primary/supplemental `media-exp-*` Releases as needed;
- dispatches one all-data Atlas only after all dates succeed;
- removes temporary extraction/package files;
- leaves the original `results.zip` untouched.

Dry run:

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

Selected dates:

```bash
python tools/publish_from_archive.py results.zip \
  --date 2026-06-29 \
  --date 2026-06-30
```

Keep the extracted tree:

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

The internal publisher also supports `--skip-atlas-dispatch` for exceptional maintenance operations, but normal ingestion should leave the automatic full-corpus rebuild enabled.

## Last-resort browser transfer: upload ordinary split files

If one 2+ GiB ZIP cannot be transferred through the browser, split it locally in WSL:

```bash
sha256sum results.zip > results.zip.sha256
split -b 1500M -d -a 3 results.zip results.zip.upload-part-
```

Upload:

```text
results.zip.upload-part-000
results.zip.upload-part-001
results.zip.sha256
```

Reconstruct and verify inside Codespaces:

```bash
cat results.zip.upload-part-* > results.zip
sha256sum -c results.zip.sha256
python tools/publish_from_archive.py results.zip
```

This changes only the browser transport. The reconstructed archive, date Releases, and final Atlas trigger are identical to the primary path.

## Fast storage path: publish an input snapshot first

Use this when the priority is to place a completed upload into Release storage immediately:

```bash
python tools/input_snapshot.py publish results.zip
```

The script verifies the ZIP central directory, splits the file into byte-exact parts below 1.8 GiB, calculates SHA-256 for the source and every part, and creates a neutral Release such as:

```text
Tag: media-input-2026-07-15-<sha12>
Assets:
  results.zip.part001
  results.zip.part002
  input-snapshot-manifest.json
```

The source is not recompressed. Temporary split parts are removed after upload.

Packaging-only test:

```bash
python tools/input_snapshot.py publish results.zip --dry-run
```

## Promote a stored snapshot later

### GitHub Actions

1. Open **Actions**.
2. Select **Promote input snapshot**.
3. Run the workflow.
4. Leave `snapshot_tag` as `latest`, or provide an exact `media-input-*` tag.
5. Leave `dry_run` disabled to create normal experiment Releases.

The workflow downloads and verifies every part, reconstructs the exact ZIP, extracts it safely, and calls the same common publisher. The common publisher dispatches one full-corpus Atlas after the promoted multi-date batch succeeds. The promotion workflow separately refreshes analytics.

### Codespaces

Promote the latest snapshot:

```bash
python tools/input_snapshot.py promote
```

Promote an exact snapshot:

```bash
python tools/input_snapshot.py promote \
  --tag media-input-2026-07-15-<real-sha-prefix>
```

Restore only:

```bash
python tools/input_snapshot.py restore \
  --output restored-results.zip
```

## Direct folder compatibility

When a complete directory is already available through a terminal transfer or a small browser operation:

```bash
python tools/publish_results.py --source results
```

This is a first-class path. It scans every `YYYY-MM-DD` directory, publishes all new runs, and dispatches one all-data Atlas when the batch succeeds.

## Duplicate and conflict behavior

| Local state | Remote state | Result |
|---|---|---|
| New `run_id` | Missing | Publish in the date Release batch. |
| Same `run_id`, same digest | Present | Skip safely. |
| Same `run_id`, different digest | Present | Fail that date and do not dispatch the final Atlas. |
| New run on a published date | Primary exists | Create `-sNN` supplement. |

A failure on one date does not prevent other dates from being evaluated, but the one final Atlas dispatch waits for a failure-free batch so it never claims that a partial upload is the completed corpus update.

## Cleanup

Ignored paths include:

```text
results/
results*.zip
results.zip.*
.archive-imports/
.input-staging/
.input-download/
.release-staging/
visual-analysis/output/
```

After Releases are verified, deleting the Codespace removes local uploads and temporary workspaces without changing Release assets.
