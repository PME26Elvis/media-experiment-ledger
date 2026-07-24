# 06 — Detection Studio Specification

## 1. Scope

Detection Studio is an independent local object-detection product inside the desktop app. It allows users to select one or more supported models, run inference over a project image corpus, pause/resume or recover jobs, inspect detections and compare model agreement/disagreement.

It must include the two models already used by the repository:

- YOLOX-Tiny;
- NanoDet-Plus-m-320.

It must also support a model registry capable of offering larger/more computationally expensive variants after runtime and artifact-license validation.

Detection Studio is independent from Atlas Studio. The modules may join results by stable image SHA-256, but neither module controls the other's job, output, history or success state.

## 2. Goals

- Make real local inference accessible through a polished GUI.
- Support multiple model sizes and clear compute tiers.
- Verify model identity and license metadata.
- Avoid bundling model artifacts until redistribution rights are reviewed.
- Download models on demand with checksums and resumable transfer.
- Run thousands of images without blocking the app.
- Persist per-item checkpoints and recover from app/engine crash.
- Display accurate progress at job, model, stage and item levels.
- Preserve machine-readable outputs and visual previews.
- Compare models without mislabeling disagreement as accuracy.

## 3. Explicit non-goals for v1

- Training/fine-tuning.
- Full annotation platform.
- Automatic accuracy, precision, recall or mAP claims on unlabeled generated images.
- Running unverified arbitrary Python model repositories.
- Loading model files directly in the renderer.
- Assuming every official code repository license automatically covers every linked pretrained weight.

## 4. Model registry

### 4.1 Registry entry

Each model version has a signed or repository-controlled manifest:

```json
{
  "modelId": "yolox-tiny-coco-onnx",
  "family": "YOLOX",
  "variant": "Tiny",
  "version": "upstream-or-app-model-version",
  "format": "onnx",
  "input": { "width": 416, "height": 416, "layout": "NCHW" },
  "outputSchema": "yolox-coco-v1",
  "labels": "coco-80-v1",
  "artifact": {
    "distributionMode": "bundled|download|user-supplied|blocked",
    "url": "optional",
    "size": 0,
    "sha256": "..."
  },
  "license": {
    "codeLicense": "Apache-2.0",
    "weightLicenseStatus": "verified|needs-review|user-supplied-only|blocked",
    "noticeFiles": []
  },
  "runtime": {
    "minimumRamBytes": 0,
    "estimatedPeakRamBytes": 0,
    "executionProviders": ["cpu"]
  },
  "adapterVersion": "1"
}
```

### 4.2 Registry sources

- built-in registry shipped with app;
- signed registry update delivered with app update;
- project-pinned registry snapshot;
- user-supplied model entry created through an expert validation wizard, provisional.

Remote registry content must not define executable code. It may reference only adapters already shipped and allowlisted.

### 4.3 Model states

- not installed;
- downloading;
- verifying;
- installed;
- update available;
- incompatible runtime;
- license review required;
- user-supplied;
- corrupt;
- disabled/deprecated.

## 5. Initial model catalog

### 5.1 YOLOX

Required baseline:

- YOLOX-Tiny — current repository-compatible model.

Candidate catalog after artifact review:

- YOLOX-Nano — lower resource option;
- YOLOX-S — higher quality/compute than Tiny/Nano;
- YOLOX-M;
- YOLOX-L;
- YOLOX-X — highest resource official family option in the initial catalog.

The UI displays input resolution, artifact size, parameter/FLOP information where verified, expected speed tier and estimated memory based on local benchmarks.

### 5.2 NanoDet-Plus

Required baseline:

- NanoDet-Plus-m-320 — current repository-compatible model.

Candidate larger options from the official model family:

- NanoDet-Plus-m-416;
- NanoDet-Plus-m-1.5x-320;
- NanoDet-Plus-m-1.5x-416.

Legacy NanoDet/EfficientLite/RepVGG variants are not initial commitments; the registry can add them only when adapter/output compatibility and artifact licenses are documented.

### 5.3 Support definition

A model is “supported” only when all are present:

