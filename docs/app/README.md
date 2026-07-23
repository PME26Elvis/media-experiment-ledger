# Media Experiment Ledger Studio Specification and Implementation Index

This directory is the normative human-readable specification set and implementation evidence index for the `app-main` desktop product line.

## Current status

- Public product: **Media Experiment Ledger Studio**
- Descriptor: **Atlas · Detection · Media Automation**
- Product status: `implementation_merged_release_qualification_pending`
- Implementation status: `merged_to_app-main`
- Contract baseline: `2026-07-23.1`
- Machine contract: [`../../app-product-contract.json`](../../app-product-contract.json)
- Long-lived product branch: `app-main`
- Implementation PR: [#30](https://github.com/PME26Elvis/media-experiment-ledger/pull/30), merged normally
- Merge commit: `9838b1c5e56d9523087f9739deebd1804746f0d8`
- Validated implementation head: `447ed656375c6fe934953a0991f2bf4fbcd88122`
- Desktop App CI: run `29972465923`, Windows/macOS/Ubuntu all successful
- Blocking product questions: **0**
- Next phase: operator-controlled release qualification and signed prerelease/stable release evidence

## Verified implementation evidence

The merged application passed the full validation chain on Windows, macOS and Ubuntu:

1. locked `npm ci` installation;
2. production dependency audit;
3. TypeScript and Vue typecheck;
4. JavaScript component/domain tests and coverage gates;
5. Python engine tests;
6. PyInstaller self-contained engine build and engine protocol smoke;
7. Electron renderer/main/preload production build;
8. unpacked Electron package creation;
9. real packaged application launch;
10. sandboxed renderer, isolated preload bridges, SQLite integrity and engine availability checks;
11. platform evidence artifact upload.

Evidence artifacts from run `29972465923`:

- `app-build-evidence-windows-latest`
- `app-build-evidence-macos-latest`
- `app-build-evidence-ubuntu-latest`

## Release qualification boundaries

The implementation is merged, but a signed stable `1.0.0` release still requires evidence that cannot be manufactured by ordinary repository code alone:

- Windows signing certificate;
- Apple Developer ID signing and notarization credentials;
- GPG and Ed25519 release-signing keys;
- real DirectML, CUDA and CoreML hardware execution evidence;
- Full Research corpus redistribution/privacy attestations;
- final manual large-corpus benchmark and release workflow runs.

These remain release-blocking acceptance items. They do not revert the application to an “unimplemented” state.

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
- Vue 3 + Vuetify 3.
- Composition API and `<script setup lang="ts">`.
- TypeScript strict.
- Pinia for UI/session state.
- TanStack Vue Query for bounded asynchronous state over typed IPC.
- SQLite as authoritative project data.
- `electron-builder` + `electron-updater`.

### Runtime and security

- Self-contained PyInstaller Python engine; no user Python installation.
- Versioned child-process protocol; no public local server.
- Sandboxed renderer and self-contained typed preload.
- Four isolated bridges: main app, diagnostics, report templates and custom models.
- OS/session/expert-env/encrypted-vault credential modes.
- CPU universal fallback with optional DirectML, CUDA and CoreML provider selection.

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
