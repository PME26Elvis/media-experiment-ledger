# Hardware Feasibility Audit and Functional Expansion Plan

Status: `software_path_hardened_external_hardware_evidence_pending`

This document answers two separate questions:

1. whether the hardware-dependent implementation follows established ONNX Runtime and desktop-application patterns closely enough to be expected to work on correctly configured hardware; and
2. what product capabilities should be added after the current release-candidate line.

It does **not** replace real-device evidence. It records whether the software architecture, provider configuration, packaging path, fallback policy and operational boundaries are technically coherent before hardware is attached.

## Executive conclusion

The current CPU, DirectML and CoreML designs are structurally sound and follow mainstream ONNX Runtime patterns. CUDA is structurally sound at the inference layer, but must remain an optional runtime/package profile rather than an implied capability of the ordinary Linux build. The application now uses one shared provider-planning implementation for production inference and qualification, eliminating the previous risk that CI tested different CoreML options from the shipped path.

The remaining risks are primarily operational rather than algorithmic:

- selecting among multiple devices;
- limiting concurrent sessions against finite VRAM;
- warming and caching compiled provider artifacts;
- matching model/operator support to a provider before a long job starts;
- distributing optional CUDA libraries without making the normal package unnecessarily large;
- collecting evidence from the exact packaged executable on representative hardware.

## Mainstream implementation comparison

| Concern | Media Experiment Ledger Studio | Established pattern | Assessment |
|---|---|---|---|
| Provider discovery | Uses `onnxruntime.get_available_providers()` and exposes the packaged inventory through typed IPC | ONNX Runtime and projects such as Immich discover available providers at runtime | Aligned |
| Provider order | Accelerator first, optional CPU second | Microsoft examples use `CUDAExecutionProvider` before `CPUExecutionProvider`; Immich builds an ordered supported-provider list | Aligned after this audit |
| Strict execution | Can omit CPU and sets `session.disable_cpu_ep_fallback=1` | Explicit fail-closed mode is preferable when a user asks for accelerator-only execution | Aligned after this audit |
| DirectML session constraints | Disables memory patterns and forces sequential execution | Required by the ONNX Runtime DirectML provider documentation | Aligned |
| DirectML concurrency | Every durable job launches a separate engine process and therefore a separate ORT session | DirectML forbids concurrent `Run` calls on one session but permits separate sessions | Structurally safe; VRAM admission control still needed |
| CoreML options | Uses MLProgram, all compute units, dynamic-shape allowance and a persistent model cache | ONNX Runtime CoreML documents the same provider options; Immich also uses MLProgram and a model cache | Aligned after this audit |
| CUDA options | Uses an explicit device ID, requested-size arena growth and the default copy stream | Common ONNX Runtime CUDA provider options | Aligned at inference level |
| Runtime libraries | Windows ships `onnxruntime-directml`; normal Linux/macOS builds ship CPU/CoreML-capable `onnxruntime`; CUDA is installed only in its hardware profile | Mature projects commonly use separate accelerated images or runtime profiles | Correct boundary |
| Frozen Python engine | PyInstaller `onedir`, `--collect-all onnxruntime`, copied distribution metadata and a packaged inventory smoke | PyInstaller hooks collect ONNX Runtime provider plugins; frozen engines commonly keep native libraries outside ASAR | Aligned |
| Model integrity | Hash-pinned imports, adjacent manifest validation and immutable model records | Standard supply-chain pattern for user-supplied model artifacts | Strong |
| Execution evidence | CPU comparison, finite-output check, tolerance check and ORT profiling node counts | Stronger than merely checking that a provider name is present | Strong |

Primary references:

- ONNX Runtime execution providers: <https://onnxruntime.ai/docs/execution-providers/>
- ONNX Runtime DirectML provider: <https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html>
- ONNX Runtime CoreML provider: <https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html>
- ONNX Runtime CUDA provider: <https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html>
- ONNX Runtime Python install variants: <https://onnxruntime.ai/docs/install/>
- Microsoft ONNX Runtime examples: <https://github.com/microsoft/onnxruntime-inference-examples>
- Immich ORT session implementation: <https://github.com/immich-app/immich/blob/main/machine-learning/immich_ml/sessions/ort.py>
- PyInstaller ONNX Runtime hooks: <https://github.com/pyinstaller/pyinstaller-hooks-contrib>

## Provider-by-provider verdict

### CPU

