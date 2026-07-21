# Multi-detector YOLOX + NanoDet pipeline specification

> Status: **`implemented_pending_production`**  
> Decision: separate detector inference workflows, one aggregate publisher workflow, one combined detector Release family  
> Atlas impact: **none**

## 1. Goal

Add NanoDet-Plus as a second COCO-pretrained object detector without coupling it to Prompt Repeatability Atlas. YOLOX-Tiny and NanoDet must run independently, publish transport artifacts, and then feed a third workflow that creates one coherent detector Release plus a YOLOX-versus-NanoDet comparison gallery.

The target product is not an accuracy benchmark. The repository has generated media but no human-verified COCO ground truth. The comparison therefore reports **agreement, disagreement, coverage, box overlap, confidence, class distribution, and runtime**, never model accuracy, precision, recall, or mAP on this corpus.

## 2. Correctness of the proposed GitHub Actions architecture

The proposed architecture is valid:

1. Workflow A rebuilds the canonical corpus and runs YOLOX-Tiny.
2. Workflow B rebuilds the same canonical corpus and runs NanoDet-Plus.
3. Workflow C downloads the artifacts from the exact A/B workflow run IDs, validates them, builds comparison outputs, and publishes one Release.

`actions/download-artifact` supports downloading artifacts from another workflow run when `run-id` and `github-token` are supplied. The implementation should use the current major version available at development time; the initial design targets `actions/download-artifact@v5` rather than intentionally pinning the older v4 interface.

The difficult part is pairing two runs safely. "Latest successful YOLO" plus "latest successful NanoDet" is forbidden because the two runs may describe different source Releases, quarantine policy, thresholds, or code versions.

## 3. Release families

Existing immutable history remains valid:

- `media-yolo-all-*`: historical YOLO-only Releases.
- `media-analysis-*`: Prompt Repeatability Atlas; never modified by this feature.

After NanoDet production verification, new combined detector publications use:

```text
media-detection-all-<latest-experiment-date>-vN
```

Example:

```text
media-detection-all-2026-07-13-v1
```

The Release title identifies both detector implementations and model hashes. YOLO-only `media-yolo-*` Releases remain accessible but are treated as the legacy single-detector family.

## 4. Workflow topology

### 4.1 Workflow A — YOLOX inference

Planned file:

```text
.github/workflows/detector-yolox-inference.yml
```

Responsibilities:

- enumerate every published `media-exp-*` Release;
- apply `config/release-quarantine.json`;
- validate manifests, Release asset size/SHA, ZIP CRC, member paths and member hashes;
- build the canonical unique-image inventory;
- run the existing SHA-pinned YOLOX-Tiny ONNX Runtime CPU implementation;
- render annotated images and explicit empty-detection images;
- create success or failure sidecars for every canonical image;
- package YOLOX namespaced ZIP assets;
- upload exactly one workflow artifact containing the detector package and completion manifest;
- **do not create or edit a GitHub Release**;
- **do not write indexes or README history to `main`**.

### 4.2 Workflow B — NanoDet inference

Planned file:

```text
.github/workflows/detector-nanodet-inference.yml
```

Responsibilities mirror Workflow A, but use the NanoDet adapter and NanoDet model lock.

Initial model candidate:

```text
NanoDet-Plus-m-320
ShuffleNetV2 1.0x
320 × 320
COCO 80 classes
Apache-2.0
```

The official project reports approximately 1.17 million parameters, 0.9 GFLOPs, and 27.0 COCO mAP for this variant. These upstream benchmark values are descriptive metadata only and must not be presented as performance on this repository's generated images.

### 4.3 Workflow C — aggregate and publish

Planned file:

```text
.github/workflows/detector-comparison-publish.yml
```

Responsibilities:

