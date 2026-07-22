# Media Experiment Ledger Studio

> Product line branch: `app-main`  
> Public identity: **Media Experiment Ledger Studio**  
> Product descriptor: **Atlas · Detection · Media Automation**  
> Current phase: **implementation ready**  
> Implementation status: **not started**  
> Specification baseline: **2026-07-22.3**  
> Primary specification index: [`docs/app/README.md`](docs/app/README.md)

## Purpose

`app-main` is a new desktop-application product line for Media Experiment Ledger. It is not a wrapper around the GitHub Pages site and does not replace the existing `main` web/analysis/Release product line.

The app is a substantial local-first cross-platform studio for:

- importing, indexing, deduplicating and managing large image/video corpora;
- optionally generating media through supported APIs, beginning with Agnes image and video;
- configuring durable high-volume automation with pacing, retries, budgets, checkpoints and recovery;
- running Prompt Repeatability Atlas independently from object detection;
- running multiple detector models through CPU, DirectML, CUDA and CoreML providers;
- reviewing thousands of assets through virtualized, display-pixel-aware previews;
- producing editable, highly polished Atlas documents and static PDFs;
- managing models, runtime packs, templates, credentials and project migrations;
- publishing explicit GitHub Releases;
- scheduling background work through platform user schedulers;
- synchronizing projects through user-selected cloud folders without live SQLite synchronization;
- updating the app while preserving projects, settings, credentials, jobs and recovery history.

## Complete-v1 principle

The third specification round establishes the controlling rule:

> When a capability is based on mature engineering techniques and its primary difficulty is implementation volume, platform integration or testing effort, it MUST be completed in v1 rather than deferred merely to create a smaller MVP.

Ordinary engineering complexity is not a deferral reason. Legal rights, unsafe arbitrary-code execution, unsupported scientific claims and genuine platform impossibility remain valid boundaries.

Normative details:

- [`docs/app/SPECIFICATION_ROUND_03.md`](docs/app/SPECIFICATION_ROUND_03.md)
- [`docs/app/V1_SCOPE_ACCEPTANCE_MATRIX.md`](docs/app/V1_SCOPE_ACCEPTANCE_MATRIX.md)
- [`docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md`](docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md)
- [`app-product-contract.json`](app-product-contract.json)

## Required v1 packages

- Windows x64 NSIS installer;
- Windows x64 portable package;
- macOS arm64 DMG and update ZIP;
- macOS Intel x64 DMG and update ZIP;
- Linux x64 AppImage;
- Linux x64 `.deb`.

Packaging uses Vite, `electron-builder` and `electron-updater`. Stable `1.0.0` requires Windows code signing and Apple signing/notarization. Unsigned artifacts are clearly labeled prereleases and cannot enter the stable automatic-update channel.

## Non-negotiable frontend baseline

- Electron.
- Vue 3 Single-File Components.
- Vuetify 3 current stable syntax at implementation time.
- Composition API everywhere with `<script setup lang="ts">`.
- TypeScript strict mode.
- Pinia for UI/session state.
- TanStack Vue Query for bounded asynchronous query state.
- SQLite as source of truth.
- Responsive layouts built with `v-container`, `v-row` and `v-col`.
- Meaningful `color`, `prepend-icon` and `append-icon` usage.
- `v-hover` and Vuetify/Vue transitions on meaningful interactive surfaces.
- Light, dark and system appearance.
- Reduced-motion support.
- Complete `zh-TW`, `en`, `zh-CN`, `ja` and `ko` localization.
- Loading, empty, partial, error, offline, interrupted, recovery and completed states where applicable.

## Runtime and security baseline

- Sandboxed renderer with `nodeIntegration: false` and `contextIsolation: true`.
- Narrow typed/versioned preload IPC only.
- No renderer filesystem, secret or process-spawn privileges.
- Self-contained version-pinned Python engine; users do not install Python.
- Versioned pipe-based protocol and capability-scoped staging files; no public listening port.
- OS secure credential storage when genuinely secure.
- Linux `basic_text` persistence rejected.
- Session secret mode, expert `.env` mode and portable Argon2id/XChaCha20-Poly1305 encrypted vault.
- Source media remains immutable.
- Jobs, checkpoints, migrations, updates and exports are durable and transactional where applicable.

## Accepted v1 functional scope

### Data and automation

- Quick Start and sanitized Full Research corpora in dedicated immutable Releases.
- Sanitized complete prompt text and normalized provenance when rights review passes.
- Adaptive managed-copy/external-reference imports.
- Agnes image/video automation.
- Generated Media collection and optional named-corpus auto enrollment.
- Task Scheduler, LaunchAgent, `systemd --user` and tray fallback scheduling.

### Atlas

- Complete image/video cohort analysis and evidence.
- Hybrid structured/freeform document editor.
- Rich text, autosave, revisions and undo/redo.
- Seven built-in templates.
- Declarative external template import/export.
- Static PDF with default 10%/50%/90% video strip and poster/timestamp/strip/keyframe alternatives.

### Detection

- YOLOX-Tiny/S/L.
- NanoDet-Plus-m-320/m-416/m-1.5x-416.
- CPU fallback plus DirectML, CUDA and CoreML in v1.
- Signed acceleration packs where useful.
- Hash/provenance/license-aware model registry.
- User-supplied ONNX through known adapters, declarative manifests and sandboxed WASM postprocessing.
- Item-level checkpoints, pause/resume/cancel/recovery and partial results.

### Integrations

- Draft-first GitHub Release publisher.
- Provider-agnostic cloud-folder project sync using immutable blobs, snapshots, journals and conflict resolution.
- Comprehensive local diagnostics.
- Default-off consent-based remote telemetry transport.

## Engineering method

All implementation is specification-driven and test-driven.

```text
Decision -> Requirement ID -> Failing test -> Implementation -> CI evidence -> Release manifest
```

Required evidence includes unit, component, IPC, Python engine, real FFmpeg/ONNX, Playwright Electron E2E, migration, fault-injection, visual, accessibility, all-locale, real GPU, package install/update, performance, license and SBOM tests.

A feature is not complete merely because its happy-path UI works.

## Open-source and rights

- App-specific source is Apache-2.0.
- Accepted source and binaries are public.
- Third-party notices, SBOM, checksums and dependency/license scans are mandatory.
- Model weights, sample data, fonts, templates and provider assets keep separate rights manifests.
- Unknown redistribution rights default to `do_not_distribute`.
- When rights prevent bundling, use verified download-on-demand or user-supplied acquisition rather than silently deleting the feature.

## Branch policy

- `main` remains the existing web/analysis/Release product line.
- `app-main` is the long-lived desktop integration branch.
- Feature branches start from `app-main`.
- Use normal merge commits.
- Preserve branches unless the user asks for deletion.
- Draft PR #29 remains unmerged until the user changes that instruction.

## Implementation authorization

The product specification is ready. The application has not been implemented.

No production implementation begins until the user explicitly asks to start or complete it.