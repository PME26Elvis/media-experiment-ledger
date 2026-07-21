# AGENTS.md

## Scope

This file applies to the entire repository. A more specific `AGENTS.md` in a subdirectory may override it for that subtree.

## User and communication preferences

- Default user-facing language is **Traditional Chinese**.
- When the user has granted broad permission, make mainstream and reasonable implementation decisions directly instead of repeatedly asking about minor details.
- Prefer a working, production-ready implementation over a plan-only response.
- Keep progress updates concise and honest. Never claim that a workflow, Release, or deployment succeeded until it has been checked.
- Do not promise asynchronous work. Complete as much as possible in the current session.

## Git and GitHub workflow

- Work on a feature branch, open a pull request, run validation, and use a normal merge commit unless the user explicitly requests another method.
- Do not delete branches unless asked.
- Prefer a focused but complete pull request: implementation, regression tests, documentation, workflow updates, and user-facing entry points should stay synchronized.
- When GitHub connector or Actions access is unavailable, run all feasible checks locally and provide either a unified patch or Codespaces-ready commands as the fallback.
- Never use a passing unit test as proof that a production Release or deployment succeeded; verify the actual Release/index/writeback/Pages run when the task includes publication.

## Contract hierarchy

- Read `project-contract.json` first for machine-enforced values and `docs/PROJECT_CONTRACT.md` for rationale.
- Apply `config/release-quarantine.json` to every canonical corpus consumer.
- Preserve immutable Atlas history: explicit report metrics normally win, then `config/atlas-history-overrides.json`; only a proven corrupt legacy report may use an audited `authoritative: true` override. Never backfill an old row from current corpus totals.
- When a contract changes, update all synchronized surfaces in the same PR and run `python tools/validate_project_contract.py`.
- YOLOX-Tiny object detection is `implemented`: production Release `media-yolo-all-2026-07-13-v1`, writeback commit `bab357c4f92963d5d74e7229ad86272147436295`, YOLO Lab, README history, 387-image coverage, and Atlas non-regression were verified.
- The planned YOLOX + NanoDet comparison architecture is `specified_not_implemented`; follow `docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md` and do not imply the workflows or `media-detection-*` Release family exist until implemented and production-verified.

## Repository source-of-truth rules

- Formal experiment data comes only from immutable `media-exp-*` Releases.
- `media-input-*` Releases are transport/snapshot artifacts. Do not include them in formal statistics or analysis source data.
- Existing published experiment Releases are immutable. New data for an existing date must use the established supplemental Release flow.
- Historical invalid runs remain as evidence but are excluded through `config/release-quarantine.json`; never silently delete them.
- Distinguish API completion events from archived media files. Publication must fail when their counts differ.
- Prompt Repeatability Atlas and detector inference rebuild from the complete currently published canonical corpus. Avoid hidden incremental state or processing caches unless there is a documented, explicit contract change.
- Release assets remain ZIP-only. Inline JPEG/GIF previews are served from versioned repository paths rather than uploaded as naked Release assets.
- Image and video Atlas bundles contain up to 15 prompt IDs each.

## Pages and generated-output behavior

- `web/` is source; `site/` is compiled Astro output.
- `site/` is ephemeral, ignored by Git, and must never be committed to `main`.
- GitHub Pages receives `site/` only through `actions/upload-pages-artifact` and `actions/deploy-pages`.
- The analytics workflow must keep **build**, **deploy**, and **writeback** as separate jobs.
- Pages deployment depends on the validated build artifact, not on a successful Git push.
- Canonical writeback is limited to `analytics/` and `forecasts/`, downloaded from a short-lived workflow artifact and committed with fetch/rebase/push retries.
- Never add `site/` to writeback paths; doing so duplicates versioned Atlas GIF/JPEG and detector previews and causes large generated commits.
- `tools/validate_site_build.py` must cover all primary routes, Analytics/Forecast/Visual Lab/YOLO Lab JSON URLs, JSON parsing, malformed base paths, and Pages artifact size guards.

## Atlas behavior

- Image and video samples must remain in separate cohorts.
- Video seed is retained as sample evidence but excluded from the repeatability cohort identity because the harvester intentionally randomizes it for each run.
- Image Release Notes previews use an evidence-rich dynamic policy:
  - at most 15 image cohorts;
  - at least 4 verified unique samples by default;
  - cover distinct categories first using the strongest cohort in each category;
  - fill remaining slots by descending sample count with deterministic tie-breaking.
- Video Release Notes previews include all eligible comparable video cohorts by default. The current corpus contains seven video prompt cohorts.
- Release Notes should use separate **Image highlights** and **Video highlights** sections and may be long when the entries materially improve inspection.
- Every highlighted entry must link to its containing ZIP bundle.
- Keep backward-compatible combined `highlights` metadata when adding media-specific highlight fields.
- Detector work must not reduce, replace, gate, or move these Atlas image/GIF Release Notes previews.

