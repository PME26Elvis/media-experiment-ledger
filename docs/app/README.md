# Media Experiment Ledger Studio Specification Index

This directory is the normative human-readable specification set for the `app-main` product line.

The desktop product is deliberately specified as a system of documents rather than a single monolithic proposal. The expected implementation may eventually contain tens of thousands of lines across Electron main/preload processes, Vue/Vuetify renderer code, worker runtimes, media pipelines, model adapters, database migrations, packaging scripts and platform-specific update logic. A one-file specification would become difficult to review, contradict and safely revise.

## Current status

- Public product name: **Media Experiment Ledger Studio**
- Descriptor: **Atlas · Detection · Media Automation**
- Product status: `specification_in_progress`
- Implementation status: `not_started`
- Specification baseline: `2026-07-22.2`
- Machine contract: [`../../app-product-contract.json`](../../app-product-contract.json)
- Long-lived product branch: `app-main`
- Draft review PR: `#29`
- Target review model: iterative specification rounds with explicit user decisions

## Normative precedence

Until the baseline documents are fully consolidated before implementation, conflicts are resolved in this order:

1. `app-product-contract.json` for stable machine-enforced invariants;
2. the newest accepted specification-round document;
3. `LICENSING_AND_DISTRIBUTION_POLICY.md` for rights/distribution boundaries;
4. `DECISIONS.md` and accepted decision records;
5. numbered baseline specifications;
6. provisional defaults in `OPEN_QUESTIONS.md`.

## Document map

| Document | Scope | Current state |
|---|---|---|
| [`SPECIFICATION_ROUND_02.md`](SPECIFICATION_ROUND_02.md) | Accepted product name, packages, sample tiers, `.env`, tray, Atlas editor/templates, detector subset and open-source posture | **Normative round 2** |
| [`LICENSING_AND_DISTRIBUTION_POLICY.md`](LICENSING_AND_DISTRIBUTION_POLICY.md) | Apache-2.0 app source, notices/SBOM, model/data/font/UI asset rights and takedown resilience | **Accepted** |
| [`00_PRODUCT_CHARTER.md`](00_PRODUCT_CHARTER.md) | Product intent, personas, local-first principles, scope boundaries and user journeys | Baseline defined; round 2 applies |
| [`01_UX_DESIGN_SYSTEM.md`](01_UX_DESIGN_SYSTEM.md) | Vuetify 3 component rules, responsive layouts, hover, motion, accessibility and information architecture | Baseline defined |
| [`02_DESKTOP_ARCHITECTURE_AND_SECURITY.md`](02_DESKTOP_ARCHITECTURE_AND_SECURITY.md) | Electron processes, IPC, filesystem, workers, database, secrets and threat model | Baseline defined; packaging/engine questions remain |
| [`03_DATA_PROJECT_AND_RELEASE_SPEC.md`](03_DATA_PROJECT_AND_RELEASE_SPEC.md) | Project schema, paths, import/export, two-tier sample corpus, Release assets and workflow inputs | Baseline defined; round 2 applies |
| [`04_MEDIA_API_AUTOMATION_SPEC.md`](04_MEDIA_API_AUTOMATION_SPEC.md) | Agnes integration, API keys, execution policies, scheduling, retries, stop conditions and audit | Baseline defined; `.env`/tray decisions accepted |
| [`05_ATLAS_STUDIO_SPEC.md`](05_ATLAS_STUDIO_SPEC.md) | App-native Atlas pipeline, hybrid document editing, seven templates and PDF export | Baseline defined; round 2 applies |
| [`06_DETECTION_STUDIO_SPEC.md`](06_DETECTION_STUDIO_SPEC.md) | Multi-model registry, licensing, representative v1 models, checkpoints, progress and comparison | Baseline defined; round 2 applies |
| [`07_PERFORMANCE_AND_SCALE_SPEC.md`](07_PERFORMANCE_AND_SCALE_SPEC.md) | Thousands-of-assets architecture, thumbnails, virtualization, workers, caching and budgets | Baseline defined |
| [`08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md`](08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md) | Online/offline updates, signing, six required package targets, migrations, backup and rollback | Baseline defined; package tool remains open |
| [`09_TESTING_RELEASE_AND_ACCEPTANCE.md`](09_TESTING_RELEASE_AND_ACCEPTANCE.md) | Test pyramid, six-target matrix, benchmark gates, rights validation, Release verification and acceptance criteria | Baseline defined; round 2 adds gates |
| [`10_ROADMAP_AND_DELIVERY_PLAN.md`](10_ROADMAP_AND_DELIVERY_PLAN.md) | Staged delivery plan, implementation gates and dependency ordering | Baseline defined; round 2 scope applies |
| [`DECISIONS.md`](DECISIONS.md) | Original accepted/provisional architecture/product decisions | Active baseline |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | Resolved round-two answers plus remaining implementation-blocking questions | Active |
| [`REFERENCES.md`](REFERENCES.md) | Primary upstream references and dependency/licensing review checklist | Active |
| [`../../app/LICENSE`](../../app/LICENSE) | Apache License 2.0 for app-specific source | Accepted |
| [`../../app/NOTICE`](../../app/NOTICE) | Initial project notice and third-party boundary | Accepted |