Verdict: **implementation-proven**.

The CPU package is the universal baseline, is built into every supported platform engine, and runs the complete production detector path in hosted CI. It remains the recovery path when an accelerator is unavailable and the user explicitly permits fallback.

### DirectML

Verdict: **software design expected to work; real Windows GPU evidence still required**.

Reasons for confidence:

- the Windows engine installs and freezes `onnxruntime-directml`;
- provider inventory verifies that `DmlExecutionProvider` exists in the packaged engine;
- production and qualification both disable memory patterns and use sequential execution;
- each application job owns a separate child process/session;
- accelerator-first and optional CPU-second ordering is explicit;
- strict mode disables implicit CPU execution;
- model output is compared with CPU and provider-assigned nodes are counted when hardware is available.

Remaining DirectML work:

- enumerate DX12-capable adapters and expose device selection;
- measure VRAM and cap concurrent sessions;
- test integrated and discrete GPUs, including low-memory devices;
- record driver, adapter and feature-level information in support bundles;
- consider a future Windows ML migration study because DirectML is in sustained engineering rather than active feature expansion.

### CoreML

Verdict: **implementation-proven on hosted Apple Silicon and Intel macOS runners, with production-path parity restored**.

The previous qualification script used CoreML provider options that production inference did not. This audit moved those options into the shared provider planner. Production and qualification now use the same MLProgram, compute-unit, dynamic-shape and model-cache configuration. Profiling evidence has already shown real CoreML graph-node assignment on both required macOS architectures.

Remaining CoreML work:

- expose CPU-only, CPU+GPU and ALL compute-unit preferences;
- measure first-run compilation separately from warm-cache inference;
- monitor cache size and provide a safe cache-reset action;
- add Neural Engine-oriented representative devices to manual evidence.

### CUDA

Verdict: **inference design expected to work in a CUDA runtime profile; not a capability of the ordinary Linux package**.

The shared planner now supplies an explicit device ID and conservative stream/arena options. The opt-in self-hosted CUDA workflow installs the GPU runtime, runs unit tests, builds the PyInstaller engine, verifies that the frozen manifest exposes CUDA, and then requires real CUDA-assigned nodes against the CPU baseline.

The ordinary Linux AppImage and `.deb` intentionally remain CPU packages. A production CUDA claim requires one of these explicit distribution choices:

1. an optional CUDA engine bundle downloaded by Model Manager;
2. a separate CUDA-labelled desktop package; or
3. a documented system-runtime profile for advanced users.

The preferred product direction is an optional signed engine bundle, because it avoids adding hundreds of megabytes to every Linux download and permits independent CUDA/cuDNN compatibility updates.

## Changes made by this audit

- introduced one shared provider planner for production and qualification;
- added ordered accelerator-to-CPU fallback and a strict fail-closed mode;
- moved CoreML provider options and cache configuration into the production path;
- added CUDA device/options handling and optional pip-vendor DLL preload support;
- exposed CPU fallback policy in Detection Studio;
- upgraded CUDA hardware CI to build and inventory the frozen engine before accepting execution evidence;
- corrected the large-corpus benchmark workflow to use the current `app-main` branch;
- expanded provider policy tests.

## Known limitations that should not be hidden

1. Provider availability does not prove that every operator in every user model is supported.
2. `session.get_providers()` reports registered providers, not the exact provider used by every node; profiling remains the evidence source.
3. Multiple engine processes are isolation-friendly but can oversubscribe VRAM without an admission controller.
4. The current hardware qualifier uses the pinned YOLOX-Tiny graph; NanoDet and custom-model compatibility still need matrix coverage.
5. CUDA library redistribution and driver compatibility need a separate signed runtime-bundle policy.
6. Performance results from hosted runners are not representative hardware benchmarks.

# Functional expansion roadmap

## Phase H1 — Hardware Runtime Center

Goal: turn provider support from a settings dropdown into a diagnosable runtime subsystem.

Features:

- device discovery with adapter name, vendor, memory, driver/runtime and provider support;
- one-click provider self-test using a tiny bundled or generated ONNX graph;
- cold-start, warm-start, throughput and memory measurements;
- recommended provider selection per model and machine;
- explicit CPU fallback policy, device ID and compute-unit controls;
- provider cache inspection and safe cleanup;
- exportable non-secret hardware evidence bundle.

Acceptance:

- unavailable devices are never selectable;
- a selected device can be self-tested before a corpus job;
- evidence distinguishes provider registration, session creation and actual assigned nodes;
- failures include actionable remediation rather than a raw ORT exception.

## Phase H2 — Resource-aware Job Scheduler

Goal: prevent otherwise-correct hardware code from producing poor desktop behavior.

Features:

- provider/device-specific concurrency limits;
- configurable VRAM safety reserve;
- model warm-session pool with idle eviction;
- CPU thread limits and process priority controls;
- automatic queueing when estimated memory exceeds budget;
- out-of-memory classification with lower-resolution/CPU retry suggestions;
- thermal and sustained-throughput observation where the OS exposes it.

Acceptance:

- two heavy GPU jobs do not start simultaneously when the declared budget cannot fit them;
- pause/cancel releases the child process and its accelerator memory;
- the UI explains why a job is queued and which resource is blocking it.

## Phase H3 — Optional Accelerator Engine Bundles

Goal: add CUDA and future providers without bloating the universal application.

Features:

- signed, hash-pinned engine bundle manifests;
- CPU, DirectML, CoreML and CUDA runtime profiles;
- compatibility constraints for OS, architecture, ORT, CUDA and cuDNN;
- atomic install, rollback and quarantine;
- independent runtime updates from the Electron shell;
- license, SBOM and native-library inventory per bundle.

Acceptance:

- the base app remains usable with CPU only;
- an incompatible bundle is rejected before installation;
- switching bundles never mutates user models or project data;
- every bundle passes the same protocol and detector golden tests.

## Phase D1 — Detection Workflow Expansion

Goal: make Detection Studio useful beyond a one-off image-directory run.

Features:

- video detection with configurable sampling and annotated video export;
- side-by-side multi-model and multi-provider benchmark runs;
- per-class filters, confidence histograms and confusion/disagreement review;
- searchable detection browser with crops and source navigation;
- COCO JSON, JSONL, CSV and annotated-media export;
- model warm-up and batch-size controls;
- saved detection presets and project-level defaults.

Acceptance:

- image and video jobs are resumable and deterministic under the same manifest;
- benchmark results separate cold compilation from steady-state inference;
- exports retain source/model/provider hashes and never imply ground-truth accuracy without labels.

## Phase D2 — Atlas and Detection Fusion

Goal: use detector output as experimental evidence rather than an isolated feature.

Features:

- class-count and spatial-layout dimensions in Atlas cohorts;
- prompt-to-object consistency reports;
- YOLOX/NanoDet/custom-model disagreement triage;
- representative samples chosen by semantic diversity, not only time quantiles;
- quality gates that can flag empty, corrupt or unexpected generated outputs;
- report blocks that embed detection evidence and provider metadata.

Acceptance:

- every derived chart links back to immutable source media and detection sidecars;
- disagreement is labelled as model disagreement, not accuracy;
- reports remain rebuildable from manifests without hidden UI state.

## Phase A1 — Automation Quality Policies

Goal: connect generation, validation and analysis into one durable pipeline.

Features:

- post-generation image/video technical validation;
- optional detector-based expected/forbidden object rules;
- automatic retry, quarantine or human-review routing;
- provider-aware local post-processing after cloud generation;
- budget-aware stop conditions based on valid outputs rather than API success alone;
- reusable policy templates per experiment.

Acceptance:

- policy decisions are recorded with inputs, thresholds and evidence;
- retries remain bounded and idempotent;
- no generated item is silently deleted because it failed a quality rule.

## Phase P1 — Additional Provider Research

Candidates, not v1 promises:

- OpenVINO for Intel CPU/iGPU/NPU;
- TensorRT for specialized NVIDIA deployments;
- ROCm/MIGraphX for supported AMD Linux systems;
- Windows ML as the long-term Windows execution-provider abstraction;
- remote worker protocol for a dedicated inference machine.

Each candidate must first implement the provider planner contract, frozen-engine inventory, deterministic CPU comparison, node-assignment evidence, license review and resource scheduler integration.

## Recommended delivery order

1. Merge the shared provider-path hardening from this audit.
2. Implement Hardware Runtime Center diagnostics and self-test.
3. Add resource-aware scheduling before enabling broad GPU concurrency.
4. Build optional signed CUDA engine bundles.
5. Add video detection and benchmark UX.
6. Fuse detection evidence into Atlas and automation policies.
7. Evaluate additional providers only after the common runtime contract is stable.
