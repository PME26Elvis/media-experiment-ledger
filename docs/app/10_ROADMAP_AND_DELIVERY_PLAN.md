# 10 — Roadmap and Delivery Plan

## 1. Purpose

This roadmap converts the product specification into a dependency-aware sequence. It intentionally separates infrastructure, user workflows, analysis engines, document authoring, model expansion and release/update hardening.

The expected implementation may reach many tens of thousands of lines. Line count is not an acceptance metric; behavior, tests, recovery and platform evidence are.

## 2. Branch and PR strategy

- `app-main` is the long-lived desktop integration branch.
- Feature branches start from `app-main`.
- Use normal merge commits.
- Retain branches unless the user requests deletion.
- Each PR should be focused but complete: implementation, tests, schemas, migrations, docs and UI entry points remain synchronized.
- Specification PR stays draft/open during iterative definition.
- No app code is declared production-ready before platform package evidence.

## 3. Phase 0 — Specification convergence

### Goals

- Review first baseline with user.
- Resolve security-critical and product-shaping open questions.
- Expand requested modules.
- Stabilize v1 platform/package/model scope.
- Mark contract `implementation_ready`.

### Deliverables

- approved product charter;
- accepted architecture decisions;
- v1 feature matrix;
- stable project/config/job schemas;
- model artifact license plan;
- update/package plan;
- test/benchmark reference hardware;
- implementation issue/PR map.

### Exit criteria

- no open question blocks architecture/security;
- all v1 capabilities have acceptance tests;
- user approves first implementation milestone order;
- draft spec PR is ready for normal merge into `app-main` or remains as branch baseline by explicit choice.

## 4. Phase 1 — Secure application shell

### Scope

- Electron Forge/Vite scaffold after tool choice confirmation;
- Vue 3, Vuetify 3, TypeScript strict;
- Composition API `<script setup>` rules;
- routing, Pinia and i18n;
- light/dark/system themes;
- responsive shell/navigation;
- typed preload bridge;
- main-process security baseline;
- structured logging;
- global error/recovery shell;
- initial CI/type/lint/component/E2E.

### UI

- Workspace empty state;
- Settings shell;
- Job Shelf placeholder;
- Updates placeholder;
- responsive/hover/transition design tokens.

### Exit criteria

- renderer has no Node access;
- IPC allowlist tested;
- Windows/macOS/Linux development launch works;
- visual review at all breakpoints/themes;
- packaged smoke placeholder can launch.

## 5. Phase 2 — Project, database and asset foundation

### Scope

- global/per-project SQLite;
- project manifests and locks;
- path grants;
- create/open/rename/recent projects;
- image/video independent bindings;
- folder/file browse and reveal;
- drag-and-drop import preview;
- streaming index;
- media metadata and hashes;
- thumbnail pyramid;
- virtualized corpus browser;
- config import/export foundation;
- project export/import security.

### Exit criteria

- 10,000-image fixture opens responsively;
- source media remains unchanged;
- external path relink works;
- project restart restores state;
- configs support YAML/JSON and import TOML;
- archive traversal tests pass.

## 6. Phase 3 — Job supervisor and local engine protocol

### Scope

- durable job state machine;
- queue/priorities;
- progress aggregation;
- pause/resume/cancel;
- worker leases/heartbeats;
- engine protocol and packaged development engine;
- crash recovery;
- Job Center UI;
- logs/diagnostics/support bundle;
- resource presets/backpressure.

### Exit criteria

- worker crash does not crash shell;
- restart recovers a synthetic long job;
- checkpoint state is transactionally correct;
- renderer remains responsive;
- support bundle redacts secrets fixtures.

## 7. Phase 4 — Sample Corpus and Release infrastructure

### Scope

- sample corpus manifest/schema;
- data privacy/publication audit;
- multipart packaging under size boundary;
- resumable sample download;
- checksum/extraction/import;
- first-launch sample journey;
- app Release workflow inputs;
- notes/feature bullet generation;
- checksums/SBOM/notices;
- draft Release verification.

### Exit criteria

- user can install and run a meaningful workflow without API key;
- missing/corrupt sample part is detected;
- GitHub draft assets match manifest;
- personal/raw data review evidence exists.

## 8. Phase 5 — API Automation foundation and Agnes

### Scope

- secret profiles and safeStorage;
- `.env` compatibility;
- provider adapter API;
- current Agnes config importer;
- prompt editor/import;
- image/video run wizard;
- pacing/concurrency/retry/stop/circuit breaker;
- durable request records;
- download/decode verification;
- live run UI;
- fixture provider tests;
- real manual Agnes smoke.

### Exit criteria

- API key optional;
- secrets absent from renderer/log/export;
- submitted video job survives restart;
- 429/Retry-After and quota stop policies verified;
- archived success requires verified media;
- current script-compatible configs import correctly.

## 9. Phase 6 — Atlas Analysis

### Scope

