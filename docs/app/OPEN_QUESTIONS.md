# Desktop Product Open Questions

This register is the primary interface for future specification rounds. Each question includes why it matters, a provisional default so the design remains coherent, and the specification surfaces that must change when the answer is approved.

Questions are grouped by priority:

- **P0** — blocks secure architecture, package identity or the first implementation milestone.
- **P1** — materially changes v1 product scope or user workflow.
- **P2** — can be deferred without creating expensive architectural rework.

Answering a question should:

1. update this file with the selected answer and status;
2. add or revise a decision in `DECISIONS.md`;
3. update every affected specification;
4. update `app-product-contract.json` if the answer is a stable invariant;
5. update roadmap and acceptance tests.

---

## P0 — Product and platform foundation

### APP-Q-001 — What is the final public app name?

- Priority: P0 before packaging/signing.
- Status: `open`
- Why it matters: package IDs, executable/app bundle names, signing identity, update feed, data directories and public Release branding should not be renamed casually after stable release.
- Provisional default: **Media Experiment Ledger Desktop**; slug `media-experiment-ledger-desktop`.
- Options:
  1. Keep the repository-aligned name.
  2. Choose a shorter independent product name while retaining “by Media Experiment Ledger”.
  3. Use a technical studio name emphasizing Atlas/Detection.
- Recommendation: choose before Phase 1 packaging identifiers are finalized; internal project schema IDs should remain brand-independent.
- Affected: Product Charter, Release naming, update identity, signing, UI branding.

### APP-Q-002 — Which v1 platform/package matrix is mandatory?

- Priority: P0.
- Status: `open`
- Why it matters: updater choice, native modules, code signing, CI cost and test matrix depend on exact package types.
- Provisional default:
  - Windows x64 installer: required;
  - macOS arm64 DMG/app: required;
  - Linux x64 AppImage: required;
  - Windows portable: provisional;
  - macOS x64/universal: provisional;
  - Linux `.deb`: provisional.
- Decisions needed:
  - Must Intel macOS be supported at v1?
  - Is a Windows portable ZIP/exe important enough to support separate update semantics?
  - Is `.deb` required alongside AppImage?
- Recommendation: required first stable set should be Windows x64, macOS arm64 and Linux AppImage; add other packages only when update/install tests are real.
- Affected: Architecture, Releases, Updates, Testing, Roadmap.

### APP-Q-003 — Which Electron packaging/updater strategy should be selected?

- Priority: P0 before implementation scaffold.
- Status: `open`
- Why it matters: Electron Forge makers, Windows installer type, macOS update archive/feed and Linux behavior affect package identity and migration testing.
- Provisional default: Electron Forge + Vite; choose supported makers/updater after exact package matrix is approved.
- Candidate considerations:
  - Forge makers with Squirrel.Windows, ZIP/DMG and AppImage/deb tooling;
  - electron-builder/electron-updater alternative if its update/package matrix is materially stronger;
  - custom update manifest layered over platform installer handoff.
- Recommendation: compare current maintained tooling against the approved package matrix at implementation start, then lock one architecture decision before writing product code.
- Affected: Architecture, Release workflow, Updates.

### APP-Q-004 — Should the sample corpus normally live in every app Release or a dedicated immutable data Release?

- Priority: P0 for Release architecture.
- Status: `open`
- Why it matters: repeatedly attaching gigabytes to every app release wastes upload time and makes Releases dense, but separate data releases add indirection.
- Provisional default: same app Release for the first demonstrator; dedicated immutable sample-corpus Release once corpus size/cadence becomes independent.
- Options:
  1. Always same Release.
  2. Always dedicated `sample-corpus-vN` Release.
  3. Hybrid manifest: same Release may point to an existing dedicated corpus version.
- Recommendation: hybrid; app Release records the recommended corpus manifest/tag but does not re-upload unchanged data.
- Affected: Data/Release, onboarding, workflow inputs, update/download manifest.

### APP-Q-005 — Which existing repository data is approved for sample-corpus redistribution?

- Priority: P0 before first public sample asset.
- Status: `open`
- Why it matters: “raw input” may include prompts, provider metadata, URLs, paths, EXIF or personal/sensitive information. App sample data becomes a deliberate product asset, not an automatic copy of all Releases.
- Provisional default: create a curated subset after automated and manual privacy/license review; include enough images/videos for Atlas and two-model Detection demos, but exclude secrets, signed URLs, local paths and unnecessary provider payloads.
- Decisions needed:
  - full current canonical corpus or smaller tutorial corpus?
  - include original prompt text or only IDs/categories?
  - include raw response metadata after sanitization?
  - include all videos or selected representative cohorts?
