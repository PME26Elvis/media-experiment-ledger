# Multi-detector YOLOX + NanoDet pipeline specification

> Status: **`implemented`**  
> Decision: separate detector inference workflows, one exact-run aggregate publisher workflow, one combined detector Release family  
> Atlas impact: **none**

## 1. Purpose and interpretation boundary

The repository runs YOLOX-Tiny and NanoDet-Plus-m-320 independently over the same complete canonical image corpus, then publishes one validated comparison product. The generated media has no human-verified COCO ground truth, so this product reports **agreement, disagreement, coverage, box overlap, confidence, class distribution, and runtime**. It must never present repository observations as model accuracy, precision, recall, or mAP.

Required disclaimer:

> These are observations from two COCO-pretrained detectors, not ground-truth labels or an accuracy benchmark. Agreement does not prove correctness, and disagreement does not identify which detector is correct.

Videos are outside this detector corpus. They remain part of general Analytics and the image/video Prompt Repeatability Atlas.

## 2. Canonical source corpus

Every invocation rebuilds the image inventory from all published, non-draft `media-exp-*` Releases after applying `config/release-quarantine.json`.

The inventory process must:

- download formal manifests, standalone `run_*-outputs.jsonl`, and `run_*-images*.zip` assets;
- reject unsafe ZIP paths and unsupported members;
- verify Release asset integrity, manifest records, member hashes, image decode, dimensions, and byte size;
- exclude quarantined runs;
- deduplicate byte-identical images by SHA-256 while preserving every source Release, run, prompt, category, model, and timestamp alias;
- produce an immutable corpus fingerprint and ordered canonical SHA set;
- start from scratch on every workflow run, with no hidden incremental state, cross-run inference cache, or published-result reuse.

## 3. Implemented workflow topology

### 3.1 Workflow A — YOLOX-Tiny inference

```text
.github/workflows/detector-yolox-inference.yml
```

The workflow:

- is **workflow_dispatch only**; repository pushes never launch a full-corpus inference run;
- rebuilds the complete canonical image corpus;
- downloads and verifies the SHA-pinned YOLOX-Tiny ONNX model and COCO 80 labels;
- runs real ONNX Runtime CPU inference;
- emits one normalized success or explicit failure sidecar for every canonical image;
- renders annotated images and explicit empty-detection evidence;
- builds deterministic namespaced ZIP packages and an offline gallery;
- uploads exactly one short-lived `detector-yolox-<analysis_batch_id>` workflow artifact;
- has read-only repository contents permission and never creates a Release or writes indexes.

### 3.2 Workflow B — NanoDet-Plus inference

```text
.github/workflows/detector-nanodet-inference.yml
```

The workflow mirrors Workflow A and is also **workflow_dispatch only**, while using NanoDet-Plus-m-320. The production model is the **official immutable pre-exported ONNX** asset from the pinned upstream Release. Its byte size, SHA-256, labels hash, input shape, strides, and `reg_max` are fixed in `object-detection/nanodet-model-lock.json`; a real ONNX Runtime shape smoke runs before full-corpus inference.

The artifact name is:

```text
detector-nanodet-<analysis_batch_id>
```

### 3.3 Workflow C — validate, compare, and publish

```text
.github/workflows/detector-comparison-publish.yml
```

The publisher is intentionally **workflow_dispatch only** and accepts the two explicit successful detector workflow run IDs. It does not infer a pair from generic latest runs or depend on a chained `workflow_run` event.

The publisher:

- accepts explicit YOLOX and NanoDet workflow run IDs as the deterministic production and recovery interface;
- verifies that each run belongs to this repository, used trusted `main`, completed successfully, and came from the expected detector workflow ID;
- requires exactly one unexpired detector artifact from each run and requires the artifact batch IDs to match;
- refuses already-published batches before downloading the large transport artifacts;
- downloads both artifacts with `actions/download-artifact@v5`, exact `run-id`, and `github-token`;
- validates both completion manifests and every packaged file hash before comparison;
- creates comparison JSON, representative tri-panels, an offline HTML gallery, and deterministic ZIP assets;
- publishes one immutable `media-detection-all-<latest-experiment-date>-vN` Release;
- updates independent detector latest/history indexes and versioned Detector Lab previews on `main` using fetch/rebase/push retries;
- never changes Atlas workflows, Releases, previews, indexes, history, Notes, or success state.

## 4. Trigger and refresh policy

### 4.1 Manual inference and recovery

Operators may manually dispatch A and B using the same `analysis_batch_id`. After both succeed, dispatch Workflow C with those two **exact run IDs**. This is also the recovery route for a promotion whose detector publication step was interrupted after inference completed.

The publisher never pairs independently selected generic latest detector runs. **"Latest successful YOLO" plus "latest successful NanoDet" is forbidden.**

### 4.2 Promotion exact-run orchestration

A non-dry-run **Promote input snapshot** Action that creates at least one new formal Release owns the automatic A → B → C handoff:

1. create one immutable `promotion-<promotion-workflow-run-id>` batch ID;
2. dispatch YOLOX-Tiny and NanoDet-Plus with that same batch;
3. capture the exact workflow run ID returned by each dispatch;
4. wait for the exact YOLOX run to succeed;
5. wait for the exact NanoDet run to succeed;
6. dispatch Workflow C with those two exact run IDs and `publish_release=true`;
7. wait for the exact publisher run to finish successfully.

In other words, Promotion **waits for both detector runs** and explicitly hands their IDs to the publisher. It does not rely on a chained `workflow_run` event, which is not a reliable orchestration boundary for workflows dispatched from another workflow through the repository `GITHUB_TOKEN`.

If either detector fails, no publisher is dispatched. If the publisher fails, the promotion fails visibly while the successful detector artifacts remain available for the exact-run recovery path during their retention window.

### 4.3 Expensive-trigger safety

Both full-corpus inference workflows are manual-dispatch workflows only. They have no `push` trigger. This prevents workflow, documentation, or source-code merges from accidentally reprocessing thousands of images.

The comparison publisher is also explicit-run `workflow_dispatch` only. Automatic publication is achieved by Promotion calling it after both exact inference runs succeed, not by hidden same-head discovery.

### 4.4 Input promotion integration

A non-dry-run **Promote input snapshot** Action:

1. reconstructs and promotes the input archive;
2. counts newly created formal `media-exp-*` Releases from the publisher output;
3. refreshes Analytics and the full Experiment Release Audit;
4. when and only when at least one new formal Release was created, performs the exact-run detector orchestration in §4.2.

A repeated no-op promotion does not rerun detector inference. Direct CLI publishing or CLI promotion still creates formal Releases, triggers release-based Analytics, and dispatches Atlas, but it does not additionally dispatch the Audit or detector workflows.

## 5. Batch and artifact identity

Every detector manifest includes at least:

```json
{
  "schema_version": 1,
  "analysis_batch_id": "detection-or-promotion-...",
  "detector_id": "yolox-tiny",
  "workflow_run_id": 123456789,
  "head_sha": "...",
  "corpus_fingerprint": "...",
  "quarantine_policy_digest": "...",
  "source_release_tags": ["media-exp-..."],
  "date_from": "YYYY-MM-DD",
  "date_to": "YYYY-MM-DD",
  "canonical_image_count": 893,
  "successful_image_count": 893,
  "failed_image_count": 0,
  "labels_sha256": "...",
  "model_sha256": "...",
  "thresholds": {
    "confidence": 0.25,
    "nms_iou": 0.45,
    "max_detections": 100
  },
  "package_files": []
}
```

The example count is illustrative of a corpus snapshot, not a fixed contract value.

The publisher requires:

- exact `analysis_batch_id` match;
- exact corpus fingerprint and quarantine-policy digest match;
- identical ordered source Release tags;
- identical canonical image SHA set;
- identical COCO labels hash and compatible thresholds;
- distinct expected detector IDs;
- complete sidecar coverage and policy-compliant failures;
- every artifact file name, size, and SHA-256 to match its manifest.

Any mismatch fails closed and creates no Release.

## 6. Security boundary

The privileged publisher must never consume arbitrary PR artifacts or execute content from detector artifacts.

It must:

- accept only explicit run IDs supplied through its trusted `workflow_dispatch` interface;
- checkout publisher code from current trusted `main`;
- reject runs from another repository, untrusted branch, unexpected workflow, or unsuccessful conclusion;
- require both artifact batch IDs to match before downloading large payloads;
- extract only under `${{ runner.temp }}`;
- reject absolute paths, `..`, symlinks, unexpected top-level members, and hash mismatches;
- validate schemas before reading comparison data;
- use fixed concurrency with `cancel-in-progress: false`;
- prevent duplicate publication for the same batch.

## 7. Model supply chain

### YOLOX-Tiny

- model family and immutable download are pinned in `object-detection/model-lock.json`;
- labels are pinned in `object-detection/coco-80.json`;
- CI verifies model size, SHA-256, labels, ONNX Runtime session creation, and real output tensor shape.

### NanoDet-Plus-m-320

- upstream model: NanoDet-Plus-m-320 / ShuffleNetV2 1.0x / 320 × 320 / COCO 80 / Apache-2.0;
- immutable ONNX details are pinned in `object-detection/nanodet-model-lock.json`;
- CI verifies expected size, SHA-256, labels hash, input/output shape, and real ONNX Runtime execution;
- upstream COCO benchmark numbers are descriptive model metadata only and are never claimed as results on this generated corpus.

## 8. Normalized sidecar contract

Both adapters emit the same comparison-facing schema:

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

Detector-specific preprocessing evidence may appear in namespaced fields, but comparison code consumes the normalized contract.

## 9. Comparison metrics

For each canonical image, the comparison records:

- class-set intersection, union, and Jaccard similarity;
- total detection-count delta;
- YOLOX-only and NanoDet-only classes;
- both-empty, one-empty, or both-nonempty state;
- deterministic same-class greedy box matching at IoU ≥ 0.50;
- matched and unmatched box counts;
- mean/median matched IoU and confidence delta;
- a versioned normalized disagreement score.

