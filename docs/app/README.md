# Desktop Application Specification Index

This directory is the normative human-readable specification set for the `app-main` product line.

The desktop product is deliberately specified as a system of documents rather than a single monolithic proposal. The expected implementation may eventually contain tens of thousands of lines across Electron main/preload processes, Vue/Vuetify renderer code, worker runtimes, media pipelines, model adapters, database migrations, packaging scripts and platform-specific update logic. A one-file specification would become difficult to review, contradict and safely revise.

## Current status

- Product status: `specification_in_progress`
- Implementation status: `not_started`
- Specification baseline: `2026-07-22.1`
- Machine contract: [`../../app-product-contract.json`](../../app-product-contract.json)
- Long-lived product branch: `app-main`
- Target review model: iterative specification rounds with explicit user decisions

## Document map

| Document | Scope | Current state |
|---|---|---|
| [`00_PRODUCT_CHARTER.md`](00_PRODUCT_CHARTER.md) | Product intent, personas, local-first principles, scope boundaries and user journeys | Baseline defined |
| [`01_UX_DESIGN_SYSTEM.md`](01_UX_DESIGN_SYSTEM.md) | Vuetify 3 component rules, responsive layouts, hover, motion, accessibility and information architecture | Baseline defined |
| [`02_DESKTOP_ARCHITECTURE_AND_SECURITY.md`](02_DESKTOP_ARCHITECTURE_AND_SECURITY.md) | Electron processes, IPC, filesystem, workers, database, secrets and threat model | Baseline defined |
| [`03_DATA_PROJECT_AND_RELEASE_SPEC.md`](03_DATA_PROJECT_AND_RELEASE_SPEC.md) | Project schema, paths, import/export, mock corpus, Release assets and workflow inputs | Baseline defined |
| [`04_MEDIA_API_AUTOMATION_SPEC.md`](04_MEDIA_API_AUTOMATION_SPEC.md) | Agnes integration, API keys, execution policies, scheduling, retries, stop conditions and audit | Baseline defined |
| [`05_ATLAS_STUDIO_SPEC.md`](05_ATLAS_STUDIO_SPEC.md) | App-native Atlas pipeline, review UI, rich document editing, templates and PDF export | Baseline defined |
| [`06_DETECTION_STUDIO_SPEC.md`](06_DETECTION_STUDIO_SPEC.md) | Multi-model registry, model licensing, inference jobs, checkpoints, progress and comparison | Baseline defined |
| [`07_PERFORMANCE_AND_SCALE_SPEC.md`](07_PERFORMANCE_AND_SCALE_SPEC.md) | Thousands-of-assets architecture, thumbnails, virtualization, workers, caching and budgets | Baseline defined |
| [`08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md`](08_UPDATE_MIGRATION_AND_RECOVERY_SPEC.md) | Online/offline updates, signing, platform flows, settings migration, backup and rollback | Baseline defined |
| [`09_TESTING_RELEASE_AND_ACCEPTANCE.md`](09_TESTING_RELEASE_AND_ACCEPTANCE.md) | Test pyramid, cross-platform matrix, benchmark gates, Release verification and acceptance criteria | Baseline defined |
| [`10_ROADMAP_AND_DELIVERY_PLAN.md`](10_ROADMAP_AND_DELIVERY_PLAN.md) | Staged delivery plan, implementation gates and dependency ordering | Baseline defined |
| [`DECISIONS.md`](DECISIONS.md) | Accepted and provisional architecture/product decisions with rationale | Active |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | Questions for future discussion, defaults selected for now and impact of each answer | Active |
| [`REFERENCES.md`](REFERENCES.md) | Primary upstream references and dependency/licensing review checklist | Active |

## How future specification rounds work

Each review round should follow this sequence:

1. The user describes a desired capability, workflow, concern or preference.
2. The affected specification documents are updated rather than appending an isolated note.
3. New decisions receive stable IDs in `DECISIONS.md`.
4. Questions that still materially affect implementation are added to `OPEN_QUESTIONS.md` with a provisional default.
5. The machine contract is changed only when the invariant is stable enough to enforce.
6. Milestones and acceptance tests are synchronized.
7. Contradictions with the existing web/analysis product are called out explicitly.
8. The draft PR remains open until the user declares the specification ready for implementation.

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
- release and migration implications;
- acceptance criteria;
- unresolved questions.

## Implementation rules that are already fixed

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

### Product boundaries

- API-based generation is optional.
- Atlas and object detection are independent products inside the same workspace.
- The current repository's Releases may seed sample data, but personal/raw data must pass an explicit publication review.
- PDF export is a static document workflow; GIF animation is not promised inside PDF.
- Detector disagreement without human labels is not an accuracy benchmark.
- Application updates must preserve settings and projects through explicit schema migrations.

## Definition of specification-ready

The specification can move from `specification_in_progress` to `implementation_ready` only when:

- every accepted module has an implementation milestone;
- all security-critical choices are accepted rather than open;
- the first supported platform/package matrix is approved;
- model artifact distribution has passed license review;
- project and config schemas have stable versioning rules;
- the update and migration contract is approved;
- large-corpus performance budgets are measurable;
- every v1 capability has acceptance tests;
- unresolved questions are either answered or explicitly deferred beyond v1.

Until then, the branch is a product-definition branch and must not be presented as a completed app.