- Recommendation: two tiers later—small Quick Start corpus plus optional full Research corpus.
- Affected: Sample manifest, privacy audit, Release size, onboarding, fixtures.

### APP-Q-006 — How much persistent `.env` file-backed secret management should the app support?

- Priority: P0 security decision.
- Status: `open`
- Why it matters: user wants direct file access, but persistent `.env` values are plaintext and may be copied into backups/cloud sync.
- Provisional default:
  - import `.env` into encrypted profiles;
  - ordinary configs reference profile IDs;
  - explicit optional file-backed mode with warning;
  - explicit secret-bearing `.env` export;
  - no silent plaintext fallback.
- Options:
  1. Import/export only; app never continuously reads a persistent `.env`.
  2. Support persistent file-backed profiles as an expert option.
  3. Make `.env` the default store, contrary to current security recommendation.
- Recommendation: option 2 with encrypted store as default.
- Affected: Architecture, API Automation, settings UI, backups.

### APP-Q-007 — What is the Linux secret-storage fallback when Secret Service is unavailable?

- Priority: P0 for Linux credential support.
- Status: `open`
- Why it matters: safeStorage may not have a secure OS backend in minimal Linux environments.
- Provisional default: offer session-only environment secret and guidance to configure a keyring; do not persist plaintext.
- Candidate future option: password-protected portable vault using a reviewed KDF/encryption design.
- Recommendation: session-only + keyring guidance in first implementation; portable encrypted vault only after dedicated cryptographic review.
- Affected: Architecture, API Automation, Linux tests.

### APP-Q-008 — Should the initial engine package include a self-contained Python runtime?

- Priority: P0 architecture/package size.
- Status: `open`
- Why it matters: existing Atlas/detection Python is valuable, but shipping Python increases package size, platform builds and vulnerability/license maintenance. A full rewrite increases correctness risk.
- Provisional default: hybrid packaged engine with Python reuse behind a language-neutral protocol; no user-installed Python.
- Options:
  1. Package Python engine first, migrate selectively later.
  2. Rewrite all processing to Node/native before first app milestone.
  3. External Python environment—currently not recommended for mainstream users.
- Recommendation: option 1, guarded by golden equivalence and independent engine updates only through signed app releases.
- Affected: Architecture, package sizes, SBOM, Roadmap.

---

## P1 — Primary product workflows

### APP-Q-009 — Should API jobs continue in the system tray/background after the main window closes?

- Priority: P1.
- Status: `open`
- Why it matters: long Agnes jobs may run for days; close-button semantics, sleep prevention and startup scheduling affect user expectations.
- Provisional default: configurable behavior; when a job is active, closing shows “keep running in tray / pause and quit / cancel” rather than terminating silently.
- Additional decisions:
  - launch at login?
  - resume scheduled jobs automatically?
  - prevent sleep while active submission/download is in flight?
  - show native notifications?
- Recommendation: tray/background supported, launch-at-login opt-in, sleep prevention scoped to active critical stages.
- Affected: Product Charter, API Automation, app lifecycle, platform tests.

### APP-Q-010 — How freeform should Atlas document layout be?

- Priority: P1 before Document Studio implementation.
- Status: `open`
- Why it matters: a fully freeform desktop-publishing canvas is powerful but significantly increases layout engine, accessibility, pagination, PDF and migration complexity.
- Provisional default: structured block/page editor with responsive columns, controlled sizing and page-break rules; optional advanced absolute-position block later.
- Options:
  1. Structured block editor only.
  2. Hybrid: structured default plus controlled freeform page mode.
  3. Fully freeform canvas from v1.
- Recommendation: option 2 staged—ship structured v1 foundation, then add freeform mode without making every report depend on it.
- Affected: Atlas Studio, performance, PDF, accessibility, roadmap.

### APP-Q-011 — Which Atlas templates and visual direction should be prioritized?

- Priority: P1.
- Status: `open`
- Why it matters: built-in templates define the product’s visual identity and affect typography/font packaging.
- Provisional set:
  - Research Light;
  - Editorial Dark;
  - Gallery Minimal;
  - Technical Audit;
  - Executive Review.
- Decisions needed:
  - keep all five?
  - should Chinese academic report style be a dedicated template?
  - should a 16:9 slide-like PDF template exist?
  - preferred brand accent and font families?
- Recommendation: retain five concepts and add a Traditional-Chinese Academic template if it reflects the user's likely workflow.
- Affected: Atlas Studio, font licenses, visual tests.

