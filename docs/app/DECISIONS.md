# Desktop Product Decision Log

This file records durable product and architecture decisions for the `app-main` product line. It prevents later specification rounds from silently contradicting earlier choices.

## Status vocabulary

- `accepted` — stable unless explicitly reopened.
- `provisional` — selected as the working default but still open to user revision.
- `open` — no implementation commitment may rely on one answer yet.
- `rejected` — excluded unless explicitly reopened.
- `superseded` — replaced by a later decision ID.

## Decision record format

Each decision includes:

- stable ID;
- status;
- date;
- decision;
- rationale;
- consequences;
- affected specifications;
- superseding/superseded relationship where relevant.

---

## Product and branch decisions

### APP-DEC-001 — Create a separate desktop product line

- Status: `accepted`
- Date: 2026-07-22
- Decision: The desktop application is developed on the long-lived `app-main` product-line branch rather than replacing the current `main` web/analysis architecture.
- Rationale: The desktop product has different runtime, security, storage, update, packaging and UX requirements. Treating it as a frontend framework replacement would preserve inappropriate browser assumptions.
- Consequences:
  - feature branches start from `app-main`;
  - the existing `main` product remains independently operable;
  - reuse occurs through explicit schemas/engine boundaries rather than direct renderer coupling;
  - app-specific Releases use distinct tags/assets.
- Affected: all app specifications.

### APP-DEC-002 — The first deliverable is a specification system

- Status: `accepted`
- Date: 2026-07-22
- Decision: The first app-main milestone contains detailed, versioned, machine-readable and human-readable specifications before production implementation.
- Rationale: The expected app is large enough that unstructured implementation would create contradictory behavior and migration debt.
- Consequences:
  - current implementation status remains `not_started`;
  - each specification round updates decisions, questions, contract, roadmap and acceptance criteria together;
  - implementation begins only after `implementation_ready` gate.
- Affected: `APP_PRODUCT_LINE.md`, `app-product-contract.json`, specification index.

### APP-DEC-003 — Local-first desktop workbench

- Status: `accepted`
- Date: 2026-07-22
- Decision: The app is a local-first project/workspace application for import, optional generation, Atlas, detection, report authoring and reproducible evidence.
- Rationale: Atlas and detection must work on user-selected data without requiring a hosted backend or API key.
- Consequences:
  - offline projects remain usable;
  - network access is action-specific;
  - no mandatory account service;
  - large local storage and migration are first-class.
- Affected: Product Charter, Data/Project, Architecture, Updates.

### APP-DEC-004 — API generation is optional

- Status: `accepted`
- Date: 2026-07-22
- Decision: A user can install the app, obtain/import sample data and run analysis without configuring Agnes or any API provider.
- Rationale: The app is an analysis product as well as an automation client.
- Consequences:
  - onboarding has import/sample/provider paths;
  - missing credentials are an empty state, not an application error;
  - test/sample corpus is a release requirement.
- Affected: Product Charter, API Automation, Sample Corpus.

### APP-DEC-005 — Product-facing name remains provisional

- Status: `provisional`
- Date: 2026-07-22
- Decision: Use “Media Experiment Ledger Desktop” and slug `media-experiment-ledger-desktop` until the user selects a final public product name.
- Rationale: A stable internal name is needed for specs and artifact examples, but branding is not yet approved.
- Consequences:
  - schemas use stable IDs independent of display name;
  - package/release names may change before implementation;
  - migration should not key data identity solely to brand text.
- Affected: Product Charter, Release spec, Open Question APP-Q-001.

---

## Frontend and UX decisions

### APP-DEC-010 — Vue 3 and Vuetify 3 renderer

- Status: `accepted`
- Date: 2026-07-22
- Decision: The Electron renderer uses Vue 3 and current stable Vuetify 3 syntax at implementation start.
- Rationale: Explicit user requirement and suitable desktop-responsive component ecosystem.
- Consequences:
  - no React/Angular renderer alternate in v1;
  - dependency versions are pinned at implementation/release time;
  - upgrades require visual and component regression tests.
- Affected: UX Design System, Architecture, Testing.

### APP-DEC-011 — Composition API and `<script setup lang="ts">`

- Status: `accepted`
- Date: 2026-07-22
- Decision: Ordinary Vue components use Composition API and `<script setup lang="ts">`; Options API is prohibited except a documented tooling limitation.
- Rationale: Explicit user requirement and consistent typed composable architecture.
- Consequences:
  - component lint/static rules enforce this convention;
  - reusable behavior uses typed composables;
  - exceptions require decision-log entry.
