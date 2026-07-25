# Detection Workflow Expansion — D1 Delivery Record

Status: `implemented_in_app_v1_detection_workflow_expansion`

Target application candidate: `studio-v1.0.0-rc.7`

## Scope

This document records the fourth hardware/runtime expansion priority from issue #53. D1 extends Detection Studio from resumable image-corpus inference into a durable mixed image/video workflow with structured exports, result review, presets and comparable performance evidence.

The implementation does not change the model-trust boundary. Every job still requires a Model Manager record with a local ONNX path, recorded SHA-256, declared adapter and fixed input dimensions. Provider selection continues to use the shared production planner, optional accelerator runtime verification and the resource-aware scheduler.

## Resumable video inference

A video source is identified by its canonical path and SHA-256. Each sampled frame is identified by:

`source path + source SHA-256 + zero-based frame index`

Completed sampled frames have an atomic JSON sidecar and a full-resolution annotated-frame cache entry. The job checkpoint records both paths. On resume, a frame is accepted only when:

1. the job fingerprint is unchanged;
2. the source SHA-256 is unchanged;
3. the frame sidecar still exists; and
4. the annotated-frame cache file still exists.

If any condition fails, that frame is inferred again. This avoids appending to partially encoded MP4 files and avoids treating an incomplete video container as durable inference evidence.

### Sampling policy

The effective frame interval is the stricter of:

- `sample_every_n_frames`; and
- the interval derived from `source FPS / sample_target_fps`.

Frame zero is always eligible. `max_sampled_frames = 0` means no sampled-frame limit. Sampling decisions depend only on source metadata and frame index, so restart behavior is deterministic.

## Annotated media

Sampled frames are rendered at source resolution. Final MP4 encoding is a separate deterministic pass:

- sampled frames use their verified annotated cache entries;
- unsampled frames remain unmodified;
- H.264/yuv420p is used for broad playback compatibility;
- the original audio stream is copied through a best-effort FFmpeg mux into AAC;
- if audio muxing is unavailable or fails, the verified silent video remains the output rather than discarding completed inference.

The manifest explicitly records `annotation_policy: sampled-frames-only` and whether audio was preserved.

## Crop and structured exports

Each detection may produce a JPEG crop under a class-specific directory. The crop path is linked from the same detection object used by all structured exports.

Every completed Detection job emits:

- `detection-manifest.json` schema 7;
- one atomic sidecar per image or sampled video frame;
- `detections.jsonl` with one complete item per line;
- UTF-8 CSV with one row per box and explicit rows for items with no boxes;
- COCO JSON containing images, categories, annotations and scores;
- `class-summary.json` with per-class counts;
- an annotated-media inventory;
- optional per-class crop files;
- optional annotated MP4 files.

No accuracy claim is inferred from these exports. `accuracy_claim` remains `null` unless an externally qualified evaluation is attached.

## Detection result and crop browser

The renderer does not parse arbitrary files directly. A closed typed preload bridge sends a bounded request to the main process. The main process:

1. resolves and reads the selected manifest;
2. normalizes schema 7 items into a fixed browser contract;
3. applies path/item/class text search;
4. applies exact class and minimum-confidence filters;
5. paginates to at most 200 items per response; and
6. exposes only recorded evidence paths for explicit reveal actions.

The browser shows source type, frame index, timestamp, box count, classes, confidence, area fraction, annotated-media evidence and crop evidence without rerunning inference.

## Benchmark matrix

A benchmark suite is represented as independent durable jobs for every selected model × provider pair. This is deliberate:

- each provider/device gets an independent resource reservation;
- accelerator concurrency and memory budgets remain enforceable;
- one failed pair does not discard successful pairs;
- pause, resume, cancellation and interrupted recovery use the ordinary Job Center lifecycle;
- every pair has its own immutable output directory and manifest.

Benchmark mode clears the in-process Detection session cache before measuring the cold path. It then records:

- fresh-session initialization plus first inference;
- first-inference duration;
- estimated session initialization duration;
- steady-state iteration count and input sample count;
- median, p95, minimum and maximum latency;
- median-derived throughput;
- execution-provider and fallback evidence;
- model SHA-256 and adapter identity.

Cold and steady-state numbers are not combined into one average.

## Presets and project defaults

Detection presets are local JSON preferences stored outside project media. A preset contains:

- model and provider selections;
- benchmark model/provider selections;
- device, fallback and CoreML compute-unit policy;
- thresholds and maximum detections;
- video sampling policy;
- crop and annotated-video output policy;
- benchmark sample and steady-iteration counts.

Writes use temporary-file replacement. One preset may be selected as the default. Presets do not contain media, model bytes, credentials or detection outputs.

## Acceptance evidence

The D1 tranche is accepted only when the pull-request head passes:

- TypeScript and Vue typecheck;
- Vitest coverage, including preset and result-browser behavior;
- Python engine tests, including deterministic sampling and export contracts;
- frozen-engine build and persistent protocol smoke;
- packaged application launch on Windows, Linux and macOS;
- provider qualification and four-platform install lifecycle gates;
- four-platform Studio release dry-run.

The release candidate does not replace the external stable evidence in issue #49. Real DirectML/CUDA assigned-node evidence, production signing/notarization, production accelerator-bundle signing, redistribution approval, corpus rights, large-scale performance and final operator acceptance remain separate gates.