- identify an exact successful YOLOX run and NanoDet run;
- download both workflow artifacts using exact run IDs and the repository token;
- extract only into `${{ runner.temp }}` after path validation;
- validate completion manifests and every packaged file hash;
- reject mismatched batches, corpora, source Release sets, quarantine digests, COCO labels, or image coverage;
- build detector-comparison JSON, representative tri-panel images and an offline HTML gallery;
- create deterministic comparison ZIP assets;
- create a draft `media-detection-all-*` Release;
- upload all namespaced ZIP assets;
- verify the published asset list and hashes;
- publish the Release;
- write independent detector latest/history indexes and versioned Release Notes previews to `main` with rebase/retry;
- never change Atlas indexes, Atlas Releases, Atlas previews, or Atlas history.

## 5. Batch identity and pairing

Every inference invocation receives or derives an immutable `analysis_batch_id`.

Recommended value:

```text
detection-<latest-experiment-date>-<corpus-fingerprint-12>-<requested-at-UTC>
```

Example:

```text
detection-2026-07-13-633b2daf9eab-20260721T040000Z
```

The batch ID is metadata, not persistent processing state. It exists only to pair workflow artifacts.

Both detector manifests must contain:

```json
{
  "schema_version": 1,
  "analysis_batch_id": "detection-...",
  "detector_id": "yolox-tiny" ,
  "workflow_run_id": 123456789,
  "head_sha": "...",
  "corpus_fingerprint": "...",
  "quarantine_policy_digest": "...",
  "source_release_tags": ["media-exp-..."],
  "date_from": "2026-06-29",
  "date_to": "2026-07-13",
  "canonical_image_count": 387,
  "successful_image_count": 387,
  "failed_image_count": 0,
  "labels_sha256": "...",
  "model_sha256": "...",
  "thresholds": {
    "confidence": 0.25,
    "nms_iou": 0.45,
    "max_detections": 100
  },
  "package_files": [
    {
      "name": "...zip",
      "size_bytes": 123,
      "sha256": "..."
    }
  ]
}
```

Publisher requirements:

- exact `analysis_batch_id` match;
- exact `corpus_fingerprint` match;
- exact `quarantine_policy_digest` match;
- identical ordered `source_release_tags`;
- identical canonical image SHA set;
- identical COCO label hash;
- zero missing sidecars;
- failures below the declared policy threshold;
- detector IDs must be distinct and expected.

A mismatch produces an explicit failed workflow and no Release.

## 6. Trigger strategy

### 6.1 Initial reliable mode

The initial implementation should favor explicit run pairing:

1. manually dispatch A and B with the same batch ID;
2. after both succeed, manually dispatch C with `yolox_run_id` and `nanodet_run_id`.

This mode is deterministic, easy to audit, and avoids hidden run selection.

### 6.2 Optional automatic mode

After production verification, C may listen to `workflow_run` completion events for A and B.

The publisher then:

1. downloads the triggering run's completion manifest;
2. reads its batch ID;
3. queries successful runs of the counterpart workflow;
4. finds exactly one unexpired counterpart artifact with the same batch ID;
5. exits successfully without publication if the counterpart is not ready;
6. publishes when both artifacts exist;
7. uses a fixed publisher concurrency group with `cancel-in-progress: false`;
8. checks for an existing draft/final Release carrying the same batch ID before creating another.

The batch-level duplicate-publication guard is publication idempotency, not inference-result reuse.

## 7. Artifact contract

### 7.1 YOLOX workflow artifact

Artifact name:

```text
detector-yolox-<analysis_batch_id>
```

Contents:

```text
completion-manifest.json
release-assets/
  yolox-coco-metadata.zip
  yolox-coco-detections-part001.zip
  yolox-coco-annotated-part001.zip
  yolox-coco-offline-gallery.zip
  yolox-coco-complete-part001.zip
```

### 7.2 NanoDet workflow artifact

Artifact name:

```text
detector-nanodet-<analysis_batch_id>
```

Contents:

```text
completion-manifest.json
release-assets/
  nanodet-coco-metadata.zip
  nanodet-coco-detections-part001.zip
  nanodet-coco-annotated-part001.zip
  nanodet-coco-offline-gallery.zip
  nanodet-coco-complete-part001.zip
```

Artifacts are transport packages only:

- retention: 7 days by default;
- `compression-level: 0` because payloads are already ZIP-compressed;
- no incremental state;
- no cache hit may skip inference;
- no artifact is considered a published source of truth;
- the final immutable Release remains the published product.

## 8. NanoDet model supply chain

### 8.1 Model choice

Initial target:

```text
NanoDet-Plus-m-320
```

Reasons:

- official Apache-2.0 project;
- COCO 80-class output aligns with YOLOX;
- very small model and low compute;
- suitable for GitHub-hosted CPU inference;
- materially different anchor-free detector architecture from YOLOX.

### 8.2 Export and runtime

The official project distributes PyTorch weights/checkpoints and provides `tools/export_onnx.py`.

The production implementation should use:

- a pinned NanoDet Git commit or tagged Release;
- a pinned official weight/checkpoint URL;
- expected byte size and SHA-256;
- Python 3.10 for compatibility with the upstream PyTorch range;
- pinned CPU PyTorch/torchvision versions for export;
- deterministic ONNX export with fixed input shape 320 × 320;
- SHA-256 of the exported ONNX written into the completion manifest;
- ONNX Runtime CPU for full-corpus inference.

Two acceptable implementation policies:

1. **Export every workflow run.** This is simplest, fully reproducible, and adds only model-setup time.
2. **Publish a repository-owned immutable model-preparation Release.** This reduces setup time, but requires a separate audited supply-chain spec and must not be treated as an inference result cache.

Initial implementation should use option 1 unless export compatibility proves unstable.

## 9. Common detector sidecar schema

Both detector adapters must emit the same normalized schema:

```json
{
  "schema_version": 1,
  "status": "success",
  "detector_id": "yolox-tiny",
  "model_sha256": "...",
  "image_sha256": "...",
  "width": 1024,
  "height": 1024,
  "sources": [],
  "thresholds": {},
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.91,
      "bbox_xyxy": [10, 20, 300, 500],
      "bbox_normalized_xyxy": [0.01, 0.02, 0.29, 0.49],
      "area_pixels": 139200,
      "area_fraction": 0.1328
    }
  ],
  "detection_count": 1,
  "class_counts": {"person": 1},
  "annotated_file": "...jpg"
}
```

Detector-specific raw tensors or preprocessing details may be included in namespaced fields, but comparison logic consumes only the normalized schema.

## 10. Comparison logic

### 10.1 Per-image agreement

For every canonical image:

- class-set intersection and union;
- class Jaccard similarity;
- total detection-count delta;
- YOLOX-only class list;
- NanoDet-only class list;
- both-empty, one-empty, or both-nonempty state;
- same-class box matches using deterministic descending-confidence greedy matching;
- match eligibility: same COCO class and IoU at least 0.50;
- matched-box count;
- unmatched YOLOX boxes;
- unmatched NanoDet boxes;
- mean and median IoU among matched boxes;
- matched confidence delta;
- maximum disagreement score.

These metrics are called **agreement metrics**, not accuracy metrics.

### 10.2 Disagreement score

Suggested normalized ranking score:

```text
0.35 × class-set disagreement
+ 0.25 × normalized count difference
+ 0.25 × unmatched-box fraction
+ 0.15 × (1 - mean matched IoU)
```

The exact formula and version must be stored in the comparison report.

### 10.3 Aggregate summaries

- total images compared;
- both-empty count;
- YOLOX-only nonempty count;
- NanoDet-only nonempty count;
- both-nonempty count;
- total detections by detector;
- per-class counts by detector;
- per-class count difference;
- per-class co-occurrence;
- matched/unmatched box totals;
- runtime and throughput comparison;
- top agreement and disagreement image lists;
- category and prompt breakdowns.

## 11. Comparison gallery design

### 11.1 Representative static previews

Create up to 20 versioned repository previews for Release Notes and the web UI.

Each preview is a three-column panel:

```text
Original | YOLOX-Tiny | NanoDet-Plus
```

Footer metadata:

- prompt ID;
- source category;
- image SHA prefix;
- detector counts;
- shared classes;
- detector-only classes;
- agreement score.