- Affected: UX Design System, Testing.

### APP-DEC-012 — Vuetify RWD grid is mandatory

- Status: `accepted`
- Date: 2026-07-22
- Decision: Primary route layouts use `v-container`, `v-row` and `v-col` and must remain functionally complete in narrow windows.
- Rationale: Explicit user requirement and need for desktop-window resizing/touch devices.
- Consequences:
  - fixed desktop-only macro layouts are rejected;
  - wide and narrow acceptance screenshots/tests are mandatory;
  - inspectors/tables adapt to sheets/cards when needed.
- Affected: UX Design System, Testing.

### APP-DEC-013 — Semantic color, icons, hover and transitions are required

- Status: `accepted`
- Date: 2026-07-22
- Decision: Interactive controls use semantic Vuetify colors/icons; meaningful cards use `v-hover`; route/panel/state changes use transitions.
- Rationale: Explicit user requirement for a high-quality premium interaction layer.
- Consequences:
  - hover cannot be the only access path;
  - focus/touch equivalents required;
  - reduced-motion mode required;
  - visual polish is acceptance-tested rather than decorative afterthought.
- Affected: UX Design System, Testing.

### APP-DEC-014 — Structured information density over hidden evidence

- Status: `accepted`
- Date: 2026-07-22
- Decision: Complex evidence is managed through tabs, filters, grouping, virtualized views and inspectors rather than omitted to shorten pages.
- Rationale: Matches existing user preference and analytical product purpose.
- Consequences:
  - pages may be information-rich;
  - performance architecture must support density;
  - empty/error/provenance states are explicit.
- Affected: UX, Atlas, Detection, Performance.

### APP-DEC-015 — Pinia and Vue Router

- Status: `provisional`
- Date: 2026-07-22
- Decision: Use Vue Router for routes and Pinia for small renderer/session/view state.
- Rationale: Mainstream Vue 3 choices; the database remains canonical for large datasets.
- Consequences:
  - Pinia must not hold entire corpora, raw detections or secrets;
  - may be revisited before scaffold if a better maintained solution exists.
- Affected: Architecture, Performance, Open Question APP-Q-018.

---

## Electron architecture and security decisions

### APP-DEC-020 — Electron desktop runtime

- Status: `accepted`
- Date: 2026-07-22
- Decision: Use Electron for Windows, macOS and Linux desktop packages.
- Rationale: Explicit user requirement and need for native dialogs, filesystem integration, packaging and update flows with a Vue/Vuetify renderer.
- Consequences:
  - Chromium/Node/Electron update cadence is security-relevant;
  - native dependencies require ABI/platform builds;
  - package sizes are accepted as a tradeoff for capability.
- Affected: Architecture, Packaging, Updates.

### APP-DEC-021 — Electron Forge + Vite baseline

- Status: `provisional`
- Date: 2026-07-22
- Decision: Start implementation with Electron Forge and Vite integration unless implementation-start review finds a stronger current stable option.
- Rationale: Mainstream Electron packaging/scaffold with current project familiarity.
- Consequences:
  - exact makers/updater depend on final platform choices;
  - do not pin versions during specification phase;
  - revisit in APP-Q-002/003.
- Affected: Architecture, Roadmap.

### APP-DEC-022 — Renderer is unprivileged

- Status: `accepted`
- Date: 2026-07-22
- Decision: Production windows use Node integration off, context isolation on, sandbox where compatible, restrictive CSP and deny-by-default navigation.
- Rationale: Electron security boundary.
- Consequences:
  - renderer cannot directly use filesystem, secrets, shell or process spawn;
  - privileged actions go through typed preload/main validation;
  - remote web content cannot share privileged renderer context.
- Affected: Architecture, Testing.

### APP-DEC-023 — Typed allowlisted preload API

- Status: `accepted`
- Date: 2026-07-22
- Decision: Preload exposes explicit versioned methods, never a generic channel invocation API.
- Rationale: Prevent arbitrary privileged IPC and keep contracts testable.
- Consequences:
  - runtime schemas required on IPC boundaries;
  - every event subscription is bounded/unsubscribable;
  - API compatibility has a version.
- Affected: Architecture, Testing.

### APP-DEC-024 — Durable job supervisor

- Status: `accepted`
- Date: 2026-07-22
- Decision: Every long-running import, generation, hashing, Atlas, detection, model, PDF and migration operation is a durable job with checkpoints and recovery.
- Rationale: Jobs may last hours/days and must survive navigation/restart/crash.
- Consequences:
  - button spinners are not a substitute for job state;
  - final success follows verification, not progress 100%;
  - database state precedes renderer notifications.
