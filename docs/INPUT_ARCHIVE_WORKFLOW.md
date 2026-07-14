# ZIP input and snapshot workflow

The browser-based Codespaces Explorer can be unreliable when a large directory contains many media files. The supported primary input is therefore one `results.zip` file. Direct `results/` folder input remains compatible, but it is no longer the recommended browser-upload path.

## Primary path: upload one ZIP and publish meaningful releases

Create a ZIP locally with either of these layouts:

```text
results.zip
  results/
    2026-06-29/
      run_20260629_120000/
        outputs.jsonl
        errors.jsonl
        media/images/...
        media/videos/...
```

or:

```text
results.zip
  2026-06-29/
    run_20260629_120000/...
```

One extra wrapper directory is also accepted. ZIP64 archives larger than 2 GiB are supported.

1. Open a Codespace on `main`.
2. Upload `results.zip` to the repository workspace.
3. If the Codespace was already open before this feature was merged, update the tracked code:

```bash
git pull --ff-only
```

`results.zip` is ignored by Git, so its presence does not enter Git history or prevent a normal fast-forward pull.

4. Publish every new date and run:

```bash
python tools/publish_from_archive.py results.zip
```

The command:

- rejects incomplete or unsafe ZIP members;
- checks whether the uploaded archive changes during processing;
- estimates required free disk space;
- extracts to `.archive-imports/` temporarily;
- accepts a top-level `results/`, direct date directories, or one wrapper directory;
- invokes the existing SHA-256 duplicate-aware date publisher;
- removes extracted files after completion;
- leaves the original `results.zip` in the Codespace.

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

Keep the extracted tree for inspection:

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

## Last-resort browser transfer: upload two ordinary files

If the browser also fails to upload one 2+ GiB ZIP, split it locally in WSL and upload the resulting files one at a time. This only changes the transport into Codespaces; the reconstructed ZIP and all later Releases remain identical.

In WSL, beside `results.zip`:

```bash
sha256sum results.zip > results.zip.sha256
split -b 1500M -d -a 3 results.zip results.zip.upload-part-
```

Upload these files individually:

```text
results.zip.upload-part-000
results.zip.upload-part-001
results.zip.sha256
```

Then reconstruct and verify inside Codespaces:

```bash
cat results.zip.upload-part-* > results.zip
sha256sum -c results.zip.sha256
python tools/publish_from_archive.py results.zip
```

The upload parts and reconstructed archive are ignored by Git.

## Fast storage path: publish an input snapshot first

Use this when the priority is to get the uploaded archive into Release storage immediately, before spending time extracting, analyzing, and repackaging every date.

```bash
python tools/input_snapshot.py publish results.zip
```

The script verifies that the ZIP central directory is readable, splits the file into byte-exact parts below 1.8 GiB, calculates SHA-256 for the source and every part, and creates a neutral input snapshot Release such as:

```text
Tag: media-input-2026-07-15-<first-12-SHA-256-characters>
Assets:
  results.zip.part001
  results.zip.part002
  input-snapshot-manifest.json
```

The text inside angle brackets is descriptive, not a literal tag to paste. The publish command prints the exact real tag after a successful upload.

The original ZIP is not recompressed. Temporary split parts are removed after successful upload.

A packaging-only test is available:

```bash
python tools/input_snapshot.py publish results.zip --dry-run
```

## Promote a stored snapshot later

### From GitHub Actions

1. Open **Actions**.
2. Select **Promote input snapshot**.
3. Select **Run workflow**.
4. Leave `snapshot_tag` as `latest` to promote the newest input snapshot.
5. Leave `dry_run` disabled to create the normal date-scoped Releases.

An exact tag is optional. To list the currently available snapshot tags from Codespaces:

```bash
gh release list --limit 1000 --json tagName \
  --jq '.[] | select(.tagName | startswith("media-input-")) | .tagName'
```

The resolver checks the tag before downloading anything. If a supplied tag does not exist and only one snapshot is present, it automatically uses that one and prints a warning. If multiple snapshots exist, it stops and lists the valid choices.

The workflow downloads and verifies every part, reconstructs the original ZIP byte-for-byte, extracts it safely, runs the normal publisher, and then explicitly starts the analytics workflow.

### From Codespaces

Promote the latest snapshot:

```bash
python tools/input_snapshot.py promote
```

Promote an exact snapshot:

```bash
python tools/input_snapshot.py promote --tag media-input-2026-07-15-<real-sha-prefix>
```

Restore the latest snapshot only, without publishing:

```bash
python tools/input_snapshot.py restore --output restored-results.zip
```

## Existing folder path remains compatible

When a complete `results/` directory is already present in the Codespace, the original command still works:

```bash
python tools/publish_results.py --source results
```

This path is useful for terminal-based transfer tools or small result trees, but browser directory drag-and-drop is not the preferred path.

## Cleanup

All of these paths are ignored by Git:

```text
results/
results*.zip
results.zip.*
.archive-imports/
.input-staging/
.input-download/
.release-staging/
```

After Releases have been verified, deleting the Codespace removes the uploaded archive and temporary workspace without changing any Release assets.
