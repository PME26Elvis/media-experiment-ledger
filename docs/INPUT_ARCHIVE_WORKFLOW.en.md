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

Upload the parts and checksum, then reconstruct and verify inside Codespaces:

```bash
cat results.zip.upload-part-* > results.zip
sha256sum -c results.zip.sha256
python tools/publish_from_archive.py results.zip
```

This changes only browser transport. The reconstructed archive, date Releases, and final Atlas trigger are identical to the primary path.

## Fast storage path: publish an input snapshot first

```bash
python tools/input_snapshot.py publish results.zip
```

The script verifies the ZIP central directory, splits the file into byte-exact parts below 1.8 GiB, calculates SHA-256 for the source and every part, and creates a neutral `media-input-*` Release. The source is not recompressed.

Input snapshots are transport/storage records. They are excluded from repository statistics and Atlas source data until promotion creates formal `media-exp-*` Releases.

Packaging-only test:

```bash
python tools/input_snapshot.py publish results.zip --dry-run
```

## Promote a stored snapshot later

### GitHub Actions

Run **Actions → Promote input snapshot** with `latest` or an exact `media-input-*` tag. The workflow reconstructs and verifies the exact ZIP, extracts it safely, and calls the same common publisher.

### Codespaces

```bash
python tools/input_snapshot.py promote
python tools/input_snapshot.py promote --tag media-input-2026-07-15-<real-sha-prefix>
python tools/input_snapshot.py restore --output restored-results.zip
```

## Direct folder compatibility

```bash
python tools/publish_results.py --source results
```

This first-class path scans every `YYYY-MM-DD` directory, publishes all new runs, and dispatches one all-data Atlas when the batch succeeds.

## Duplicate and conflict behavior

| Local state | Remote state | Result |
|---|---|---|
| New `run_id` | Missing | Publish in the date Release batch. |
| Same `run_id`, same digest | Present | Skip safely. |
| Same `run_id`, different digest | Present | Fail that date and do not dispatch the final Atlas. |
| New run on a published date | Primary exists | Create a `-sNN` supplement. |

A failure on one date does not prevent other dates from being evaluated, but the final Atlas waits for a failure-free batch.

## Cleanup

Ignored paths include `results/`, `results*.zip`, extraction/staging directories, and `visual-analysis/output/`. Deleting the Codespace does not change published Release assets.