### APP-Q-012 — What is the preferred model artifact distribution policy?

- Priority: P1 before stable Detection release.
- Status: `open`
- Why it matters: bundling makes first use easier but increases package size and may raise model-weight redistribution questions.
- Provisional default: app bundles adapters/labels/manifests; model weights download on demand after user reviews source/hash/license. Offline user-supplied/import package supported later.
- Options:
  1. Bundle verified baseline models.
  2. Download baseline models on demand.
  3. Require user-supplied weights.
  4. Hybrid by model/license.
- Recommendation: option 4; do not bundle until each weight has explicit approval.
- Affected: Detection, package size, Release notices, offline use.

### APP-Q-013 — Which larger detector variants are v1 requirements?

- Priority: P1.
- Status: `open`
- Why it matters: every model needs adapter tests, resource metadata, downloads, license review and cross-platform smoke.
- Provisional catalog candidates:
  - YOLOX Nano/S/M/L/X;
  - NanoDet-Plus m-416, m-1.5x-320, m-1.5x-416.
- Recommendation for first expansion:
  - YOLOX-S and YOLOX-L to represent medium/high tiers;
  - NanoDet-Plus-m-416 and m-1.5x-416;
  - add all remaining variants after registry architecture is stable.
- User decision: Is the goal “all official common variants” at initial stable release, or a carefully selected tiered subset?
- Affected: Detection, testing matrix, model storage, roadmap.

### APP-Q-014 — Is GPU acceleration required for v1 or a later milestone?

- Priority: P1.
- Status: `open`
- Why it matters: CUDA/DirectML/CoreML significantly increase runtime/package/driver testing complexity but improve larger-model usability.
- Provisional default: CPU ONNX Runtime is required baseline; acceleration is Phase 9 after the app/job/model architecture is stable.
- Options:
  1. CPU-only v1.
  2. Windows DirectML in v1.
  3. NVIDIA CUDA Windows/Linux in v1.
  4. Multi-provider acceleration in v1.
- Recommendation: CPU baseline first, then one provider selected from actual user hardware needs; never block CPU fallback.
- Affected: Detection, packages, resource presets, CI hardware.

### APP-Q-015 — What is the default PDF representation for video/GIF Atlas cohorts?

- Priority: P1.
- Status: `open`
- Why it matters: defaults affect report density and authoring effort.
- Provisional default: 10%/50%/90% three-frame contact sheet with user override to poster frame or selected timestamp.
- Options:
  1. Poster frame.
  2. Three-frame strip.
  3. Full keyframe contact sheet.
  4. Omit by default.
- Recommendation: three-frame strip/contact sheet because it preserves temporal evidence without animation.
- Affected: Atlas templates, PDF preflight, batch operations.

### APP-Q-016 — Should projects copy imported media by default or reference it in place?

- Priority: P1 onboarding/storage.
- Status: `open`
- Why it matters: copying is portable but duplicates large data; referencing is efficient but paths/drives may disappear.
- Provisional default: wizard asks with clear recommendation; small sample/import uses managed copy, large existing folders default to external reference.
- Options:
  1. Always copy.
  2. Always reference.
  3. Adaptive recommendation with explicit user selection.
- Recommendation: option 3 and save user preference per project type.
- Affected: Data/Project, onboarding, export, relinking.

### APP-Q-017 — Should generated API media be automatically enrolled into project input corpora?

- Priority: P1.
- Status: `open`
- Why it matters: automatic enrollment creates seamless workflows but may mix incomplete/failed runs into analysis unexpectedly.
- Provisional default: verified outputs enter a dedicated generated-media collection; user may enable automatic inclusion in a named analysis corpus after run completion.
- Recommendation: do not silently merge into existing user input path; use explicit collection/link.
- Affected: API Automation, project data model, Atlas/Detection input selection.

### APP-Q-018 — Should renderer state tooling remain Pinia, and is a query/cache layer needed?

- Priority: P1 implementation detail.
- Status: `open`
- Why it matters: large DB-backed screens need request cancellation, pagination and cache invalidation; Pinia alone should not become a corpus cache.
- Provisional default: Pinia for UI/session state plus a typed repository/query composable layer over IPC; evaluate a dedicated query library only if it works cleanly in Electron/Vue.
- Recommendation: keep large data in SQLite and bounded page caches regardless of library.
- Affected: Architecture, Performance.

### APP-Q-019 — Should the app support a small “Quick Start” corpus and a full corpus separately?