Selection policy:

1. strongest detector disagreement per category;
2. one-empty versus nonempty cases;
3. high box-count scenes;
4. strongest agreement examples;
5. fill remaining slots deterministically by disagreement score and SHA.

### 11.2 Full offline HTML gallery

Release asset:

```text
detector-comparison-gallery.zip
```

Contents:

```text
index.html
data.json
assets/
  originals/
  yolox/
  nanodet/
  tri-panel/
```

UI controls:

- search by prompt/category/SHA/class;
- filter by agreement state;
- select COCO class;
- minimum confidence per detector;
- sort by disagreement, matched IoU, counts, prompt or SHA;
- original/YOLOX/NanoDet/tri-panel view;
- toggle boxes and labels;
- keyboard next/previous;
- link to detector sidecars and containing ZIP assets.

## 12. Final combined Release assets

Expected namespaced assets:

```text
# YOLOX
 yolo[x]-coco-metadata.zip
 yolo[x]-coco-detections-part001.zip
 yolo[x]-coco-annotated-part001.zip
 yolo[x]-coco-offline-gallery.zip
 yolo[x]-coco-complete-part001.zip

# NanoDet
 nanodet-coco-metadata.zip
 nanodet-coco-detections-part001.zip
 nanodet-coco-annotated-part001.zip
 nanodet-coco-offline-gallery.zip
 nanodet-coco-complete-part001.zip

# Comparison
 detector-comparison-metadata.zip
 detector-comparison-gallery.zip
 detector-comparison-complete-part001.zip
```

Actual implementation should consistently use `yolox-` rather than retaining the historical `yolo-` prefix where migration allows. Every individual Release asset must remain below GitHub's per-file Release limit. Complete packages split deterministically before 1.75 GiB.

## 13. Release Notes

Release Notes sections:

1. source corpus and batch identity;
2. detector model locks and thresholds;
3. per-detector coverage and runtime;
4. aggregate agreement summary;
5. representative tri-panel previews;
6. top classes and detector count differences;
7. ZIP asset table;
8. interpretation limits.

Required disclaimer:

> These are observations from two COCO-pretrained detectors, not ground-truth labels or an accuracy benchmark. Agreement does not prove correctness, and disagreement does not identify which detector is correct.

## 14. Failure and recovery

### Inference workflows

- every canonical image must produce success or explicit failure sidecar;
- failure rate above policy threshold fails the workflow;
- artifact upload occurs only after coverage validation;
- failed workflow artifacts may be retained as short-lived diagnostics, but publisher rejects them.

### Publisher workflow

- creates the draft only after both artifacts pass validation;
- upload may resume the same batch draft after transient failure;
- final publication requires exact asset-name and checksum verification;
- index/history writeback occurs only after final publication;
- writeback uses fetch/rebase/push retry;
- publisher failure cannot affect Atlas or experiment Releases.

## 15. Security boundaries

A privileged `workflow_run` publisher must never consume arbitrary PR artifacts.

Publisher requirements:

- triggering workflows must exist on default branch;
- triggering repository must equal the current repository;
- accepted runs must target `main` or be owner-authorized `workflow_dispatch` runs;
- conclusion must be `success`;
- artifact extraction occurs under `${{ runner.temp }}`;
- reject absolute paths, `..`, symlinks and unexpected top-level members;
- validate manifest schema, detector ID, file size and SHA before use;
- never execute scripts from detector artifacts;
- publisher uses checked-in code from current `main`, not code from the artifact-producing run.

## 16. Resource planning

At the current 387 canonical images, both detector workflows are expected to finish comfortably within hosted-runner limits. Even a future 3,000-image corpus is compatible with independent single CPU jobs, provided measured throughput remains within the existing 350-minute design budget.

Inference remains full-corpus and from scratch on every invocation. Workflow artifacts are transport, not persistent state or inference caches.

## 17. Migration plan

### Phase 1 — shared schemas and NanoDet smoke

