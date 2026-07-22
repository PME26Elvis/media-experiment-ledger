# Specification Round 03 — Complete v1 Challenge

Status: **accepted and normative**  
Decision date: **2026-07-22**  
Applies to: `app-main` / Media Experiment Ledger Studio  
Supersedes any earlier deferral language that conflicts with this document.

## 1. Governing product principle

The user has established the following controlling rule:

> When a capability is based on mature engineering techniques and its primary difficulty is implementation volume, cross-platform work, testing effort or integration complexity, it MUST be completed in v1 rather than moved to a later release merely to reduce scope.

This is recorded as **APP-D-031 — Complete Mature v1**.

The rule does not permit reckless implementation. Every added capability MUST have explicit schemas, threat boundaries, deterministic failure handling, migration behavior, observability and comprehensive automated tests. Legal uncertainty, unavailable redistribution rights, physical platform limitations and unsafe arbitrary-code execution remain valid blockers; ordinary engineering effort is not.

## 2. Specification status after this round

The product specification advances to:

- product status: `implementation_ready`;
- implementation status: `not_started`;
- implementation may begin only after the user explicitly requests it;
- Draft PR #29 remains unmerged;
- `app-main` remains the long-lived product branch;
- all accepted v1 capabilities are release-blocking unless a later explicit user decision changes them.

No additional product-question round is required before implementation. During implementation, discoveries may produce architecture decision records or defect-driven spec corrections, but they MUST NOT silently reduce v1 scope.

## 3. Accepted architecture decisions

### APP-D-032 — Packaging and updates

v1 MUST use:

- Electron;
- Vite for renderer and Electron-process builds;
- `electron-builder` as the primary packaging tool;
- `electron-updater` for installed-package update flows;
- GitHub Releases as the initial public artifact/update source;
- a versioned internal update manifest and offline import path.

Required targets:

- Windows x64 NSIS installer;
- Windows x64 portable executable/package;
- macOS arm64 DMG and update ZIP;
- macOS Intel x64 DMG and update ZIP;
- Linux x64 AppImage;
- Linux x64 `.deb`.

Windows portable updates use guided download, verified replacement and relaunch while preserving the shared user-data directory. They MUST NOT pretend to use installer semantics.

Update UI MUST include check, available, release-notes, download progress, pause/cancel where supported, verification, installation readiness, restart, failure recovery and offline-package import states.

### APP-D-033 — Signing and notarization

Stable `1.0.0` is blocked until:

- Windows artifacts are Authenticode signed;
- macOS arm64 and x64 artifacts are signed and notarized;
- updater metadata and downloadable artifacts are cryptographically verified;
- signing credentials remain in protected CI environments;
- unsigned artifacts are clearly labeled development/prerelease artifacts and are never offered through the stable automatic-update channel.

Linux artifacts MUST ship checksums, signed manifests and SBOMs. AppImage and `.deb` update flows MUST verify the application release manifest before installation.

### APP-D-034 — Self-contained Python engine

v1 MUST package a self-contained, version-pinned Python runtime for every supported OS/architecture. Users MUST NOT need to install Python.

The runtime baseline is a pinned redistributable build derived from `python-build-standalone` or an equivalently reviewed relocatable distribution. The final source, version, hashes and included licenses MUST be captured in the SBOM and engine manifest.

Electron and Python communicate through a versioned, language-neutral local protocol:

- no listening public network port;
- framed JSON-RPC-style control messages over child-process pipes;
- large/binary payloads exchanged through capability-scoped staging files;
- request IDs, cancellation IDs and schema versions;
- bounded message sizes;
- process heartbeat and hang detection;
- structured progress events;
- sanitized logs;
- engine binary/runtime hash verification before launch.

The current Atlas, YOLOX and NanoDet logic is reused behind adapters and golden equivalence tests. Hot paths MAY later be replaced with Node, Rust, C++ or another native implementation only when benchmarks justify it and output equivalence is proven.

### APP-D-035 — Linux credentials and portable encrypted vault

v1 MUST support all of the following:

1. secure OS-backed storage through Electron `safeStorage` when a real secure backend exists;
2. detection and rejection of insecure `basic_text` persistence;
3. session-only secret entry;
4. explicit expert `.env` file-backed profiles with warnings;
5. a password-encrypted portable credential vault.

The portable vault MUST use a reviewed cryptographic library rather than custom primitives:

- Argon2id password-based key derivation;
- versioned KDF parameters stored with the envelope;
- XChaCha20-Poly1305 authenticated encryption through libsodium or a reviewed compatible binding;
- unique random salt and nonce;
- authenticated metadata including schema version and profile identifiers;
- atomic write and backup rotation;
- tamper detection;
- password-change re-encryption;
- explicit lock, timeout and clipboard-clearing behavior;
- no password recovery backdoor;
- no plaintext secret in logs, crash reports, project exports or ordinary backups.