- Priority: P1.
- Status: `open`
- Why it matters: a full multi-gigabyte corpus is realistic but poor onboarding; a tiny corpus may not demonstrate scale or repeatability.
- Provisional default: Quick Start corpus downloaded during onboarding, optional full Research corpus from Model/Data Manager.
- Recommendation: approve two tiers.
- Affected: Sample Release, onboarding, storage UI, tests.

### APP-Q-020 — What is the initial app license and distribution posture?

- Priority: P1 before public code/package release.
- Status: `open`
- Why it matters: app code license, third-party notices, model/data terms and whether binaries are public influence contribution and distribution.
- Provisional default: keep repository’s existing licensing posture until an explicit app license review; generate notices/SBOM regardless.
- Decisions needed:
  - fully open-source desktop app?
  - same license as current repository?
  - public binaries and source?
  - restrictions around bundled sample data/models?
- Affected: root/app license files, Release, contributor docs, model/data distribution.

---

## P2 — Enhancements that need direction but do not block the foundation

### APP-Q-021 — Should anonymous crash/performance telemetry ever be offered?

- Priority: P2.
- Status: `open`
- Provisional default: no remote telemetry; local diagnostics/support bundle only.
- Options: remain local-only, opt-in self-hosted endpoint, third-party crash service with privacy review.
- Recommendation: local-only for v1.
- Affected: Privacy, settings, architecture.

### APP-Q-022 — Which languages must ship at first stable release?

- Priority: P2.
- Status: `open`
- Provisional default: Traditional Chinese primary, English complete secondary.
- Additional candidates: Simplified Chinese, Japanese, Korean.
- Recommendation: finish zh-TW/en quality before expanding.
- Affected: i18n, visual/accessibility tests, docs.

### APP-Q-023 — Should custom report templates be importable in v1?

- Priority: P2.
- Status: `open`
- Provisional default: built-in templates and duplicate/customize within project; external template import deferred until schema/security is mature.
- Recommendation: defer external import but design versioned declarative template schema now.
- Affected: Atlas Studio, security, project export.

### APP-Q-024 — Should user-supplied ONNX models be supported in v1?

- Priority: P2.
- Status: `open`
- Provisional default: not ordinary v1; expert wizard later supports only allowlisted adapter/output schemas.
- Rationale: arbitrary ONNX shapes/postprocessing cannot be inferred safely.
- Recommendation: allow user-supplied artifact only for a known model adapter/manifest, not arbitrary model families.
- Affected: Detection, security, Model Manager.

### APP-Q-025 — Should Atlas/detection results publish back to GitHub Releases from the app?

- Priority: P2.
- Status: `open`
- Provisional default: local export only in v1.
- Recommendation: future opt-in publisher with GitHub authentication and explicit release namespace, never automatic mutation of current immutable histories.
- Affected: future roadmap, credentials, release integration.

### APP-Q-026 — Should recurring desktop schedules use an OS service/helper?

- Priority: P2.
- Status: `open`
- Provisional default: schedules execute while app/tray process is running; no privileged background service in v1.
- Recommendation: measure need after long-running automation usage.
- Affected: API Automation, installers, updates.

### APP-Q-027 — Should the app support project sync through user-selected cloud folders?

- Priority: P2.
- Status: `open`
- Provisional default: no promised sync; warn about DB locking on cloud/network folders and support export packages.
- Recommendation: future explicit sync model rather than relying on live SQLite in cloud folders.
- Affected: Data/Project, locking, backups.

### APP-Q-028 — Which reference hardware defines performance budgets?

- Priority: P2 before stable benchmark gates.
- Status: `open`
- Provisional default: define low/mid/high Windows tiers plus CI Linux/macOS machines; include SSD and HDD scenarios.
- Suggested user-relevant mid-tier: i7-10700F, 32 GB RAM, RTX 2070 with CPU baseline and optional future GPU benchmark.
- Recommendation: use the user's available machines as practical reference tiers plus clean CI runners.
- Affected: Performance, Testing, acceptance thresholds.

---

## Recommended next review round

The highest-leverage first answers are:

1. APP-Q-001 — final product name;
2. APP-Q-002 — mandatory platforms/packages;
3. APP-Q-004 and APP-Q-005 — sample corpus Release architecture/content;
4. APP-Q-006 and APP-Q-007 — `.env`/Linux secret behavior;
5. APP-Q-009 — tray/background execution;
6. APP-Q-010 — structured versus hybrid freeform Atlas editor;
7. APP-Q-012 through APP-Q-014 — model distribution, variants and GPU scope;
8. APP-Q-020 — app license/distribution posture.

The user may answer only a subset in each round. Unanswered questions retain their provisional defaults and remain visibly open.