- Affected: all functional modules.

### APP-DEC-025 — Versioned local engine boundary

- Status: `accepted`
- Date: 2026-07-22
- Decision: Heavy media and inference work executes behind a supervised, versioned local engine protocol outside the renderer and main event loop.
- Rationale: Reuse existing verified algorithms while isolating CPU/native work and future implementation languages.
- Consequences:
  - structured protocol and heartbeats;
  - binary media exchanged by validated paths/tokens;
  - engine crashes are isolated;
  - language rewrite requires golden equivalence.
- Affected: Architecture, Atlas, Detection, Testing.

### APP-DEC-026 — Hybrid packaged engine implementation

- Status: `provisional`
- Date: 2026-07-22
- Decision: Initially allow packaged Python components for verified existing pipelines plus Node/native workers where appropriate; users do not install Python.
- Rationale: Avoid risky full rewrite before equivalence while retaining future optimization path.
- Consequences:
  - platform-specific engine packaging/build size;
  - Python runtime/license/SBOM review;
  - protocol prevents permanent language coupling.
- Affected: Architecture, Roadmap, Open Question APP-Q-017.

---

## Data, paths and configuration decisions

### APP-DEC-030 — SQLite project database and JSON manifest

- Status: `accepted`
- Date: 2026-07-22
- Decision: Use SQLite for durable indexed state and a human-inspectable JSON project manifest.
- Rationale: Large filtered datasets, transactions and migrations require a database; project identity/path metadata should remain explicit.
- Consequences:
  - binaries are stored as files, not ordinary DB blobs;
  - DB schema and manifest schema version separately;
  - project locks prevent concurrent writers.
- Affected: Data/Project, Architecture, Performance, Updates.

### APP-DEC-031 — Independent media and output paths

- Status: `accepted`
- Date: 2026-07-22
- Decision: Image input, video input, generated outputs, Atlas output, detection output, report output, cache and model roots are separately configurable with reasonable defaults.
- Rationale: Explicit user requirement and separation of analysis domains.
- Consequences:
  - changing one path never silently moves others;
  - every path has browse/reveal/validation;
  - missing external paths use relink workflow.
- Affected: Data/Project, UX.

### APP-DEC-032 — Drag-and-drop with containing-directory choice

- Status: `accepted`
- Date: 2026-07-22
- Decision: Files/folders can be dropped; dropping a file offers selected-file import, containing-directory scan or directory binding, but never scans the directory silently.
- Rationale: Explicit user request with privacy/performance safety.
- Consequences:
  - drop payload is validated in main process;
  - import preview precedes work.
- Affected: Data/Project, UX, Security.

### APP-DEC-033 — YAML canonical editable config, JSON interchange

- Status: `accepted`
- Date: 2026-07-22
- Decision: YAML is primary human-editable config; import supports YAML/YML/JSON/TOML; v1 export supports YAML/JSON.
- Rationale: Readability/comments plus deterministic machine interchange.
- Consequences:
  - import is previewed/migrated before apply;
  - UI explicitly displays supported formats;
  - config folders have reveal actions.
- Affected: Data/Project, API Automation.

### APP-DEC-034 — Source media is immutable

- Status: `accepted`
- Date: 2026-07-22
- Decision: Analysis, detection, document editing and cache generation never modify source media in place.
- Rationale: Data integrity and user trust.
- Consequences:
  - annotations/proxies/results use derived directories;
  - project deletion distinguishes external source files;
  - tests verify hashes before/after workflows.
- Affected: all media modules.

---

## Secrets and API decisions

### APP-DEC-040 — OS-backed encrypted credential profiles

- Status: `accepted`
- Date: 2026-07-22
- Decision: Credential values are encrypted through Electron safeStorage/OS credential facilities and are not persisted in ordinary project/config files.
- Rationale: API keys require stronger treatment than general configuration.
- Consequences:
  - renderer receives masked metadata, not decrypted list values;
  - Linux backend absence must not silently fall back to plaintext;
  - app identity/signing affects credential migration.
- Affected: Architecture, API Automation, Updates.

### APP-DEC-041 — `.env` interoperability, not default vault