Aggregate output includes corpus coverage, detector failure counts, detections by class, co-occurrence and class deltas, matched/unmatched totals, runtime/throughput, and top agreement/disagreement cases. These remain agreement observations, not accuracy metrics.

## 10. Galleries and Release assets

Representative previews use:

```text
Original | YOLOX-Tiny | NanoDet-Plus
```

Up to 20 versioned tri-panels are selected deterministically across categories, one-empty cases, high-density scenes, strong agreement, and strong disagreement.

Final Release assets are ZIP-only and namespaced:

```text
# YOLOX
  yolox-coco-metadata.zip
  yolox-coco-detections-part*.zip
  yolox-coco-annotated-part*.zip
  yolox-coco-offline-gallery.zip
  yolox-coco-complete-part*.zip

# NanoDet
  nanodet-coco-metadata.zip
  nanodet-coco-detections-part*.zip
  nanodet-coco-annotated-part*.zip
  nanodet-coco-offline-gallery.zip
  nanodet-coco-complete-part*.zip

# Comparison
  detector-comparison-metadata.zip
  detector-comparison-gallery.zip
  detector-comparison-complete-part*.zip
```

Complete packages split deterministically before 1.75 GiB. The offline gallery supports prompt/category/SHA/class search, agreement filters, sorting, and Original/YOLOX/NanoDet/tri-panel views.

## 11. Failure and recovery

### Inference workflows

- every canonical image produces a success or explicit failure sidecar;
- coverage and failure policy are validated before artifact upload;
- failed artifacts may be retained only as short-lived diagnostics and are rejected by the publisher.

### Publisher

- no Release is created until both exact run artifacts pass the complete pair contract;
- an interrupted draft may be resumed only for the same verified batch;
- an already-published batch exits before downloading the two large transport artifacts;
- final publication requires exact asset-list and checksum verification;
- index/history writeback happens only after final publication;
- failures cannot affect experiment Releases or Atlas products.

If automatic Promotion orchestration is interrupted after both inference runs succeeded, manually dispatch Workflow C with those exact run IDs. Re-running the two expensive inference jobs is unnecessary while their artifacts are still retained.

## 12. Resource policy

Both detectors use complete GitHub-hosted CPU jobs with a 350-minute timeout. The implementation is designed for several thousand canonical images, but every larger corpus must be judged by measured end-to-end workflow evidence rather than extrapolated inference-only speed.

Workflow artifacts are transport, not persistent state. Re-running the pipeline repeats corpus acquisition, verification, inference, packaging, and publication validation from scratch. Promotion therefore records and reuses the exact run IDs produced in that invocation rather than searching for a convenient recent run.

## 13. Acceptance criteria

- A and B are `workflow_dispatch` only, have read-only repository permissions, and publish no Releases.
- Both artifacts describe the exact same canonical SHA set and batch identity.
- Workflow C is `workflow_dispatch` only and requires exact successful YOLOX and NanoDet run IDs.
- Promotion captures the exact A/B run IDs, waits for both, dispatches C with that pair, and waits for C.
- Repeated no-op Promotion does not run A/B/C.
- Any corpus/model/label/coverage/hash mismatch fails closed.
- One combined `media-detection-all-*` Release contains YOLOX, NanoDet, and comparison ZIPs.
- Full gallery works offline; representative previews remain versioned repository files.
- Comparison language never claims accuracy without ground truth.
- No Atlas workflow, Release, Notes, preview, index, history, or finalizer is modified.
- All workflows retain deterministic manifests and explicit recovery behavior.

<!-- NANODET:IMPLEMENTATION:START -->
## 14. Production implementation status — verified 2026-07-21

Status is **`implemented`**. The first production corpus was processed by YOLOX-Tiny run `29812888677` and NanoDet-Plus run `29812888709`. Publisher run `29813188073` verified the exact run IDs and created immutable ZIP-only Release [`media-detection-all-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-detection-all-2026-07-13-v1).

Permanent baseline evidence:

- canonical images: **387**, zero detector failures;
- YOLOX detections: **1,533**; NanoDet detections: **3,243**;
- matched same-class boxes at IoU ≥ 0.50: **902**;
- mean disagreement score: **0.557421**;
- full-corpus offline tri-panels plus **20** versioned representative previews;
- Detector Lab and deployed JSON verified live;
- detector writeback commit `9bef82a565ac25db97708628acfe8f56e1cc3b29` preserved the exact Atlas index blob SHA `3778183686ca7603e3c6d49013ff643182445cec`.

The official NanoDet ONNX remains pinned at SHA-256 `4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610`. These are detector agreement/disagreement observations, not ground-truth labels or an accuracy benchmark. Full evidence: [`docs/reports/NANODET_PRODUCTION_EVIDENCE.md`](reports/NANODET_PRODUCTION_EVIDENCE.md).

This section is an immutable first-production evidence snapshot. New detector publications update `data/detection/latest.json`, `data/detection/history.json`, and the web index; they do not rewrite the baseline above.
<!-- NANODET:IMPLEMENTATION:END -->