- immutable model identity and SHA-256;
- input/preprocessing specification;
- output decoding specification;
- labels identity/hash;
- postprocessing/NMS behavior;
- real-runtime smoke test;
- golden fixture tests;
- license status;
- packaged-runtime compatibility on supported platforms;
- resource tier metadata;
- output schema version.

A model appearing in an upstream README is not sufficient.

## 6. License and distribution policy

### 6.1 Separate review layers

Review separately:

1. source code license;
2. pretrained weight license/terms;
3. training dataset license/usage notes;
4. labels file provenance;
5. conversion/exported ONNX artifact rights;
6. app redistribution versus download-at-runtime rights;
7. required attribution/notices.

### 6.2 Distribution modes

- `bundled`: included in installer/resources after verified redistribution approval;
- `download`: app downloads official/approved artifact after user review;
- `user-supplied`: app provides adapter but user must select their own model file;
- `blocked`: known incompatible/restricted artifact;
- `needs-review`: visible in planning/docs but unavailable in stable UI.

### 6.3 Initial conservative policy

Until a documented artifact review is completed:

- application packages should not automatically bundle candidate model weights;
- baseline models may remain download-on-demand or user-supplied even when repository code is Apache-2.0;
- each model card displays source, license status, size and hash before download;
- notices are retained in Model Manager and report manifests.

## 7. Model Manager UX

### 7.1 Model card

Each `v-hover` model card shows:

- family/variant;
- installed state;
- compute tier;
- input size;
- expected relative speed;
- verified artifact size;
- execution providers;
- license status chip;
- update status;
- primary action with semantic color/icon.

### 7.2 Model detail

Tabs:

- Overview;
- Technical details;
- License & provenance;
- Local benchmark;
- Files & hashes;
- Compatibility;
- Diagnostics.

Actions:

- download/install;
- verify;
- benchmark;
- reveal model folder;
- remove;
- repair/redownload;
- export manifest, not necessarily the weight;
- select user-supplied artifact;
- compare variants.

### 7.3 Download

- resumable where server supports range requests;
- streamed to `.partial` staging file;
- expected size enforced;
- SHA-256 verified before install;
- atomic move into content-addressed model store;
- corrupt downloads retained only for diagnostics according to policy;
- simultaneous jobs share one download lease;
- user sees disk requirement and free space.

## 8. Runtime and execution providers

### 8.1 Initial baseline

CPU inference through ONNX Runtime is the required universally supported baseline.

### 8.2 Optional acceleration

Potential providers:

- CUDA on compatible Windows/Linux NVIDIA systems;
- DirectML on Windows;
- CoreML on macOS;
- other ONNX Runtime providers after packaging validation.

Acceleration is provisional and must fall back safely. The UI never promises GPU merely because a GPU exists.

### 8.3 Capability probe

At app/engine startup or on demand:

- enumerate supported execution providers;
- run a tiny verified smoke;
- record runtime version;
- measure available memory where reliable;
- classify driver/provider errors;
- hide or disable unusable combinations;
- store benchmark by model/provider/device/app version.

### 8.4 Resource presets

- Eco: low concurrency, minimal memory.
- Balanced: default.
- Performance: higher concurrency after benchmark.
- Custom: expert settings.

The app estimates resource impact and warns about likely memory pressure.

## 9. Detection job creation

Wizard steps:

1. Input corpus/saved filter.
2. Model selection.
3. Runtime provider and resource preset.
4. Detection thresholds.
5. Output paths and retention.
6. Comparison settings.
7. Validation and benchmark estimate.
8. Final review.

### 9.1 Input snapshot

Store:

- asset IDs and SHA-256;
- paths/grants;
- dimensions/format;
- exclusion reasons;
- ordering;
- corpus fingerprint.

A job does not silently expand when new files appear.

### 9.2 Per-model settings

- confidence threshold;
- NMS IoU threshold;
- class allow/block list;
- input resizing mode fixed by adapter where required;
- batch size only if adapter/provider supports it;
- execution provider;
- thread/concurrency limit;
- preview rendering toggle;
- retain raw normalized output toggle.

Settings are stored per model in the job snapshot.

### 9.3 Comparison settings