- Status: `accepted`
- Date: 2026-07-22
- Decision: `.env` can be imported, optionally edited in explicit file-backed mode and exported through a warning flow; encrypted profiles are the preferred internal storage.
- Rationale: User wants direct file management but plaintext storage must be transparent.
- Consequences:
  - ordinary config export contains references only;
  - secret-bearing export is explicit;
  - exact persistent file-backed defaults remain in APP-Q-006.
- Affected: Architecture, API Automation.

### APP-DEC-042 — Agnes is the initial provider

- Status: `accepted`
- Date: 2026-07-22
- Decision: First provider supports Agnes image and video generation and imports the repository's existing YAML/JSONL configuration.
- Rationale: Existing working script/data and explicit user request.
- Consequences:
  - provider adapter isolates endpoints/response schema;
  - current stop/error/rate behavior is preserved and expanded;
  - API tests use a local fixture provider; live credentials never run on untrusted PRs.
- Affected: API Automation, Testing.

### APP-DEC-043 — Explicit multi-key policy only

- Status: `accepted`
- Date: 2026-07-22
- Decision: Multiple credentials may be configured, but key rotation/fallback never occurs invisibly; the selected policy appears in run review/history.
- Rationale: Cost, quota and audit implications.
- Consequences:
  - fixed/fallback/round-robin/weighted are explicit modes;
  - auth failures quarantine profiles according to policy;
  - no secret value appears in run logs.
- Affected: API Automation.

---

## Sample data and Release decisions

### APP-DEC-050 — Curated multipart sample corpus

- Status: `accepted`
- Date: 2026-07-22
- Decision: App Releases or a dedicated data Release provide a reviewed Media Experiment Ledger Sample Corpus split by media type and zero-padded parts.
- Rationale: Users need real data without API keys.
- Consequences:
  - parts are independently resumable/verifiable;
  - manifest/checksums required;
  - personal/raw data passes explicit privacy/licensing review.
- Affected: Data/Release, Roadmap, Testing.

### APP-DEC-051 — 1.9 GB per sample part

- Status: `accepted`
- Date: 2026-07-22
- Decision: Default hard target is at most 1,900,000,000 bytes per sample part, leaving margin below a 2 GB boundary.
- Rationale: Avoid edge failures and support multipart distribution.
- Consequences:
  - deterministic partitioning;
  - manifest records compressed/uncompressed sizes;
  - app may download image/video subsets.
- Affected: Data/Release, contract.

### APP-DEC-052 — Same Release by default, dedicated data Release allowed

- Status: `provisional`
- Date: 2026-07-22
- Decision: Attach the selected sample corpus to the same app Release by default, but allow an immutable dedicated corpus Release when size or cadence makes this preferable.
- Rationale: Same Release is discoverable; dedicated data avoids repeated huge uploads.
- Consequences:
  - app consumes manifest URLs rather than hard-coded same-tag assumptions;
  - user decision requested in APP-Q-004.
- Affected: Data/Release.

### APP-DEC-053 — Manual Release workflow with rich inputs

- Status: `accepted`
- Date: 2026-07-22
- Decision: GitHub Actions must support manual app Release dispatch with optional Markdown notes, feature list converted to bullets, platform toggles, prerelease/draft and sample-data parameters.
- Rationale: Explicit user request and prior repository workflow preference.
- Consequences:
  - input validation before builds;
  - finalizer verifies GitHub-side assets;
  - package table, migration notes, manifests, checksums and SBOM in Notes.
- Affected: Data/Release, Testing.

---

## Atlas decisions

### APP-DEC-060 — Atlas is independently respecified

- Status: `accepted`
- Date: 2026-07-22
- Decision: App implementers must follow the app Atlas specification and not assume they will infer all behavior from the existing web Atlas.
- Rationale: The desktop product adds local inputs, durable jobs, editing and PDF authoring.
- Consequences:
  - image/video validation, cohorts, selections and evidence are restated;
  - compatibility tests may compare existing outputs.
- Affected: Atlas Studio.

### APP-DEC-061 — Analysis snapshot is immutable; document is editable

- Status: `accepted`
- Date: 2026-07-22
- Decision: Atlas analysis evidence is an immutable fingerprinted snapshot; rich report drafts reference it and may change wording/layout without rewriting evidence.
- Rationale: Separate scientific provenance from presentation edits.
- Consequences:
  - document schema/revisions separate from analysis schema;
  - source media remains unchanged;
  - report manifest identifies snapshot/fingerprint.
- Affected: Atlas Studio, Updates.

### APP-DEC-062 — Static PDF only for animated/video evidence in v1

