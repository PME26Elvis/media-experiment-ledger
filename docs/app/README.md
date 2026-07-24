# Media Experiment Ledger Studio Specification and Implementation Index

This directory is the normative human-readable specification set and implementation evidence index for the `app-main` desktop product line.

## Current status

- Public product: **Media Experiment Ledger Studio**
- Descriptor: **Atlas · Detection · Media Automation**
- Product status: `release_candidate_published_stable_external_evidence_pending`
- Implementation status: `merged_to_app-main`
- Contract baseline: `2026-07-23.1`
- Machine contract: [`../../app-product-contract.json`](../../app-product-contract.json)
- Long-lived product branch: `app-main`
- Initial implementation PR: [#30](https://github.com/PME26Elvis/media-experiment-ledger/pull/30), merged normally
- Lifecycle candidate: [`studio-v1.0.0-rc.2`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.2)
- Latest provider-qualified candidate: [`studio-v1.0.0-rc.3`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.3)
- Immutable Quick Start corpus: [`studio-sample-corpus-quick-start-v2`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-sample-corpus-quick-start-v2)
- Stable external qualification register: [issue #49](https://github.com/PME26Elvis/media-experiment-ledger/issues/49)
- Blocking product questions: **0**

The application is implemented and distributable as an explicitly unsigned prerelease. Stable `1.0.0` remains blocked by credentials, rights, real hardware and manual evidence that repository code cannot truthfully manufacture.

## Verified implementation and release evidence

The merged application and release candidates have passed:

1. locked `npm ci` installation and production dependency audit;
2. TypeScript/Vue typecheck, JavaScript tests and Python engine tests;
3. self-contained PyInstaller engine build and protocol smoke;
4. renderer/main/preload production build;
5. real packaged application launch on Windows, Linux and macOS;
6. sandbox, preload bridge, SQLite and engine readiness checks;
7. 130 route, locale and viewport checks across five locales;
8. exact public asset allowlist, SBOM, notices, checksums, manifests and consolidated evidence;
9. pull-request release dry runs that build all four platform targets without creating tags or Releases.

### RC.2 install lifecycle

- Windows x64: silent NSIS baseline install, `0.9.9` → `1.0.0-rc.2` in-place upgrade, portable launch and silent uninstall.
- Linux x64: baseline `.deb` install, RC.2 upgrade, AppImage launch and package removal.
- macOS arm64 and Intel x64: baseline DMG installation, RC.2 bundle replacement and removal.
- Every platform verifies that persistent user data survives upgrade and removal.

### RC.3 provider truth

- The packaged engine reports its actual ONNX Runtime provider inventory through the typed engine protocol.
- Detection Studio disables unavailable providers and defaults safely to CPU.
- An explicit accelerator request cannot silently claim CPU fallback as accelerator success.
- Hosted macOS arm64 and Intel x64 runners prove real CoreML graph-node execution against a deterministic CPU baseline.
- Hosted Windows proves the packaged DirectML runtime inventory and records truthful CPU fallback where no usable DirectML device exists.
- Opt-in self-hosted DirectML and CUDA jobs remain fail-closed and require assigned graph nodes greater than zero.

## Release qualification boundaries

Stable `1.0.0` still requires the unchecked evidence in [issue #49](https://github.com/PME26Elvis/media-experiment-ledger/issues/49), including:

- Windows Authenticode signing;
- Apple Developer ID signing, notarization, stapling and Gatekeeper verification;
- GPG checksum signing and Ed25519 offline-update verification;
- signed online and offline update-path qualification;
- real DirectML and CUDA hardware execution evidence;
- a rights-cleared immutable Full Research corpus;
- published 10,000-image / 1,000-video scale evidence;
- final accessibility, visual, controlled real-provider and operator acceptance evidence.

These are release-blocking acceptance items. They do not revert the executable product to an “unimplemented” state, and prereleases must name the missing evidence rather than implying stable qualification.

## Controlling v1 principle

Specification round 3 establishes:

> When a capability uses mature engineering techniques and its main difficulty is implementation volume, platform integration or testing effort, it MUST be completed in v1 rather than deferred merely to reduce scope.

This does not weaken security, data integrity or licensing gates. Unknown redistribution rights, unsafe arbitrary code, unsupported accuracy claims and unavailable operator credentials remain valid boundaries.

## Normative precedence

Conflicts are resolved in this order:

1. `app-product-contract.json` version `2026-07-23.1`;
2. [`SPECIFICATION_ROUND_03.md`](SPECIFICATION_ROUND_03.md);
3. [`V1_SCOPE_ACCEPTANCE_MATRIX.md`](V1_SCOPE_ACCEPTANCE_MATRIX.md);
4. [`V1_TDD_SDD_ENGINEERING_POLICY.md`](V1_TDD_SDD_ENGINEERING_POLICY.md);
5. [`SPECIFICATION_ROUND_02.md`](SPECIFICATION_ROUND_02.md);
6. [`LICENSING_AND_DISTRIBUTION_POLICY.md`](LICENSING_AND_DISTRIBUTION_POLICY.md);
7. accepted decisions and numbered baseline specifications;
8. supporting references.

A newer accepted decision or recorded implementation result overrides earlier provisional or “not started” language. Release qualification language still controls stable publication.

## Core normative documents

| Document | Scope | State |
|---|---|---|
| [`SPECIFICATION_ROUND_03.md`](SPECIFICATION_ROUND_03.md) | Complete-v1 principle; packaging, signing, engine, vault, GPU, PDF, import, query, sync, scheduler, telemetry, templates, custom ONNX and publishing | Normative round 3 |
| [`V1_SCOPE_ACCEPTANCE_MATRIX.md`](V1_SCOPE_ACCEPTANCE_MATRIX.md) | Requirement IDs and release evidence for complete v1 | Release-blocking |
| [`V1_TDD_SDD_ENGINEERING_POLICY.md`](V1_TDD_SDD_ENGINEERING_POLICY.md) | SDD/TDD workflow, test stack, coverage, mutation, fault injection and CI gates | Release-blocking |
| [`SPECIFICATION_ROUND_02.md`](SPECIFICATION_ROUND_02.md) | Name, package matrix, sample tiers, secrets, tray, editor, templates, detector subset and open-source posture | Accepted |
| [`LICENSING_AND_DISTRIBUTION_POLICY.md`](LICENSING_AND_DISTRIBUTION_POLICY.md) | Apache-2.0 app source and separate model/data/font/template rights | Accepted |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | Historical decisions; no blocking product questions remain | Resolved register |
| [`ROUND_03_REFERENCES.md`](ROUND_03_REFERENCES.md) | Official references for builder/updater, safeStorage, Python runtime, libsodium, ONNX providers and test stack | Supporting |
| [`HARDWARE_FEASIBILITY_AND_EXPANSION_PLAN.md`](HARDWARE_FEASIBILITY_AND_EXPANSION_PLAN.md) | Mainstream provider-pattern audit, software feasibility verdicts and phased feature roadmap | Active engineering plan |
| [Issue #49](https://github.com/PME26Elvis/media-experiment-ledger/issues/49) | External stable-release evidence checklist | Active release gate |

## Numbered baseline specifications

| Document | Scope |
|---|---|
| [`00_PRODUCT_CHARTER.md`](00_PRODUCT_CHARTER.md) | Product intent, personas, local-first principles, scope and journeys |
| [`01_UX_DESIGN_SYSTEM.md`](01_UX_DESIGN_SYSTEM.md) | Vuetify 3 design system, responsive behavior, hover, transitions, accessibility and information architecture |
| [`02_DESKTOP_ARCHITECTURE_AND_SECURITY.md`](02_DESKTOP_ARCHITECTURE_AND_SECURITY.md) | Electron processes, typed IPC, workers, engine, secrets and threat model |
| [`03_DATA_PROJECT_AND_RELEASE_SPEC.md`](03_DATA_PROJECT_AND_RELEASE_SPEC.md) | Projects, paths, import/export, sample corpora and Releases |
| [`04_MEDIA_API_AUTOMATION_SPEC.md`](04_MEDIA_API_AUTOMATION_SPEC.md) | Agnes image/video calls, pacing, retries, budgets, scheduling and recovery |
| [`05_ATLAS_STUDIO_SPEC.md`](05_ATLAS_STUDIO_SPEC.md) | Atlas analysis, evidence, report editor, templates and PDF export |
| [`06_DETECTION_STUDIO_SPEC.md`](06_DETECTION_STUDIO_SPEC.md) | Model registry, licenses, checkpoints, comparison and inference |
| [`07_PERFORMANCE_AND_SCALE_SPEC.md`](07_PERFORMANCE_AND_SCALE_SPEC.md) | 10,000-image/1,000-video design, proxies, virtualization, caches and workers |
| [`08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md`](08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md) | Online/offline updates, backup, migration and Recovery Center |
| [`09_TESTING_RELEASE_AND_ACCEPTANCE.md`](09_TESTING_RELEASE_AND_ACCEPTANCE.md) | Test and release baseline, extended by round-three TDD/SDD policy |
| [`10_ROADMAP_AND_DELIVERY_PLAN.md`](10_ROADMAP_AND_DELIVERY_PLAN.md) | Dependency ordering and delivery gates |
| [`DECISIONS.md`](DECISIONS.md) | Accepted decision history |
| [`REFERENCES.md`](REFERENCES.md) | Initial upstream references and audit checklist |

## Implemented architecture summary

### Application stack

- Electron + Vite.
- Vue 3 + Vuetify 3 with Composition API and `<script setup lang="ts">`.
- TypeScript strict, Pinia, TanStack Vue Query and SQLite.
- `electron-builder` + `electron-updater`.

### Runtime and security

- Self-contained PyInstaller Python engine; no user Python installation.
- Versioned child-process protocol; no public local server.
- Sandboxed renderer and closed typed preload bridges.
- OS/session/expert-env/encrypted-vault credential modes.
- CPU universal path with truthful DirectML, CUDA and CoreML provider selection.

### Functional surfaces

- Workspace, Media Import and Sample Corpora.
- Agnes image/video Automation.
- Atlas Studio and mixed-media evidence.
- Detection Studio and Model Manager.
- Job Center.
- Report Library, custom templates and PDF export.
- Settings and credential profiles.
- Update & Recovery Center.
- Support & Privacy diagnostics.

### Platform packages

- Windows x64 NSIS installer and portable package.
- macOS arm64 and Intel x64 DMG/update ZIP.
- Linux x64 AppImage and `.deb`.
- Windows signing and Apple signing/notarization remain required for stable publication.