KDF parameters MUST be calibrated per device within documented lower bounds and tested on low/mid/high reference hardware.

### APP-D-036 — Full v1 hardware acceleration

CPU ONNX Runtime remains the universal fallback. v1 stable MUST also complete:

- DirectML on supported Windows systems;
- CUDA on supported NVIDIA Windows and Linux systems;
- CoreML on supported macOS systems.

Acceleration providers MAY be delivered as signed, version-compatible engine packs so the base installer does not have to include every runtime dependency. However, provider discovery, installation, verification, diagnostics, benchmarks, selection and fallback are v1 features.

Each provider/model/platform combination MUST have:

- capability detection;
- dependency/version diagnostics;
- a real inference smoke test;
- golden-output tolerance tests against CPU;
- out-of-memory handling;
- fallback rules;
- user-selectable automatic/manual provider policy;
- recorded runtime/provider identity in every result manifest.

A detected GPU is not considered usable until the provider smoke test succeeds.

### APP-D-037 — Atlas video representation in PDF

The default representation for a video/GIF cohort is a deterministic three-frame strip sampled at 10%, 50% and 90% of verified duration.

v1 MUST also offer:

- poster frame;
- user-selected timestamp;
- configurable multi-frame strip;
- complete keyframe/contact-sheet page;
- batch conversion of selected video blocks;
- per-block captions and provenance;
- preflight warnings when frames cannot be decoded.

PDF remains static; animated GIF playback inside PDF is not promised.

### APP-D-038 — Adaptive media import and portability

The import wizard MUST provide adaptive recommendations rather than one global behavior:

- Quick Start and small imports default to managed copy;
- large existing folders default to external reference;
- users can override the recommendation;
- the decision can be remembered by project/import type;
- estimates show required disk space, duplicate bytes and portability impact;
- external files support relinking and missing-file diagnostics;
- portable project export can materialize referenced media into content-addressed packages;
- import operations are resumable and deduplicate by hash.

### APP-D-039 — Generated Media collection and enrollment

Verified API outputs MUST first enter a dedicated `Generated Media` collection. They MUST NOT silently pollute an existing analysis corpus.

v1 MUST support:

- automatic collection creation per project/provider/job;
- validation and quarantine before enrollment;
- optional per-job rule to enroll successful outputs into one or more named corpora;
- manual multi-select enrollment;
- provenance links back to request, credential profile ID, provider response and download verification;
- undoable enrollment links without deleting source media.

### APP-D-040 — Renderer state and query architecture

v1 MUST use:

- Pinia for UI/session/application state;
- `@tanstack/vue-query` for asynchronous paginated/query state over typed IPC repositories;
- SQLite as the source of truth;
- cursor/keyset pagination for large tables;
- bounded query caches;
- explicit invalidation and cancellation;
- stable query keys that include project/schema/filter identity;
- no persistence of sensitive query payloads by default;
- no attempt to store the complete media corpus in Pinia or one reactive array.

Virtualized rendering remains independent from query caching and MUST be benchmarked together.

### APP-D-041 — Full Research corpus metadata

The Full Research corpus MUST publish sanitized complete prompt text when rights/privacy review passes, together with:

- canonical prompt ID;
- category/tags;
- provider/model identity;
- appearance-relevant generation settings;
- seed where applicable;
- normalized timestamps and provenance;
- content hashes;
- sanitization report and data-rights manifest.

It MUST exclude secrets, temporary/signed URLs, local absolute paths, account identifiers, unnecessary raw responses and personal/sensitive prompt content. An excluded field MUST be represented through a documented redaction reason rather than silently disappearing.

## 4. Previously deferrable features moved into v1

### APP-D-042 — Telemetry and diagnostics

v1 MUST include:

- comprehensive local diagnostics and support bundles;
- default-off remote telemetry;
- explicit informed consent;
- per-category controls;
- payload preview;
- redaction and secret scanning;
- delete/disable controls;
- an OpenTelemetry-compatible exporter or equivalent pluggable transport;
- no mandatory repository-operated cloud account.

A public stable build may leave the remote endpoint unconfigured, but the tested subsystem and user-configurable endpoint capability MUST exist.

### APP-D-043 — Languages

The first stable v1 MUST ship complete, testable UI localization for:

- Traditional Chinese (`zh-TW`) as primary;
- English (`en`);
- Simplified Chinese (`zh-CN`);
- Japanese (`ja`);
- Korean (`ko`).