- Status: `accepted`
- Date: 2026-07-22
- Decision: Exported PDF uses selected poster frames/contact sheets for GIF/video; it does not promise animation.
- Rationale: PDF animation portability is unreliable and user explicitly allowed GIF omission/static handling.
- Consequences:
  - editor requires static representation choice;
  - export preflight blocks unresolved animated media;
  - manifest records timestamps/representation.
- Affected: Atlas Studio, Testing.

### APP-DEC-063 — Structured block document editor

- Status: `provisional`
- Date: 2026-07-22
- Decision: Use a structured block/page document model rather than unrestricted desktop-publishing canvas as the v1 foundation.
- Rationale: Better pagination, batch operations, migrations, accessibility and deterministic PDF for large reports.
- Consequences:
  - precise freeform positioning is limited unless later added as a controlled block mode;
  - user confirmation requested in APP-Q-010.
- Affected: Atlas Studio.

### APP-DEC-064 — Five built-in templates

- Status: `provisional`
- Date: 2026-07-22
- Decision: Initial concepts are Research Light, Editorial Dark, Gallery Minimal, Technical Audit and Executive Review.
- Rationale: Covers scientific, premium, image-forward, evidence-heavy and concise use cases.
- Consequences:
  - names/styles may be revised;
  - custom template import deferred until schema security is defined.
- Affected: Atlas Studio, APP-Q-011.

---

## Detection decisions

### APP-DEC-070 — Detection is independent from Atlas

- Status: `accepted`
- Date: 2026-07-22
- Decision: Detection and Atlas have separate jobs, indexes, outputs and failure domains; joining is by stable image SHA-256 only.
- Rationale: Explicit user requirement and existing repository non-regression principle.
- Consequences:
  - detector work cannot mutate Atlas evidence/history;
  - either module may be absent.
- Affected: Detection, Atlas, contract.

### APP-DEC-071 — Required baseline model families

- Status: `accepted`
- Date: 2026-07-22
- Decision: v1 baseline supports YOLOX-Tiny and NanoDet-Plus-m-320 with real ONNX Runtime execution.
- Rationale: Current repository production models and explicit user requirement.
- Consequences:
  - each requires immutable artifact identity, adapter, labels, smoke/golden tests and license status;
  - CPU is universal baseline.
- Affected: Detection, Testing.

### APP-DEC-072 — Larger model candidates are gated

- Status: `accepted`
- Date: 2026-07-22
- Decision: YOLOX Nano/S/M/L/X and NanoDet-Plus m-416/1.5x candidates are not stable-supported until each passes artifact-license, runtime, resource and golden-output review.
- Rationale: Code repository license alone may not settle every pretrained weight/distribution question.
- Consequences:
  - registry can list `needs-review` but stable UI cannot install as verified;
  - variants graduate independently;
  - user prioritization requested in APP-Q-013.
- Affected: Detection, References.

### APP-DEC-073 — Conservative model artifact distribution

- Status: `provisional`
- Date: 2026-07-22
- Decision: Prefer download-on-demand or user-supplied weights until bundling rights are explicitly documented.
- Rationale: Avoid packaging/license risk and reduce installer size.
- Consequences:
  - first-run Model Manager download;
  - offline model package workflow may be needed;
  - user preference requested in APP-Q-012.
- Affected: Detection, Release.

### APP-DEC-074 — Item-level durable checkpoints

- Status: `accepted`
- Date: 2026-07-22
- Decision: Detection persists verified completion per image/model plus durable stage metadata.
- Rationale: Thousands of images and expensive models require restart without full rerun.
- Consequences:
  - compatibility hashes determine reuse;
  - pause completes safe in-flight boundary;
  - corrupt/ambiguous outputs rerun.
- Affected: Detection, Performance, Testing.

### APP-DEC-075 — No accuracy claims without ground truth

- Status: `accepted`
- Date: 2026-07-22
- Decision: Unlabeled generated media reports agreement/disagreement, detections, IoU/class/runtime—not accuracy/precision/recall/mAP.
- Rationale: Scientific correctness.
- Consequences:
  - language guardrail tested;
  - future labeled evaluation is a separate mode.
- Affected: Detection, Reports.

---

## Performance decisions

### APP-DEC-080 — 10,000 image / 1,000 video design corpus

- Status: `accepted`
- Date: 2026-07-22
- Decision: Initial mandatory scale benchmark is 10,000 images and 1,000 videos plus large analysis/result/document fixtures.
- Rationale: Avoid demo-scale architecture and directly address user concern about thousands of images.
- Consequences:
  - all large views require virtualization/pagination;
  - CI/nightly generates benchmark fixtures;
  - reference hardware thresholds still open.