## Round-two accepted decisions

The user has approved:

- a technical studio identity rather than a generic desktop suffix;
- Windows installer + portable, macOS arm64 + Intel, Linux AppImage + `.deb` as required targets;
- both Quick Start and Full Research sample corpora;
- encrypted secrets by default with explicit expert `.env` file-backed mode;
- tray/background execution for active jobs;
- a hybrid structured/freeform Atlas editor;
- Traditional Chinese Academic and 16:9 Presentation Report templates;
- representative detector tiers rather than every upstream variant;
- fully open-source source and public binaries, with the project choosing a conservative license policy.

## How future specification rounds work

Each review round should follow this sequence:

1. The user describes a desired capability, workflow, concern or preference.
2. The affected specification documents or an explicit normative round amendment are updated.
3. New decisions receive stable IDs in `DECISIONS.md` or the round decision record.
4. Questions that still materially affect implementation remain in `OPEN_QUESTIONS.md` with a provisional default.
5. The machine contract is changed only when the invariant is stable enough to enforce.
6. Milestones and acceptance tests are synchronized.
7. Contradictions with the existing web/analysis product are called out explicitly.
8. The draft PR remains open until the user declares the specification ready for implementation.
9. Before implementation begins, accepted amendments are consolidated back into the numbered specifications so developers do not need to infer precedence across many rounds.

A future round may expand one topic by thousands of lines. That is expected. Length is not treated as a defect when the content establishes behavior, failure handling, data integrity, platform differences, testing or acceptance criteria.

## Decision states

### Accepted

The user has directly requested the behavior or the behavior is required by a hard platform/security constraint. Implementation may treat it as stable.

### Provisional

A mainstream default has been selected to keep the design coherent, but the user has not explicitly approved the exact choice. Provisional decisions must be easy to replace and are collected in the open-question register.

### Open

The answer changes packaging, data compatibility, licensing, privacy, cost or the primary user workflow enough that implementation should not irreversibly commit to one answer.

### Rejected

The idea is outside product scope or conflicts with a stronger requirement. Rejected decisions remain recorded to prevent repeated ambiguity.

## Specification quality rules

Every major module specification must include:

- goals and non-goals;
- principal user journeys;
- UI states, empty states and error states;
- data inputs and outputs;
- persistent schemas and versioning;
- background job stages;
- cancellation, pause, resume and recovery behavior;
- performance constraints;
- security and privacy boundaries;
- platform differences;
- telemetry/logging behavior;
- test coverage;
- release, license and migration implications;
- acceptance criteria;
- unresolved questions.

## Implementation rules already fixed

### Renderer

- Vue 3 + Vuetify 3.
- Composition API and `<script setup lang="ts">`.
- No Options API in ordinary components.
- `v-row`/`v-col` responsive grids for primary layout.
- `v-hover` and transitions for meaningful interactive surfaces.
- Semantic colors and icons, not decorative random colors.
- Reduced-motion support is mandatory.
- The renderer never receives unrestricted Node.js, filesystem or process execution access.

### Desktop runtime

- Main process owns windows, native dialogs, OS integration, updates and privileged filesystem access.
- Preload exposes a narrow, typed, versioned IPC API.
- Long-running media work executes outside the renderer and normally outside the Electron main event loop.
- Database and job state use durable transactions.
- Source media is never modified in place by analysis or document editing.
- Active jobs can continue in the tray only through explicit lifecycle behavior.

### Product boundaries

- API-based generation is optional.
- Atlas and object detection are independent products inside the same workspace.
- The current repository's Releases may seed sample data, but raw data must pass explicit privacy and rights review.
- PDF export is a static document workflow; GIF animation is not promised inside PDF.
- Detector disagreement without human labels is not an accuracy benchmark.
- Application updates must preserve settings and projects through explicit schema migrations.
- App source being Apache-2.0 does not license third-party model weights or sample data.

## Definition of specification-ready

The specification can move from `specification_in_progress` to `implementation_ready` only when:

- every accepted module has an implementation milestone;
- all security-critical choices are accepted rather than open;
- packaging/updater and engine-runtime architecture are approved;
- the six required package targets have concrete build/update test plans;
- model artifact distribution has passed artifact-level license review;
- project and config schemas have stable versioning rules;
- the update and migration contract is approved;
- large-corpus performance budgets are measurable;
- every v1 capability has acceptance tests;
- unresolved questions are either answered or explicitly deferred beyond v1;
- accepted round amendments are consolidated into the numbered specifications.

Until then, the branch is a product-definition branch and must not be presented as a completed app.