- add NanoDet model lock and export smoke test;
- add normalized detector sidecar schema tests;
- extract common corpus/package code from YOLO without changing current production Release.

### Phase 2 — artifact-only detector workflows

- add A and B;
- verify both artifacts on the complete corpus;
- keep current `media-yolo-*` workflow available during transition.

### Phase 3 — comparison publisher

- add C with explicit run-ID inputs;
- publish a draft combined Release;
- verify ZIPs, gallery, latest/history indexes and web entry.

### Phase 4 — production switch

- publish first `media-detection-all-*` Release;
- mark `media-yolo-*` as legacy single-detector history;
- disable direct Release publication in the old YOLO workflow;
- retain YOLO inference implementation as Workflow A;
- preserve Atlas unchanged.

### Phase 5 — optional automatic pairing

- add `workflow_run` pairing only after explicit-run mode is proven;
- retain manual run-ID publisher inputs as recovery path.

## 18. Acceptance criteria

- YOLOX and NanoDet workflows have no Release write permission requirement.
- Both detector artifacts describe exactly the same canonical SHA set.
- Publisher downloads exact run IDs, not "latest" artifacts.
- Publisher rejects any corpus/model/label/coverage mismatch.
- One combined `media-detection-all-*` Release contains namespaced YOLOX, NanoDet and comparison ZIPs.
- Full gallery works offline after extraction.
- Twenty or fewer representative tri-panel previews render from versioned repository paths.
- Comparison language never claims accuracy without ground truth.
- No Atlas workflow, Release, Notes, preview count, index or history is modified.
- Existing 15-image/all-eligible-video Atlas Release Notes contract remains covered by tests.
- All three workflows have deterministic package manifests and explicit recovery behavior.

<!-- NANODET:IMPLEMENTATION:START -->
## 18. Implementation status — 2026-07-21

The approved architecture is now implemented in the feature branch and is intentionally marked **`implemented_pending_production`** until the first full-corpus A/B run and combined Release are verified.

Implemented surfaces:

- `tools/nanodet_core.py`: official BGR/direct-resize preprocessing, 2,125 center priors, distribution-to-box decode, class-aware NMS, and original-image coordinate recovery;
- `object-detection/nanodet-model-lock.json`: official immutable pre-exported ONNX asset `nanodet-plus-m_320.onnx`, exact 4,793,615-byte size, SHA-256 `4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610`, input `[1,3,320,320]`, and output `[1,2125,112]`;
- `tools/build_detector_artifact.py`: shared complete-corpus-from-scratch artifact builder with normalized success/failure sidecars and deterministic ZIPs;
- separate read-only YOLOX and NanoDet inference workflows that publish workflow artifacts only;
- an exact-run publisher that validates `analysis_batch_id`, corpus fingerprint, quarantine digest, source Release order, canonical image SHA set, labels, thresholds, package hashes, ZIP CRC, and full sidecar coverage before publication;
- agreement/disagreement metrics, full-corpus offline Original | YOLOX-Tiny | NanoDet-Plus tri-panels, up to 20 versioned representative previews, comparison ZIPs, latest/history indexes, and Detector Lab;
- legacy `media-yolo-*` automation retired to explicit manual recovery; new production publications use `media-detection-*`.

### Model supply-chain decision

The alpha tag's legacy checkpoint exporter imports a removed `LightningLoggerBase` API. A reproducible bootstrap run proved that incompatibility before publication. The same official immutable Release provides a fixed-shape ONNX asset, so production uses that shorter supply chain instead of adding an obsolete PyTorch/Lightning environment. Every CI and production run downloads the official ONNX, checks exact size and SHA-256, creates an ONNX Runtime CPU session, and executes a real shape smoke.

### Promotion gate

The status changes from `implemented_pending_production` to `implemented` only after all of the following are recorded: successful YOLOX run ID, successful NanoDet run ID, publisher run ID, immutable `media-detection-all-*` Release, ZIP-only asset verification, detector index/writeback commit, live Detector Lab JSON/previews, and Atlas non-regression.
<!-- NANODET:IMPLEMENTATION:END -->