- Affected: Performance, Testing.

### APP-DEC-081 — Display-pixel-aware proxy pyramid

- Status: `accepted`
- Date: 2026-07-22
- Decision: Generate multiple image/video proxy levels and load the smallest level sufficient for rendered CSS pixels × device-pixel ratio/zoom.
- Rationale: Mature approach to prevent full-resolution eager decode while preserving visible quality.
- Consequences:
  - proxy cache keyed by source hash and transform version;
  - originals load only for export/high zoom;
  - offscreen requests cancel.
- Affected: Performance, Atlas, Detection, UX.

### APP-DEC-082 — Database pagination and bounded caches

- Status: `accepted`
- Date: 2026-07-22
- Decision: Large result sets use indexed/keyset-paginated DB queries; memory/disk caches and worker queues have explicit budgets/backpressure.
- Rationale: Renderer memory must not grow linearly with corpus size.
- Consequences:
  - no unbounded corpus arrays in Pinia;
  - low disk pauses jobs safely;
  - cache eviction distinguishes evidence from regenerable cache.
- Affected: Performance, Architecture.

---

## Update and migration decisions

### APP-DEC-090 — User data lives outside app installation

- Status: `accepted`
- Date: 2026-07-22
- Decision: Projects, settings, credentials, models and caches remain outside replaceable application binaries.
- Rationale: Updates must not require manual reconfiguration or risk uninstall data loss.
- Consequences:
  - install/uninstall semantics documented;
  - package identity changes require migration plan.
- Affected: Updates, Data/Project.

### APP-DEC-091 — Online and offline update flows

- Status: `accepted`
- Date: 2026-07-22
- Decision: Support online update discovery/install where platform/package permits and verified user-imported offline update packages/files.
- Rationale: Explicit user request and need for flexible distribution.
- Consequences:
  - update manifest and package validation;
  - platform-specific handoff;
  - manual fallback always available.
- Affected: Updates, Release.

### APP-DEC-092 — Transactional migrations with backup/recovery

- Status: `accepted`
- Date: 2026-07-22
- Decision: Schema migrations are versioned, backed up, transactional/resumable and enter Recovery Center on failure.
- Rationale: Users should not manually transfer settings or risk irreversible corruption.
- Consequences:
  - migration fixtures for supported upgrade floor;
  - update success only after workspace verification;
  - downgrade is not silently supported.
- Affected: Updates, Testing.

### APP-DEC-093 — Linux updater capability is package-specific

- Status: `accepted`
- Date: 2026-07-22
- Decision: Do not assume Windows/macOS-style built-in auto-update on Linux; provide verified AppImage/package flows and manual fallback.
- Rationale: Electron auto-update platform support and Linux package diversity.
- Consequences:
  - UI explains exact package behavior;
  - `.deb` may hand off to package manager;
  - AppImage replacement requires validated mechanism.
- Affected: Updates, Packaging.

---

## Rejected baseline approaches

### APP-DEC-100 — Replace the existing web frontend and call it the app

- Status: `rejected`
- Date: 2026-07-22
- Reason: Does not address desktop storage, jobs, secrets, local processing, updates or packaging.

### APP-DEC-101 — Mandatory API key onboarding

- Status: `rejected`
- Date: 2026-07-22
- Reason: Conflicts with optional generation and sample/local analysis workflows.

### APP-DEC-102 — Plaintext secret fallback without explicit user choice

- Status: `rejected`
- Date: 2026-07-22
- Reason: Security risk; Linux/backend limitations must be disclosed and handled explicitly.

### APP-DEC-103 — Renderer direct filesystem/process/secret access

- Status: `rejected`
- Date: 2026-07-22
- Reason: Violates Electron security boundary.

### APP-DEC-104 — Eagerly load/decode all original media

- Status: `rejected`
- Date: 2026-07-22
- Reason: Cannot meet large-corpus responsiveness/memory goals.

### APP-DEC-105 — Claim animated GIF support inside ordinary PDF

- Status: `rejected`
- Date: 2026-07-22
- Reason: Use explicit static representation and preserve interactive evidence separately.

### APP-DEC-106 — Treat model disagreement as accuracy

- Status: `rejected`
- Date: 2026-07-22
- Reason: No ground truth.

### APP-DEC-107 — Execute imported project/config/model code

- Status: `rejected`
- Date: 2026-07-22
- Reason: Imported content is data; adapters/plugins must be trusted shipped code.