- same-class matching IoU threshold;
- class mapping identity;
- pairwise or reference-model view;
- include both-empty items;
- representative preview selection;
- disagreement scoring policy;
- comparison language guardrail.

## 10. Inference pipeline

For each model:

1. verify model/labels/runtime identity;
2. acquire model execution lease;
3. enumerate pending input snapshot items;
4. decode image;
5. apply adapter-defined color conversion and resize/letterbox/direct-resize;
6. normalize/layout tensor;
7. execute inference;
8. decode outputs;
9. recover coordinates to original image;
10. apply class-aware postprocessing/NMS;
11. validate finite coordinates/confidences/classes;
12. write normalized sidecar atomically;
13. optionally render annotation preview;
14. commit item checkpoint;
15. update aggregated summaries.

Comparison begins only when required model outputs for an item are verified.

## 11. Item and checkpoint state

### 11.1 Item states per model

- pending;
- decoding;
- preprocessing;
- inferring;
- postprocessing;
- writing;
- completed;
- failed-retryable;
- failed-terminal;
- skipped-invalid-input;
- cancelled-after-completion;
- checkpoint-corrupt.

### 11.2 Durable checkpoint

Checkpoint includes:

- job/model/item ID;
- input asset hash;
- model/labels/adapter/runtime hashes;
- config hash;
- state;
- attempt count;
- timestamps/duration;
- output sidecar path/hash;
- preview path/hash;
- detection count;
- failure classification;
- worker identity.

An item is complete only after output verification and DB transaction commit.

### 11.3 Resume compatibility

Completed checkpoint may be reused only when all identity hashes match. Changing model, threshold that affects postprocessing, adapter or input invalidates the affected stage.

Potential optimization:

- retain raw model output to rerun threshold/NMS without inference when schema and storage policy allow;
- this is opt-in because raw tensors may be large.

## 12. Pause, cancellation and recovery

### 12.1 Pause

- stop scheduling new items;
- allow in-flight inference to finish or reach adapter-safe boundary;
- commit outputs;
- release model resources if pause exceeds threshold;
- state becomes paused only after durable checkpoint flush.

### 12.2 Cancel

Options:

- cancel and keep verified partial results;
- cancel and delete derived results after confirmation;
- cancel comparison only while retaining model runs.

Source media and installed models are never deleted by job cancellation.

### 12.3 Crash recovery

On restart:

- detect expired worker leases;
- verify outputs for items left in nonterminal states;
- promote valid written outputs to completed if transaction was interrupted;
- mark ambiguous/corrupt outputs for rerun;
- resume remaining items;
- avoid reprocessing verified items.

### 12.4 OOM/resource failure

When memory pressure or provider OOM occurs:

1. record provider/model/item context;
2. unload session;
3. lower concurrency/batch according to policy;
4. retry bounded times;
5. fall back to CPU only with explicit configured permission;
6. otherwise pause with recommended action.

Automatic fallback is shown in job history.

## 13. Progress and observability

### 13.1 Progress hierarchy

- Logical comparison job.
- Model run.
- Pipeline stage.
- Individual item.
- Final comparison/render/package stage.

### 13.2 UI

Live view includes:

- overall deterministic progress bar;
- one progress bar per model;
- current stage label;
- completed/failed/skipped counts;
- current asset thumbnail/name;
- throughput and moving average;
- estimated remaining time after warm-up;
- CPU/GPU/memory indicators when reliable;
- checkpoint/save indicator;
- pause/cancel controls;
- expandable event log.

Progress 100% does not mean success until output/index verification completes.

### 13.3 Event aggregation

Workers may emit per-item events, but renderer updates are throttled/aggregated. The database and Job Center remain canonical.

## 14. Normalized output schema

Per-image/model sidecar:

```json
{
  "schemaVersion": 1,
  "jobId": "uuid",
  "assetId": "uuid",
  "imageSha256": "...",
  "model": {
    "modelId": "...",
    "artifactSha256": "...",
    "adapterVersion": "...",
    "executionProvider": "cpu"
  },
  "input": { "width": 0, "height": 0 },
  "settings": { "confidence": 0.25, "nmsIou": 0.45 },
  "detections": [
    {
      "classId": 0,
      "className": "person",
      "confidence": 0.9,
      "box": { "x1": 0, "y1": 0, "x2": 1, "y2": 1 },
      "coordinateSpace": "original-pixels"
    }
  ],
  "timing": {},
  "warnings": []
}
```

