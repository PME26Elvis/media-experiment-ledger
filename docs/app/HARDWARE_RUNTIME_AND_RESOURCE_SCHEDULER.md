# Hardware Runtime Center and Resource-aware Scheduler

Status: `H1_IMPLEMENTED_RC4_PUBLISHED__H2_IMPLEMENTED_RC5_QUALIFICATION_PENDING`

This document records the delivered implementation behind roadmap phases H1 and H2. It complements the stable external-evidence checklist in issue #49; it does not claim uncollected DirectML or CUDA real-device evidence.

## H1 — Hardware Runtime Center

Released as `studio-v1.0.0-rc.4`.

The Hardware Runtime Center combines two views that must not be confused:

1. Electron/Chromium host evidence: adapters, active device, vendor/device IDs, driver metadata, feature status, CPU and host memory;
2. the exact packaged Python engine inventory: ONNX Runtime version, registered execution providers and installed runtime distributions.

A provider self-test generates a tiny ONNX Identity graph locally and runs it through the same provider planner used by Detection Studio. Evidence separates:

- runtime registration;
- session creation;
- profiling-based provider-assigned nodes;
- CPU-assigned nodes and fallback;
- cold session creation;
- cold inference;
- warm inference average;
- provider cache state.

Provider, device ID, CPU fallback and CoreML compute-unit preferences are persisted. Detection Studio consumes and records the same policy. Users may clear provider caches and export a redacted JSON evidence bundle with SHA-256; media, credentials and project configuration are excluded.

## H2 — Resource-aware Job Scheduler

Target release: `studio-v1.0.0-rc.5`.

### Admission model

Every queued job is converted to a resource request before an engine process is created.

CPU jobs reserve a CPU concurrency slot. Accelerator jobs reserve a provider/device key such as `directml:0`, `cuda:0` or `coreml:0`, with:

- a maximum concurrent-job count;
- a declared memory budget;
- a safety reserve that is never admitted to jobs;
- current reserved memory;
- available admission memory.

The default policy is deliberately conservative:

- CPU concurrent jobs: 2;
- accelerator concurrent jobs per device: 1;
- declared accelerator budget: 4096 MB;
- safety reserve: 512 MB;
- warm Detection worker idle lifetime: 90 seconds.

These are scheduling policies, not claims of exact free VRAM. Platforms do not expose a uniform trustworthy free-VRAM API. Users can override the default per provider/device after consulting Hardware Runtime Center evidence.

### Memory estimation

Detection memory estimates are deterministic and manifest-derived:

- explicit `estimated_vram_mb` takes precedence;
- otherwise input width, input height and batch size determine a conservative estimate;
- non-Detection accelerator operations use documented safe defaults.

A job whose estimate does not fit after the safety reserve remains queued. Its stage and scheduler snapshot explain the required estimate, available budget and blocking limit.

### Queue and lifecycle correctness

Queued pause and cancel complete immediately without entering phantom `pausing` or `cancelling` states. Running pause/cancel aborts the engine process. Reservations are released in `finally` paths for success, failure, abort and interrupted recovery. Queue admission is re-evaluated after every release and policy update.

Application shutdown marks active work recoverable, destroys warm workers and aborts active child processes. Durable checkpoints remain the source of truth for resume.

### Warm Detection workers

Detection uses a bounded persistent engine protocol:

- Node launches a sequential Python worker keyed by model hash, provider, device, CoreML units, fallback policy and credential environment fingerprint;
- Python accepts multiple JSON-line requests without restarting;
- compatible ONNX Runtime sessions are cached with a maximum of two sessions per worker process;
- workers are reused only while idle and compatible;
- configured idle eviction terminates the process and releases runtime/GPU state;
- abort destroys the worker rather than returning it to the pool.

Other job types keep the existing one-process-per-job isolation model.

### Out-of-memory recovery

Errors are classified into accelerator or host memory exhaustion. Stored job guidance recommends the relevant recovery path:

- reduce model input size or batch;
- reduce device concurrency or declared simultaneous load;
- enable or select CPU fallback;
- reduce general corpus parallelism and close host-memory-heavy applications.

The original engine error remains attached to the actionable explanation.

## UI evidence

Hardware Runtime Center shows:

- active resource reservations;
- per-resource concurrency and memory admission state;
- queued jobs with exact block reasons and estimates;
- current warm workers and busy/idle state;
- editable default and per-device policies.

Job Center displays the scheduler stage directly and permits pausing queued jobs.

## Automated acceptance

The release candidate must pass:

- TypeScript typecheck;
- JavaScript/Vue tests;
- Python engine tests;
- resource estimation, reservation, safety-reserve and OOM tests;
- persistent protocol and session-reuse tests;
- frozen engine build and inventory;
- packaged renderer smoke on Windows, Linux and macOS;
- provider qualification including hosted CoreML execution evidence;
- Windows, Linux, macOS arm64 and macOS Intel install/upgrade/remove lifecycle;
- four-platform release-request dry-run.

## Remaining external evidence

H1/H2 completion does not close:

- representative DirectML and CUDA physical-device execution;
- exact driver/device benchmark matrices;
- code signing/notarization/update signatures;
- large licensed corpus benchmarks;
- stable 1.0.0 release approval.

Those remain tracked by issue #49 rather than being hidden behind the scheduler implementation.
