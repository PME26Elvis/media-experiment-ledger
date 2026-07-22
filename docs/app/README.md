# Media Experiment Ledger Studio Specification Index

This directory is the normative human-readable specification set for the `app-main` desktop product line.

## Current status

- Public product: **Media Experiment Ledger Studio**
- Descriptor: **Atlas · Detection · Media Automation**
- Product status: `implementation_ready`
- Implementation status: `not_started`
- Specification baseline: `2026-07-22.3`
- Machine contract: [`../../app-product-contract.json`](../../app-product-contract.json)
- Long-lived product branch: `app-main`
- Draft review PR: `#29`
- Blocking product questions: **0**
- Next action: wait for explicit user instruction to begin implementation

The specification is intentionally large because the product is not a minimal wrapper. It defines a complete cross-platform local-first application with media acquisition, large-corpus processing, Atlas document production, multi-model detection, hardware acceleration, updates, synchronization, scheduling, publishing, recovery and comprehensive release evidence.

## Controlling v1 principle

Specification round 3 establishes:

> When a capability uses mature engineering techniques and its main difficulty is implementation volume, platform integration or testing effort, it MUST be completed in v1 rather than deferred merely to reduce scope.

This does not weaken security, data integrity or licensing gates. Unknown redistribution rights, unsafe arbitrary code, unsupported accuracy claims and unavailable platform capabilities remain valid boundaries.

## Normative precedence

Conflicts are resolved in this order:

1. `app-product-contract.json` version `2026-07-22.3`;
2. [`SPECIFICATION_ROUND_03.md`](SPECIFICATION_ROUND_03.md);
3. [`V1_SCOPE_ACCEPTANCE_MATRIX.md`](V1_SCOPE_ACCEPTANCE_MATRIX.md);
4. [`V1_TDD_SDD_ENGINEERING_POLICY.md`](V1_TDD_SDD_ENGINEERING_POLICY.md);
5. [`SPECIFICATION_ROUND_02.md`](SPECIFICATION_ROUND_02.md);
6. [`LICENSING_AND_DISTRIBUTION_POLICY.md`](LICENSING_AND_DISTRIBUTION_POLICY.md);
7. accepted decisions and numbered baseline specifications;
8. supporting references.

A newer accepted decision overrides earlier provisional or deferral language. Implementation MUST consolidate affected numbered specifications as feature branches touch them; developers must not use stale baseline wording to reduce round-three scope.

## Core normative documents

| Document | Scope | State |
|---|---|---|
| [`SPECIFICATION_ROUND_03.md`](SPECIFICATION_ROUND_03.md) | Complete-v1 principle; packaging, signing, engine, vault, GPU, PDF, import, query, sync, scheduler, telemetry, templates, custom ONNX and publishing | **Normative round 3** |
| [`V1_SCOPE_ACCEPTANCE_MATRIX.md`](V1_SCOPE_ACCEPTANCE_MATRIX.md) | Requirement IDs and release evidence for the complete v1 | **Release-blocking** |
| [`V1_TDD_SDD_ENGINEERING_POLICY.md`](V1_TDD_SDD_ENGINEERING_POLICY.md) | SDD/TDD workflow, test stack, coverage, mutation, fault injection and CI gates | **Release-blocking** |
| [`SPECIFICATION_ROUND_02.md`](SPECIFICATION_ROUND_02.md) | Name, six packages, sample tiers, `.env`, tray, hybrid editor, templates, detector subset and open-source posture | Accepted |
| [`LICENSING_AND_DISTRIBUTION_POLICY.md`](LICENSING_AND_DISTRIBUTION_POLICY.md) | Apache-2.0 app source and separate model/data/font/template rights | Accepted |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | Historical decisions; no blocking questions remain | Resolved register |
| [`ROUND_03_REFERENCES.md`](ROUND_03_REFERENCES.md) | Official references for builder/updater, safeStorage, Python runtime, libsodium, ONNX providers and test stack | Supporting |

## Numbered baseline specifications

| Document | Scope |
|---|---|
| [`00_PRODUCT_CHARTER.md`](00_PRODUCT_CHARTER.md) | Product intent, personas, local-first principles, scope and journeys |
| [`01_UX_DESIGN_SYSTEM.md`](01_UX_DESIGN_SYSTEM.md) | Vuetify 3 design system, RWD, hover, transitions, accessibility and information architecture |
| [`02_DESKTOP_ARCHITECTURE_AND_SECURITY.md`](02_DESKTOP_ARCHITECTURE_AND_SECURITY.md) | Electron processes, typed IPC, workers, engine, secrets and threat model |
| [`03_DATA_PROJECT_AND_RELEASE_SPEC.md`](03_DATA_PROJECT_AND_RELEASE_SPEC.md) | Projects, paths, import/export, sample corpora and Releases |
| [`04_MEDIA_API_AUTOMATION_SPEC.md`](04_MEDIA_API_AUTOMATION_SPEC.md) | Agnes image/video calls, pacing, retries, budgets, scheduling and recovery |
| [`05_ATLAS_STUDIO_SPEC.md`](05_ATLAS_STUDIO_SPEC.md) | Atlas analysis, evidence, hybrid editor, templates and PDF export |
| [`06_DETECTION_STUDIO_SPEC.md`](06_DETECTION_STUDIO_SPEC.md) | Model registry, licenses, checkpoints, comparison and inference |
| [`07_PERFORMANCE_AND_SCALE_SPEC.md`](07_PERFORMANCE_AND_SCALE_SPEC.md) | 10,000-image/1,000-video design, proxies, virtualization, caches and workers |
| [`08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md`](08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md) | Online/offline updates, backup, migration and Recovery Center |
| [`09_TESTING_RELEASE_AND_ACCEPTANCE.md`](09_TESTING_RELEASE_AND_ACCEPTANCE.md) | Original test/release baseline, extended by round-three TDD/SDD policy |
| [`10_ROADMAP_AND_DELIVERY_PLAN.md`](10_ROADMAP_AND_DELIVERY_PLAN.md) | Dependency ordering and delivery gates; all mature capabilities now belong to v1 |
| [`DECISIONS.md`](DECISIONS.md) | Accepted decision history through APP-D-050 |
| [`REFERENCES.md`](REFERENCES.md) | Initial upstream references and audit checklist |