Coordinates must be bounded/validated. Non-finite values fail the item.

## 15. Comparison model

### 15.1 Matching

Default pairwise matching:

- same class;
- IoU at or above configured threshold;
- deterministic one-to-one assignment;
- unmatched detections retained.

### 15.2 Summary states

Per image:

- both empty;
- both nonempty;
- model A only nonempty;
- model B only nonempty;
- both nonempty with match/disagreement metrics;
- one or more model failures.

### 15.3 Allowed language

Allowed:

- agreement;
- disagreement;
- coverage;
- detection count;
- matched same-class boxes;
- IoU distribution;
- class distribution;
- runtime/throughput.

Prohibited without human ground truth:

- accuracy;
- precision;
- recall;
- false-positive rate;
- false-negative rate;
- mAP claims on this corpus.

If ground-truth import is later added, metrics live in a separate explicitly labeled evaluation mode.

## 16. Detection result browser

### 16.1 Views

- annotated gallery;
- original/model overlay comparison;
- tri-panel original + two models;
- table;
- class distribution;
- disagreement ranking;
- failures/retry queue;
- runtime diagnostics.

### 16.2 Filters

- model;
- class;
- confidence;
- detection count;
- comparison state;
- disagreement score;
- prompt/category/tag;
- failed/skipped;
- included in report;
- execution provider.

### 16.3 Overlay controls

- show/hide boxes;
- label/confidence display;
- line thickness;
- class color scheme;
- model-specific overlay;
- synchronized zoom/pan;
- original pixels versus proxy;
- export selected annotation.

Renderer uses optimized image proxies and vector overlays. It must not eagerly generate/store a full annotated original for every image unless requested by job policy.

## 17. Packaging and exports

A completed job can export:

- normalized JSON/JSONL sidecars;
- CSV summary;
- model manifests/licenses;
- job config and corpus fingerprint;
- representative annotated previews;
- full offline gallery;
- selected result images;
- comparison summary;
- integrity/checksum manifest.

Large exports use multipart ZIPs with size boundaries. Export does not include model weights by default.

## 18. Performance requirements

- model session loaded once per worker/run, not per image;
- input decode and inference concurrency are independently bounded;
- thousands of DB rows use pagination;
- overlay rendering is on demand;
- thumbnail/proxy cache is shared by image hash;
- memory cache has hard budgets;
- engine provides backpressure;
- worker count defaults from benchmark, not raw CPU core count alone;
- model switching unloads resources deterministically;
- long jobs can run with renderer closed/minimized;
- UI event frequency remains bounded.

Design benchmark:

- 10,000 mixed-size images;
- two models;
- restart midway;
- corrupt item subset;
- low disk space and memory-pressure scenarios.

## 19. Security

- model downloads are hash-verified;
- model directory is not renderer-writable;
- user-supplied models are data, not executable plugins;
- adapters are shipped/signed code only;
- ONNX external-data files are path-validated;
- outputs use safe atomic paths;
- report HTML is isolated/sanitized;
- license/source links open externally through allowlist flow;
- diagnostics redact local paths in exported bundles when chosen.

## 20. Acceptance criteria

- YOLOX-Tiny and NanoDet-Plus-m-320 run real smoke/inference on all supported platforms;
- candidate larger variants remain unavailable until model-specific verification passes;
- model cards show size, hash, source and license status;
- download resumes and rejects wrong hash;
- user can select one or multiple models;
- job progress is visible at overall/model/stage/item levels;
- pause waits for safe checkpoint and resume skips verified items;
- app restart recovers mid-corpus job;
- OOM/concurrency fallback is bounded and recorded;
- normalized output coordinates match original image space;
- result browser remains responsive with 10,000 images;
- comparison uses exact model/corpus/config identities;
- no unlabeled-corpus accuracy claim appears;
- Atlas data/history is not changed by detector work;
- exports include config, hashes and model license/provenance metadata.