## YOLO behavior

- Workflow: `.github/workflows/yolo-object-detection.yml`.
- Release family: `media-yolo-all-<latest-experiment-date>-vN`.
- Execution: one complete GitHub-hosted CPU job with a 350-minute timeout, not a matrix in v1.
- Runtime/model: ONNX Runtime CPU with the SHA-pinned YOLOX-Tiny COCO model in `object-detection/model-lock.json`.
- Every invocation reprocesses the complete canonical image corpus from scratch.
- No persistent state, cross-run cache skip, incremental-only mode, or published-result reuse.
- Within one invocation, byte-identical images may be inferred once while all source aliases are preserved.
- All Release assets are ZIP containers; representative annotated previews are copied to versioned repository paths for Notes and YOLO Lab.
- YOLO and Atlas do not share a workflow, draft Release, finalizer, assets, Notes, latest pointer, or history table.
- YOLO Lab may read the independent YOLO index; joining with Atlas is allowed only by stable image SHA-256 and must tolerate either side being absent.
- YOLO failure must not affect Atlas, and Atlas failure must not affect YOLO.
- Tests must lock the existing Atlas preview contract as a non-regression requirement.

## Planned multi-detector behavior

- Planned inference workflows are `.github/workflows/detector-yolox-inference.yml` and `.github/workflows/detector-nanodet-inference.yml`; the planned publisher is `.github/workflows/detector-comparison-publish.yml`.
- The initial publisher must accept **exact workflow run IDs**. Never pair "latest successful" detector runs.
- Both artifacts must have identical `analysis_batch_id`, corpus fingerprint, quarantine digest, source Release list, canonical image SHA set, and COCO labels hash.
- Workflow artifacts are short-lived transport only, never source of truth, inference cache, or persistent processing state.
- The planned combined Release family is `media-detection-all-<latest-experiment-date>-vN`; existing `media-yolo-*` Releases remain immutable single-detector history.
- The comparison gallery uses Original / YOLOX-Tiny / NanoDet-Plus tri-panels plus a full offline HTML ZIP.
- Without human-verified ground truth, describe agreement, disagreement, coverage, IoU, class distributions, and runtime. Never claim accuracy, precision, recall, or mAP on this generated corpus.
- Multi-detector workflows and Releases remain independent of Atlas. They may not change Atlas Notes, previews, indexes, Releases, history, or workflow success.

## Documentation and UX direction

- `README.md` is the default Traditional Chinese landing page; `README.en.md` is the English companion.
- Update README, analysis specifications, Visual Lab/YOLO Lab, and workflow descriptions whenever an implementation contract changes.
- The project should feel polished and complete rather than intentionally minimal. Rich but coherent UI/UX is preferred.
- Avoid hiding evidence merely to shorten a page. Use grouping, filters, headings, and downloadable bundles to manage density.

## Validation expectations

Before merging relevant changes, run or verify:

```bash
python tools/validate_project_contract.py
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt \
  -r requirements-yolo.txt
sudo apt-get install -y --no-install-recommends ffmpeg
python -m compileall tools tests
python -m unittest discover -s tests -v
python tools/yolo_model_smoke.py
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
python tools/validate_site_build.py
```

For video Atlas work, tests must exercise real `ffmpeg`/`ffprobe` behavior with generated media rather than only mocking subprocess calls. For YOLO work, CI must download the pinned model, verify its size/SHA, create an ONNX Runtime CPU session, and validate the real output tensor shape. For Pages work, tests must ensure `site/` remains ignored/untracked and deployment is independent of writeback. For future NanoDet work, validate official checkpoint integrity, deterministic ONNX export, normalized sidecars, exact-run artifact pairing, and comparison-language guardrails.

<!-- NANODET:AGENTS:START -->
## Multi-detector behavior

- Multi-detector status is `implemented_pending_production` until the production evidence fields in `project-contract.json` are populated.
- Inference workflows are read-only and artifact-only. Pair only exact workflow run IDs; never combine independently selected "latest" runs.
- NanoDet-Plus uses the SHA-pinned official immutable pre-exported ONNX and `requirements-nanodet.txt`; do not reintroduce the obsolete Lightning checkpoint exporter without a new audited decision.
- The publisher must verify batch, corpus fingerprint, quarantine digest, source Releases, canonical image SHA set, COCO labels, thresholds, sidecar coverage, package hashes, and ZIP CRC before creating `media-detection-*`.
- Detector Lab is the primary combined UI. YOLO Lab remains a legacy historical view.
- Use agreement/disagreement language only. No accuracy claim is allowed without ground truth.
- Multi-detector work must not change Atlas workflow, Releases, previews, indexes, history, or finalizer.
<!-- NANODET:AGENTS:END -->