All strings, dialogs, menus, notifications, errors, updater flows, accessibility names, PDF template labels and onboarding content MUST be externalized. CI MUST detect missing keys and layout overflow in all required locales.

### APP-D-044 — External custom template import/export

v1 MUST support import/export of declarative Atlas templates through a versioned schema.

Templates:

- contain no executable JavaScript, native code or arbitrary remote resources;
- declare typography, colors, spacing, blocks, page rules and allowed assets;
- undergo schema, font, asset, path and size validation;
- open in preview/quarantine before installation;
- record origin, hash, schema version and compatibility;
- can be duplicated and edited without modifying the original package.

### APP-D-045 — User-supplied ONNX models

v1 MUST support user-supplied ONNX detection models through:

1. known built-in adapters;
2. a declarative custom detection-adapter manifest for common tensor layouts, labels, preprocessing, box decoding and NMS;
3. an expert sandboxed WASM postprocessor path for cases that cannot be expressed declaratively.

Custom adapters MUST be capability-restricted, versioned, resource-limited, hash-identified and disabled by default until validation succeeds. Native or arbitrary Python plugins are prohibited.

### APP-D-046 — GitHub Release publisher

v1 MUST provide an explicit GitHub Release publication workflow from the app:

- encrypted credential/token profile;
- repository and permission validation;
- draft-first preview;
- configurable tag/title/notes/feature bullets;
- asset namespace protection;
- checksums and manifest;
- resumable upload where feasible;
- immutable-history safeguards;
- confirmation before publish;
- no automatic mutation of existing experiment Releases;
- audit log without secrets.

### APP-D-047 — OS scheduler helper

v1 MUST provide opt-in per-user background scheduling through:

- Windows Task Scheduler;
- macOS LaunchAgent;
- Linux `systemd --user` timer/service where available;
- tray-process fallback.

The helper MUST be same-version or protocol-compatible with the app, signed where the platform supports signing, installable/removable from Settings, observable from Job Center and unable to execute arbitrary user scripts.

### APP-D-048 — Cloud-folder project synchronization

v1 MUST support user-selected cloud-folder synchronization without placing a live writable SQLite database under uncontrolled file synchronization.

The design MUST use:

- content-addressed immutable blobs;
- versioned project snapshots;
- operation/change journal exports;
- atomic publish markers;
- device IDs and vector/version metadata;
- lock/lease hints that are not the sole correctness mechanism;
- conflict detection and an explicit resolution UI;
- three-way merge for supported structured metadata;
- duplicate/hash reuse for media;
- recoverable sync history;
- provider-agnostic local folder semantics.

OneDrive, Dropbox, Google Drive or similar clients are treated as folder transports, not trusted database coordinators.

### APP-D-049 — Reference hardware matrix

v1 acceptance MUST include low, mid and high reference tiers plus SSD and HDD scenarios. The user's i7-10700F, 32 GB RAM and RTX 2070 system is a named practical mid-tier Windows reference. A lower-resource CPU-only tier and modern Apple Silicon/high-end GPU tiers MUST also be defined before performance gates are finalized.

## 5. Complete-v1 interpretation rules

- A feature is not complete because a button exists; its error, empty, offline, interrupted, migration and recovery states are part of v1.
- Cross-platform parity means equivalent user outcomes, not identical OS implementation.
- Optional features may remain disabled by default, but their implementation and tests are still release-blocking.
- Provider/license restrictions may change how an artifact is obtained, not whether the surrounding v1 workflow exists.
- A capability can use separately downloadable signed packs without being considered deferred.
- Documentation, accessibility, localization, migration and update handling are part of each feature, not post-release polish.

## 6. Testing and specification-driven development

All implementation MUST follow [`V1_TDD_SDD_ENGINEERING_POLICY.md`](V1_TDD_SDD_ENGINEERING_POLICY.md) and the traceable acceptance matrix in [`V1_SCOPE_ACCEPTANCE_MATRIX.md`](V1_SCOPE_ACCEPTANCE_MATRIX.md).

No v1 item may be marked complete until:

- its requirement IDs are implemented;
- red/green/refactor evidence exists for test-first work where technically applicable;
- unit, component, IPC, engine, E2E, migration, fault-injection and package tests pass as applicable;
- platform artifacts are installed and exercised, not merely compiled;
- recovery paths are tested through deliberate interruption/corruption scenarios;
- licensing and SBOM gates pass;
- required locale and accessibility checks pass;
- performance budgets pass on the declared reference tier.

## 7. Implementation authorization boundary

This round completes the required product decisions and makes the specification implementation-ready. It does **not** itself authorize code implementation. The repository MUST remain in `implementation_status: not_started` until the user explicitly asks to begin or complete implementation.