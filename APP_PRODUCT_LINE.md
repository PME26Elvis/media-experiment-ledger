# Media Experiment Ledger Studio

> Product line branch: `app-main`  
> Public identity: **Media Experiment Ledger Studio**  
> Product descriptor: **Atlas · Detection · Media Automation**  
> Current phase: **specification in progress**  
> Implementation status: **not started**  
> Primary specification index: [`docs/app/README.md`](docs/app/README.md)

## Purpose

`app-main` is a new desktop-application product line for Media Experiment Ledger. It is not a wrapper around the current GitHub Pages site and it is not a wholesale replacement of the existing repository architecture. The app must independently reconsider every existing capability, decide whether it belongs in a local desktop workflow, and add the desktop-only functions required for data acquisition, project management, large-corpus analysis, document production, recovery, and long-term updates.

The product is intended to become a substantial cross-platform application rather than a small demonstration client. The first deliverable is therefore a versioned, testable and iteratively refinable specification system. Implementation must not begin by guessing around unresolved product decisions.

## Product definition

The desktop application will provide a local-first workspace for:

- importing or generating image and video corpora;
- optionally calling supported media-generation APIs, beginning with Agnes image and video endpoints;
- configuring high-volume API execution with explicit rate, retry, stop, budget and recovery policies;
- running Prompt Repeatability Atlas processing independently from object detection;
- selecting and running multiple object-detection models with resumable jobs;
- reviewing thousands of media items without loading full-resolution assets into the renderer;
- editing Atlas presentation text and layouts through a structured-first hybrid document editor;
- exporting polished, static-image Atlas documents to PDF;
- packaging, importing and exporting projects, configurations and reports;
- downloading both a small Quick Start corpus and a sanitized Full Research corpus from dedicated immutable data Releases;
- updating the application while preserving projects, settings, credentials and migration history;
- continuing long-running jobs in the system tray when the user explicitly chooses that behavior.

## Accepted round-two product decisions

The second specification round fixes these product-level invariants:

1. The public name is **Media Experiment Ledger Studio**, rather than using the generic short brand `MEL Studio` by itself.
2. The required first-stable package matrix includes:
   - Windows x64 NSIS installer;
   - Windows x64 portable build;
   - macOS arm64 DMG/update ZIP;
   - macOS x64 DMG/update ZIP;
   - Linux x64 AppImage;
   - Linux x64 `.deb`.
3. Sample data has two mandatory tiers: **Quick Start** and **Full Research**.
4. Sample corpora normally live in dedicated immutable data Releases; app Releases reference the approved corpus manifest/tag rather than re-uploading unchanged multi-gigabyte data.
5. Encrypted credential profiles are the default. Persistent file-backed `.env` profiles are an explicit expert option with plaintext warnings; there is no silent plaintext fallback.
6. Active API or analysis jobs may continue in the system tray. Closing the main window while work is active must offer keep-running, pause-and-quit, and cancel-and-quit choices.
7. Atlas Document Studio uses a structured default plus controlled freeform page mode and includes Traditional Chinese Academic and 16:9 Presentation Report templates in addition to the original five templates.
8. Detection v1 uses representative tiers rather than every model variant: YOLOX-Tiny/S/L and NanoDet-Plus-m-320/m-416/m-1.5x-416.
9. The app source and public binaries are open source under Apache-2.0. Model weights, generated sample data, fonts, icons and other third-party artifacts remain separately reviewed and may not be redistributed merely because the app itself is open source.

The normative detail is recorded in [`docs/app/SPECIFICATION_ROUND_02.md`](docs/app/SPECIFICATION_ROUND_02.md), [`docs/app/LICENSING_AND_DISTRIBUTION_POLICY.md`](docs/app/LICENSING_AND_DISTRIBUTION_POLICY.md), and [`app-product-contract.json`](app-product-contract.json).

## Non-negotiable frontend baseline

- Electron desktop application for Windows, macOS and Linux.
- Vue 3 Single-File Components.
- Vuetify 3 using current stable syntax at implementation time.
- Composition API everywhere, with `<script setup lang="ts">` for every Vue component unless a documented compiler limitation requires an exception.
- TypeScript strict mode.
- Responsive layout built with `v-container`, `v-row` and `v-col` rather than desktop-only fixed positioning.
- Meaningful Vuetify colors and icons on interactive controls, including `color="primary"`, `prepend-icon` and `append-icon` where semantically appropriate.
- `v-hover` interaction states and Vuetify or Vue transitions on cards, panels, drawers, dialogs, route changes and progressive disclosure.
- Motion must feel polished without slowing bulk operations, violating reduced-motion preferences or producing distracting continuous animation.

## Specification governance

The specification is intentionally split into focused documents. Each normative statement uses one of these levels:

- **MUST**: required for the relevant milestone to be accepted.
- **SHOULD**: expected unless an explicit architecture decision records a better alternative.
- **MAY**: optional or deferred capability.
- **MUST NOT**: prohibited because it conflicts with security, data integrity, performance or product intent.

Each product decision is also assigned a state:

- `accepted`: approved and implementation may rely on it.
- `provisional`: this specification selects a default so work can continue, but the decision remains easy to change.
- `open`: implementation must not irreversibly depend on it.
- `rejected`: explicitly excluded unless reopened through the decision log.

The machine-readable source for stable product invariants is [`app-product-contract.json`](app-product-contract.json). Human-readable detail lives under [`docs/app/`](docs/app/). When a decision changes, the contract, affected specifications, decision log, open-question register, milestones and acceptance criteria must be updated together.

## Branch policy

- `main` remains the existing web, analysis and Release product line.
- `app-main` is the long-lived integration branch for the desktop product line.
- Feature work branches from `app-main`, uses normal merge commits and remains preserved unless the user asks for deletion.
- The app may consume algorithms, schemas and test fixtures from `main`, but it must not silently inherit Web-specific assumptions.
- App Releases and sample-data packages use their own tag and asset namespace and must not mutate immutable experiment Releases.

## Implementation gate

Before production implementation begins, the specification must at minimum define:

1. product boundaries and user journeys;
2. desktop process architecture and IPC security;
3. project, asset, job and configuration schemas;
4. credential storage and API execution behavior;
5. Atlas Studio behavior and PDF export constraints;
6. Detection Studio model registry, licensing states and resumability;
7. large-corpus performance budgets;
8. packaging, Release, update, migration and rollback behavior;
9. platform-specific acceptance tests;
10. unresolved questions that require user decisions.

The current documents establish the first two review rounds. They are expected to be expanded before implementation is declared ready.