- metadata mapping;
- image/video validation;
- cohort identity/seed policy;
- exact deduplication;
- temporal selection;
- primary/extended/full image evidence;
- video GIF/keyframe evidence;
- analysis fingerprint;
- resumable cohort rendering;
- result database/index;
- virtualized Atlas browser;
- filters/inspectors/exportable evidence.

### Exit criteria

- current repository-compatible Atlas fixture matches expected rules;
- image/video cohorts separate;
- all verified samples represented;
- restart skips verified cohorts;
- invalid/excluded items visible;
- 2,000-cohort benchmark meets budget.

## 10. Phase 7 — Atlas Document Studio and PDF

### Scope

- structured document schema;
- five built-in templates;
- rich text editor;
- block/page editor;
- page virtualization;
- static video representation;
- batch block/layout actions;
- undo/redo/autosave/revisions;
- print preview/preflight;
- isolated PDF renderer;
- manifest/evidence package.

### Exit criteria

- user edits font/size/bold/italic/underline/layout;
- template change preserves content;
- 500-page draft remains usable;
- crash recovery restores unsaved session;
- PDF has no overflow/missing media according to preflight;
- PDF and manifest hashes recorded.

## 11. Phase 8 — Detection Studio baseline

### Scope

- Model Manager;
- registry/manifest/license states;
- on-demand model download/hash verification;
- YOLOX-Tiny adapter;
- NanoDet-Plus-m-320 adapter;
- CPU ONNX Runtime;
- job wizard;
- per-item checkpoint;
- progress and resource diagnostics;
- normalized sidecars;
- overlays and result browser;
- exact two-model comparison;
- exports.

### Exit criteria

- real inference on every required platform;
- pause/restart/resume over large fixture;
- corrupt model rejected;
- original-coordinate boxes verified;
- comparison language guardrail enforced;
- Atlas outputs remain unchanged.

## 12. Phase 9 — Larger models and acceleration

### Scope

Subject to license/runtime review:

- YOLOX-S/M/L/X and optional Nano;
- NanoDet-Plus-m-416 and 1.5x variants;
- resource tiers/local benchmarks;
- optional CUDA/DirectML/CoreML providers;
- OOM fallback;
- provider-specific package/runtime validation;
- model registry update mechanism.

### Exit criteria

Per model/provider:

- artifact license accepted;
- immutable hash/source;
- real smoke/golden tests;
- resource metadata;
- cross-platform compatibility;
- safe fallback;
- user-visible download/notice.

Models may graduate independently.

## 13. Phase 10 — Updates, migrations and recovery

### Scope

- update manifests/channels;
- online update path for supported Windows/macOS package;
- Linux verified package flow;
- offline update import;
- running-job shutdown/checkpoint;
- global/project/config/credential migrations;
- backup/retention;
- Recovery Center;
- rollback guidance/mechanism;
- migration fixtures across versions.

### Exit criteria

- update from previous release on each supported package;
- settings/projects/credentials preserved;
- migration failure recovers from backup;
- wrong package blocked;
- Linux behavior accurately matches package capabilities;
- success not claimed until workspace verification.

## 14. Phase 11 — Production hardening and first stable Release

### Scope

- security review;
- dependency/SBOM/license review;
- full large-corpus benchmarks;
- accessibility audit;
- cross-platform install/uninstall/update matrix;
- crash/leak soak tests;
- sample corpus final review;
- documentation/onboarding/help;
- signing/notarization;
- Release workflow finalizer and evidence.

### Exit criteria

- all v1 contract acceptance criteria pass;
- required installers signed/notarized according to policy;
- actual GitHub assets verified;
- update path tested from prerelease candidate;
- known limitations documented;
- user approves stable publication.

## 15. Post-v1 candidate phases

- additional providers;
- custom report templates;
- ground-truth import and evaluation mode;
- user-supplied model wizard;
- GPU provider expansion;
- project sync/export integrations;
- remote worker execution;
- plugin SDK with signed declarative manifests;
- report publication to GitHub Releases;
- advanced semantic/media search.

## 16. Cross-phase invariants

Every phase must preserve:

- normal merge/no branch deletion preference;
- Traditional Chinese primary and English secondary UI;
- Vuetify responsive/hover/transition/accessibility rules;
- source media immutability;
- renderer privilege boundary;
- durable jobs for long operations;
- secret redaction;
- schema/migration discipline;
- large-corpus performance measurement;
- documentation and contract synchronization;
- no unsupported detector accuracy claims;
- no unverified Release/deployment claims.

## 17. Planning granularity

Before implementing each phase, create a phase plan containing:

- user stories;
- schema/API changes;
- file/module layout;
- migration impact;
- security review;
- test matrix;
- performance benchmark;
- PR sequence;
- release implications;
- explicit acceptance evidence.

The roadmap authorizes staged engineering but does not override unresolved decisions in `OPEN_QUESTIONS.md`.