# Media Experiment Ledger Studio

> Product line branch: `app-main`  
> Public identity: **Media Experiment Ledger Studio**  
> Product descriptor: **Atlas · Detection · Media Automation**  
> Current phase: **implementation merged; release qualification pending**  
> Implementation status: **merged to `app-main`**  
> Contract baseline: **2026-07-23.1**  
> Primary specification index: [`docs/app/README.md`](docs/app/README.md)

## Current implementation evidence

The executable desktop implementation was merged through [PR #30](https://github.com/PME26Elvis/media-experiment-ledger/pull/30) using a normal merge commit.

- Merge commit: `9838b1c5e56d9523087f9739deebd1804746f0d8`
- Validated implementation head: `447ed656375c6fe934953a0991f2bf4fbcd88122`
- Desktop App CI run: `29972465923`
- Validated runners: Windows, macOS and Ubuntu
- Verified chain: locked install, dependency audit, TypeScript/Vue tests, Python tests, self-contained PyInstaller engine, Electron production build, unpacked package, packaged application launch and evidence upload
- Evidence artifacts: `app-build-evidence-windows-latest`, `app-build-evidence-macos-latest`, `app-build-evidence-ubuntu-latest`

The implementation branch `app-v1-implementation` is retained after merge in accordance with repository policy.

## Release qualification status

The merged application is executable and cross-platform packaged-launch verified. A signed stable `1.0.0` release remains blocked until operator-controlled evidence is available:

- Windows signing certificate;
- Apple Developer ID signing and notarization credentials;
- GPG and Ed25519 release-signing keys;
- real DirectML, CUDA and CoreML hardware runs;
- Full Research corpus redistribution and privacy attestations;
- final manual benchmark and release workflow evidence.

These are release qualification gates, not a reason to revert or defer the merged application implementation.

## Purpose

`app-main` is the desktop-application product line for Media Experiment Ledger. It is not a wrapper around the GitHub Pages site and does not replace the existing `main` web, analysis and Release product line.

The app is a local-first cross-platform studio for:

- importing, indexing, deduplicating and managing large image/video corpora;
- optionally generating media through supported APIs, beginning with Agnes image and video;
- configuring durable high-volume automation with pacing, retries, budgets, checkpoints and recovery;
- running Prompt Repeatability Atlas independently from object detection;
- running YOLOX and NanoDet-Plus models through ONNX Runtime;
- reviewing large asset collections through generated proxies and bounded workers;
- producing editable Atlas reports and static PDFs;
- managing models, templates, credentials, updates, backups and recovery;
- publishing explicit GitHub Releases through gated workflows;
- preserving privacy through local-first diagnostics and default-off telemetry.

## Complete-v1 principle

The third specification round establishes the controlling rule:

> When a capability is based on mature engineering techniques and its primary difficulty is implementation volume, platform integration or testing effort, it MUST be completed in v1 rather than deferred merely to create a smaller MVP.

Ordinary engineering complexity is not a deferral reason. Legal rights, unsafe arbitrary-code execution, unsupported scientific claims and genuine platform impossibility remain valid boundaries.

Normative details:

- [`docs/app/SPECIFICATION_ROUND_03.md`](docs/app/SPECIFICATION_ROUND_03.md)
- [`docs/app/V1_SCOPE_ACCEPTANCE_MATRIX.md`](docs/app/V1_SCOPE_ACCEPTANCE_MATRIX.md)
- [`docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md`](docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md)
- [`app-product-contract.json`](app-product-contract.json)

## Required package matrix

- Windows x64 NSIS installer;
- Windows x64 portable package;
- macOS arm64 DMG and update ZIP;
- macOS Intel x64 DMG and update ZIP;
- Linux x64 AppImage;
- Linux x64 `.deb`.

Packaging uses Vite, `electron-builder` and `electron-updater`. Stable `1.0.0` requires Windows code signing and Apple signing/notarization. Unsigned artifacts are restricted to clearly labeled prereleases and cannot enter the stable automatic-update channel.

## Application baseline

- Electron hardened main process.
- Vue 3 and Vuetify 3 Single-File Components.
- Composition API with `<script setup lang="ts">`.
- TypeScript strict mode.
- Pinia for UI/session state and TanStack Vue Query for bounded asynchronous state.
- SQLite as source of truth.
- Responsive `v-row`/`v-col` layouts, semantic colors/icons, `v-hover`, transitions and reduced-motion behavior.
- Light, dark and system appearance.
- `zh-TW`, `en`, `zh-CN`, `ja` and `ko` locale foundation.

## Runtime and security baseline

- Sandboxed renderer with `nodeIntegration: false` and `contextIsolation: true`.
- Self-contained sandbox-compatible preload with closed typed IPC allowlists.
- No renderer filesystem, secret or process-spawn privileges.
- Self-contained version-pinned Python engine; users do not install Python.
- Pipe-based child-process protocol with no public listening port.
- OS-backed secure credential storage where available.
- Session secret mode, warned expert `.env` mode and encrypted portable vault.
- Source media remains immutable.
- Jobs, checkpoints, migrations, updates and exports use durable state and atomic writes where applicable.

## Implemented functional areas

### Data and automation

- Adaptive managed-copy/external-reference import.
- SHA-256 deduplication, managed blobs, proxy pyramids and video posters.
- Quick Start and Full Research corpus manifest workflows with rights gates.
- Agnes image/video automation with durable submit, poll, download and restart recovery.
- Retry-After, exponential backoff, budgets and circuit breakers.
- Generated Media validation, quarantine and optional named-corpus enrollment.

### Atlas and reports

- Mixed image/video cohort evidence.
- Default 10%/50%/90% video strips, poster and GIF preview generation.
- Hybrid structured/freeform document editor.
- Autosave, checkpoints and revision restore.
- Seven built-in templates and declarative external template import/export.
- Immutable per-document custom-template snapshots.
- Sandboxed static PDF rendering with preflight warnings and deterministic SHA manifest.

### Detection

- YOLOX-Tiny/S/L registry slots.
- NanoDet-Plus m-320/m-416/m-1.5x-416 registry slots.
- CPU fallback and optional DirectML/CUDA/CoreML provider selection.
- Hash/provenance/license-aware model management.
- Declarative user-supplied ONNX manifests restricted to verified built-in decoders.
- Durable item progress, pause/resume/cancel/recovery and partial results.

### Operations

- Job Center, Settings and Secret Profiles.
- Update & Recovery Center with online/manual/offline channels.
- Pre-update and cold-start backups, WAL checkpoints and restart restore plans.
- Support bundle preview, redaction and default-off telemetry.
- Release workflow with SBOM, notices, checksums, artifact manifests and signing gates.
- Large-corpus benchmark workflow.

## Engineering method

Implementation remains specification-driven and test-driven:

```text
Decision -> Requirement ID -> Test -> Implementation -> CI evidence -> Release manifest
```

A feature is not release-qualified merely because its happy-path UI works. Stable release evidence also includes signing, hardware, rights, installation/update, performance, accessibility and localization checks as defined by the acceptance matrix.

## Open-source and rights

- App-specific source is Apache-2.0.
- Accepted source and binaries are public.
- Third-party notices, SBOM, checksums and dependency/license scans are mandatory.
- Model weights, sample data, fonts, templates and provider assets retain separate rights manifests.
- Unknown redistribution rights default to `do_not_distribute`.
- When rights prevent bundling, use verified download-on-demand or user-supplied acquisition rather than silently deleting the surrounding workflow.

## Branch policy

- `main` remains the existing web/analysis/Release product line.
- `app-main` is the long-lived desktop integration branch.
- Feature branches start from `app-main`.
- Use normal merge commits.
- Preserve branches unless the user asks for deletion.