## Accepted v1 architecture summary

### Application stack

- Electron + Vite.
- Vue 3 + Vuetify 3.
- Composition API and `<script setup lang="ts">`.
- TypeScript strict.
- Pinia for UI/session state.
- TanStack Vue Query for bounded asynchronous query state over typed IPC.
- SQLite as authoritative project data.
- `electron-builder` + `electron-updater`.

### Platform packages

- Windows x64 NSIS installer and portable package.
- macOS arm64 and Intel x64 DMG/update ZIP.
- Linux x64 AppImage and `.deb`.
- Windows signing and Apple signing/notarization required for stable `1.0.0`.

### Runtime and acceleration

- Self-contained version-pinned Python engine; no user Python installation.
- Versioned child-process protocol; no public local server.
- CPU universal fallback.
- DirectML Windows, CUDA Windows/Linux and CoreML macOS in v1.
- Signed/provider-compatible acceleration packs may be separate downloads.

### Credentials

- OS secure storage when genuinely secure.
- Linux `basic_text` persistence rejected.
- Session secret mode.
- Explicit `.env` expert mode.
- Portable encrypted vault using Argon2id and XChaCha20-Poly1305 through a reviewed library.

### Atlas and Detection

- Atlas and Detection are independent job domains.
- Hybrid structured/freeform Atlas editor.
- Seven built-in templates plus declarative template import/export.
- Default video PDF representation is a 10%/50%/90% frame strip with all major static alternatives.
- Required detector models: YOLOX-Tiny/S/L and NanoDet-Plus-m-320/m-416/m-1.5x-416.
- Known, declarative and sandboxed-WASM custom ONNX adapter paths.

### Data and integrations

- Quick Start and Full Research corpora.
- Sanitized full prompts and normalized provenance when rights review passes.
- Adaptive managed-copy/external-reference imports.
- Generated Media collection with optional named-corpus enrollment.
- GitHub Release publisher.
- Task Scheduler, LaunchAgent and `systemd --user` scheduling.
- Provider-agnostic cloud-folder sync using blobs, snapshots and journals—not live SQLite synchronization.
- Five complete locales: `zh-TW`, `en`, `zh-CN`, `ja`, `ko`.
- Local diagnostics plus default-off opt-in remote telemetry subsystem.

## Development method

All implementation follows SDD and TDD:

```text
Decision -> Requirement ID -> Failing test -> Implementation -> CI evidence -> Release manifest
```

Required layers include:

- Vitest TypeScript tests;
- Vue Test Utils component tests;
- typed IPC contracts;
- pytest/property tests for the engine;
- real FFmpeg and ONNX inference;
- Playwright Electron E2E;
- visual/accessibility/all-locale tests;
- update and migration E2E;
- deliberate process kill, disk-full, corruption, network and GPU fault injection;
- real DirectML/CUDA/CoreML hardware tests;
- six-target clean-machine install/update tests;
- large-corpus benchmarks;
- license, SBOM, notice, secret and signature gates.

A feature is incomplete when only its happy path works.

## Specification-ready determination

The product-decision readiness gates are satisfied:

- all accepted modules have a v1 requirement matrix;
- security-critical architecture decisions are accepted;
- packaging/updater and self-contained engine architecture are fixed;
- all six packages have required test evidence definitions;
- update/signing policy is fixed;
- credential fallback and portable vault are fixed;
- GPU providers are fixed;
- model/data artifact rights remain explicit release gates rather than unanswered product questions;
- performance targets are measurable;
- SDD/TDD and acceptance evidence are defined;
- all previous P0/P1/P2 questions are resolved.

Therefore the product status is `implementation_ready`. This does not mean the app exists. Implementation remains `not_started` and waits for the user's explicit instruction.

## Branch and merge policy

- `main` remains the existing web/analysis/Release product line.
- `app-main` is the long-lived desktop integration branch.
- Implementation feature branches start from `app-main`.
- Use normal merge commits.
- Preserve branches unless the user asks for deletion.
- Draft PR #29 remains an unmerged specification review surface until the user changes that instruction.

## Authorization boundary

No production implementation, packaging claim or Release claim is implied by these documents. The next valid action is to wait until the user explicitly asks to begin or complete implementation.