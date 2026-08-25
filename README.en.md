# Media Experiment Ledger

[繁體中文](README.md) | **English**

A media-generation experiment platform that uses **GitHub Releases as an immutable data layer**. It preserves image/video runs, rebuilds Analytics and forecasts, publishes a full-corpus Prompt Repeatability Atlas, and compares YOLOX with NanoDet without committing large source result folders into Git history.

<!-- STUDIO_ENTRY:START -->
> [!TIP]
> **Desktop app: Media Experiment Ledger Studio**  
> The cross-platform, local-first Atlas, object-detection, and media-automation desktop product is maintained on [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main).  
> [Download Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v) · [Desktop app guide](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/app/README.md) · [Complete specification](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/docs/app/README.md)
<!-- STUDIO_ENTRY:END -->

## Start here

| Goal | Entry point |
|---|---|
| Inspect the current corpus, Atlas, and detector history | [Project status and history](docs/PROJECT_STATUS.en.md) |
| Upload, store, or promote `results.zip` | [ZIP and snapshot workflow](docs/INPUT_ARCHIVE_WORKFLOW.en.md) |
| Publish from Codespaces | [Codespaces publishing guide](docs/CODESPACES_PUBLISHING.en.md) |
| Browse Analytics, Visual Lab, Detector Lab, and forecasts | [GitHub Pages observatory](https://pme26elvis.github.io/media-experiment-ledger/) |
| Understand data and trust boundaries | [Project contract](docs/PROJECT_CONTRACT.md) |
| Find every technical document | [Documentation hub](docs/README.en.md) |

## Core capabilities

### Release-backed ledger

- Creates one immutable `media-exp-*` Release per experiment date, with supplemental Releases for genuinely new runs on an existing date.
- Packages images, videos, JSONL metadata, and SHA-256 manifests separately, splitting assets before GitHub's single-asset boundary.
- Skips identical content and fails closed when the same `run_id` is reused with different content.
- Stores large archives as byte-exact `media-input-*` snapshots for later promotion.

### Reproducible analysis

- Rebuilds Analytics and ensemble forecasts from formal Releases.
- Uses one corpus for image and video Prompt Repeatability Atlas products while keeping media types in separate cohorts.
- Packages deterministic bundles with 15 prompt IDs each; images receive comparison cards, while videos receive FFmpeg validation, synchronized GIFs, and keyframe sheets.
- Publishes Overview, Analytics, Visual Lab, Detector Lab, YOLO Lab, Forecast Lab, System Atlas, and Frontend Stack through GitHub Pages.

### Object detection

- YOLOX-Tiny and NanoDet-Plus-m-320 use read-only, `workflow_dispatch`-only inference workflows to process the complete canonical image corpus from scratch; repository pushes cannot accidentally launch an expensive full-corpus inference run.
- The publisher accepts only exact workflow run IDs with matching `analysis_batch_id`, corpus fingerprint, quarantine digest, SHA set, labels, and thresholds.
- When an Action promotion changes the corpus, it records the exact two inference run IDs, waits for both runs to succeed, and explicitly hands that pair to the comparison publisher instead of depending on chained `workflow_run` discovery.
- `media-detection-*` reports agreement, disagreement, box IoU, class deltas, and runtime. Without human ground truth it never claims accuracy, precision, recall, or mAP.
- [Multi-detector specification](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md) · [Detector Lab](web/src/content/docs/detector-lab.mdx)

## Fastest publishing paths

### Publish one multi-day archive directly

```bash
python tools/publish_from_archive.py results.zip
```

Validate without publishing:

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

### Store first, then promote through Actions

```bash
python tools/input_snapshot.py publish results.zip
```

Then run **Actions → Promote input snapshot**. When a non-dry-run promotion creates new formal Releases, the Action refreshes Analytics and the Release Audit, starts YOLOX and NanoDet with one shared batch ID, captures their exact run IDs, waits for both to succeed, then dispatches and waits for the comparison publisher. Repeated no-op promotion does not waste detector inference.

> Direct CLI promotion still creates formal Releases and triggers Analytics and the Atlas, but it does not additionally dispatch Audit/detector maintenance. See the [input workflow guide](docs/INPUT_ARCHIVE_WORKFLOW.en.md) for the complete distinction. If detector inference succeeded but publication was interrupted, manually run **Publish YOLOX + NanoDet comparison** with those two existing run IDs instead of rerunning inference.

## Data flow

```text
results.zip / results/
  → optional media-input-* snapshot
  → immutable media-exp-* Releases
  ├─ Analytics + Forecast + GitHub Pages
  ├─ image/video Prompt Repeatability Atlas → media-analysis-*
  ├─ full Release integrity audit
  └─ exact YOLOX + NanoDet runs → comparison publisher → media-detection-*
```

## Data integrity

- [`project-contract.json`](project-contract.json) is the machine-validated synchronization anchor.
- [`config/release-quarantine.json`](config/release-quarantine.json) preserves historical assets while excluding confirmed empty runs and metadata fixtures.
- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) permits an audited `authoritative: true` correction only for a proven-wrong legacy report; current totals never rewrite immutable history.
- The [`Experiment Release Audit`](docs/reports/EXPERIMENT_RELEASE_AUDIT.md) verifies manifests, JSONL, ZIP members, sizes, SHA-256, and CRC.
- `site/` is an ephemeral Pages build artifact rather than tracked Git output; build, deploy, and writeback remain separate.

## Repository map

| Area | Role |
|---|---|
| `tools/` | Publication, analysis, Atlas, detector, forecast, and validation tooling |
| `.github/workflows/` | Publication, promotion, Analytics, Atlas, audit, detector, and Pages orchestration |
| `docs/` | Operator guides, specifications, contracts, status, and production evidence |
| `data/` | Versioned latest/history/audit indexes |
| `web/` | Astro/Starlight Pages frontend and deployed data |
| `app-main` | Media Experiment Ledger Studio desktop-product branch |

## Development and validation

```bash
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt \
  -r requirements-yolo.txt \
  -r requirements-nanodet.txt
sudo apt-get install -y --no-install-recommends ffmpeg
python tools/validate_project_contract.py
python -m compileall tools tests
python -m unittest discover -s tests -v
python tools/yolo_model_smoke.py
python tools/nanodet_model_smoke.py
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```

Repository operating and merge policy is documented in [`AGENTS.md`](AGENTS.md). Growing generated statistics and history tables now live in [`docs/PROJECT_STATUS.en.md`](docs/PROJECT_STATUS.en.md) instead of the landing page.
