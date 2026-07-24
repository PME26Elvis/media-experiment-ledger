# v1 TDD and Specification-Driven Development Engineering Policy

Status: **accepted and release-blocking**  
Applies to: all Media Experiment Ledger Studio v1 implementation

## 1. Objective

The v1 application is intentionally large. Quality cannot depend on manual memory, optimistic smoke tests or a late stabilization phase. Development MUST be driven by versioned specifications and executable tests from the first commit.

The project uses both:

- **SDD — Specification-Driven Development:** requirements, schemas, state machines, failure behavior and acceptance criteria are defined before implementation;
- **TDD — Test-Driven Development:** for deterministic domain and boundary behavior, failing tests are written before production code, then implementation is added and refactored while tests remain green.

The goal is not test-count inflation. The goal is traceable evidence that every important behavior, interruption path and platform artifact works as specified.

## 2. Requirement traceability

Every v1 capability MUST have stable requirement IDs.

Required chain:

```text
Product decision
  -> requirement ID
  -> acceptance scenario/test ID
  -> implementation module
  -> CI evidence
  -> release manifest entry
```

Each feature PR MUST include a traceability section listing:

- decisions affected;
- requirement IDs implemented;
- test IDs added/updated;
- schemas/migrations changed;
- platform artifacts affected;
- unresolved deviations, which require an explicit spec update.

No feature may be declared complete from prose alone.

## 3. Development loop

### 3.1 Specification first

Before code:

1. identify or add requirement IDs;
2. define success, empty, loading, offline, invalid, cancelled, interrupted and recovery states;
3. define persistent schema/version implications;
4. define security and privacy boundaries;
5. define performance budget;
6. define platform differences;
7. define acceptance tests.

### 3.2 Red

Add a test or executable contract that fails for the intended reason. A test that fails because the environment is broken does not count.

### 3.3 Green

Implement the smallest coherent production behavior that satisfies the requirement without violating architecture boundaries.

### 3.4 Refactor

Improve naming, decomposition, performance and reuse while preserving observable behavior. Refactoring MUST NOT silently broaden permissions, persistence or network access.

### 3.5 Integrate

Run affected local suites, then the required CI matrix. Update docs, schemas, notices, generated clients and golden fixtures in the same focused PR.

## 4. Test stack

### 4.1 TypeScript domain and process tests

Use Vitest for:

- pure domain logic;
- config normalization;
- state machines;
- update policy;
- job scheduling;
- path rules;
- manifest generation;
- release naming;
- permission decisions;
- cache/query keys;
- serialization and migration helpers.

Use fake timers and deterministic random/clock providers rather than relying on wall-clock sleeps.

### 4.2 Vue/Vuetify component tests

Use Vitest and Vue Test Utils for:

- Composition API components;
- Vuetify forms and validation;
- semantic color/icon states;
- `v-hover` interactions;
- transitions and reduced-motion behavior;
- keyboard/focus behavior;
- responsive breakpoints;
- empty/loading/error/recovery states;
- localization rendering.

Tests SHOULD assert user-observable roles, names, text and state rather than fragile internal CSS structure.

### 4.3 Query/state tests

Pinia stores and TanStack Vue Query integration MUST be tested for:

- bounded cache behavior;
- cancellation;
- stale/invalidation rules;
- project switching;
- sensitive-data non-persistence;
- pagination and stable query keys;
- offline and reconnect behavior;
- prevention of whole-corpus reactive loading.

### 4.4 IPC contract tests

Every preload-exposed IPC method/event MUST have:

- request and response schema tests;
- invalid payload rejection;
- permission/capability tests;
- cancellation tests;
- timeout tests;
- renderer isolation tests;
- backwards/forwards protocol compatibility tests where versioned.

There MUST be no untested IPC channel in a release artifact.

### 4.5 Electron main/preload integration tests

Test:

- BrowserWindow security options;
- CSP and navigation blocking;
- native dialog adapters;
- file capability tokens;
- external URL confirmation;
- tray lifecycle;
- scheduler/helper installation;
- update events;
- single-instance behavior;
- crash recovery and restart handoff.

### 4.6 Python engine tests

Use pytest plus property-based testing where useful for:

- Atlas cohort identity;
- media validation;
- deterministic selection;
- model preprocessing/postprocessing;
- NMS;
- checkpoints;
- job protocol;
- hashes/manifests;
- PDF frame extraction;
- config parsing;
- provider fallback;
- fault handling.

Existing production fixtures MUST be preserved as golden tests. Tests MUST use real image/video decode and real ONNX inference for representative paths, not only mocks.

### 4.7 Engine protocol contract tests

Generate shared protocol schemas and test both implementations against the same fixtures.

Required cases:

- handshake/version negotiation;
- heartbeat;
- normal completion;
- progress aggregation;
- cancellation;
- pause/checkpoint/resume;
- process crash;
- malformed/oversized message;
- staged-file capability expiration;
- incompatible engine version;
- log redaction.

### 4.8 GPU/provider tests

Each required execution provider MUST run real tests on appropriate hardware before stable release:

- CPU all platforms;
- DirectML Windows;
- CUDA Windows and Linux;
- CoreML arm64 and Intel macOS where supported.

Tests compare output to CPU golden results within model-specific tolerances and verify fallback when provider initialization, allocation or inference fails.

### 4.9 Electron end-to-end tests

Use Playwright Electron automation for user journeys including:

- onboarding and project creation;
- Quick Start corpus download/import;
- drag/drop and folder selection;
- credential creation/vault lock/unlock;
- Agnes dry-run/fake-provider execution;
- Atlas build and document editing;
- detection run, pause, kill, restart and resume;
- model/runtime pack installation;
- PDF export;
- GitHub Release draft publication against a test repository;
- updater UI;
- migration/recovery center;
- cloud-folder sync conflicts;
- scheduler/helper registration.

Native dialogs MUST be replaced through deterministic main-process test adapters rather than requiring human interaction.

### 4.10 Visual regression

Capture required screens at:

- desktop wide;
- desktop narrow;
- minimum supported window;
- light and dark themes;
- reduced motion;
- all five required locales;
- key loading/error/empty/progress states.

Golden updates require explicit review. Pixel tests do not replace semantic/accessibility tests.

### 4.11 Accessibility tests

Automated checks MUST cover:

- keyboard-only operation;
- focus order and visibility;
- accessible names/descriptions;
- contrast;
- reduced motion;
- screen-reader semantics;
- dialog focus trapping/return;
- progress announcements;
- high zoom and text scaling.

Manual accessibility review remains required for major flows before stable release.

## 5. Migration and recovery testing

Every persistent schema change MUST include:

- forward migration test;
- idempotence test;
- interrupted migration test;
- backup creation/validation test;
- rollback/recovery test;
- old-version fixture compatibility;
- unknown-newer-version refusal test.

Stable v1 release candidates MUST test migration from every public prerelease schema and at least the three most recent supported stable schema generations once they exist.

Projects, credential profiles, report documents, model registries, templates, scheduler definitions and sync journals all require independent schema fixtures.

## 6. Fault injection

CI and/or dedicated integration suites MUST deliberately test:

- Electron renderer crash;
- main-process termination;
- Python engine kill;
- machine/app restart during jobs;
- disk full;
- read-only destination;
- removed external drive;
- corrupted ZIP/ONNX/image/video/database/update package;
- network interruption and timeout;
- HTTP 401/402/403/408/409/429/5xx;
- truncated provider response;
- hash mismatch;
- wrong vault password and tampering;
- expired GitHub token;
- update signature mismatch;
- cloud sync conflict and partial upload;
- GPU out-of-memory/provider load failure.

A recovery claim is invalid until the corresponding interruption has been executed in a test.

## 7. Performance testing

The benchmark suite MUST include:

- 10,000 images;
- 1,000 videos;
- multiple Atlas snapshots;
- six detector variants/models as specified;
- hundreds of thousands of boxes;
- 500-page report project;
- multi-gigabyte corpus archives;
- SSD and HDD scenarios.

Measure:

- launch/project-open time;
- index time and resumability;
- scroll frame stability;
- renderer/main/engine memory;
- thumbnail latency/cache hit rate;
- query latency;
- IPC event rate;
- CPU/GPU utilization;
- provider inference throughput;
- PDF export time/memory;
- sync/update/migration duration;
- cancellation responsiveness.

Performance regressions beyond an approved budget fail CI or release qualification.

## 8. Security testing

Required:

- dependency and license scanning;
- SBOM generation/verification;
- secret scanning;
- CSP/navigation tests;
- IPC fuzz/property tests;
- archive path traversal tests;
- symlink/path escape tests;
- template/adaptor schema abuse tests;
- WASM capability/resource-limit tests;
- update signature/tamper tests;
- vault cryptographic envelope tests;
- permission-minimization tests;
- release artifact malware scanning where infrastructure permits.

Security-critical code MUST receive focused review and mutation testing.

## 9. Coverage and mutation gates

Minimum release gates:

- TypeScript global statement/line coverage: 90%;
- TypeScript global branch coverage: 85%;
- Python global line coverage: 90%;
- critical security, migration, checkpoint, update, vault and protocol modules: 95% branch coverage or complete decision-table coverage where branch metrics are misleading;
- 100% of public IPC methods represented in contract tests;
- 100% of migration steps represented by old/new fixtures;
- mutation score target of at least 80% for selected critical deterministic modules.

Coverage exclusions require written justification and MUST NOT hide generated code that contains business behavior.

## 10. CI structure

### Fast PR tier

- formatting/lint/typecheck;
- schema/code generation consistency;
- TypeScript/Python unit tests;
- component tests;
- IPC contracts;
- selected engine real-smoke tests;
- license/secret checks;
- docs/contract validation.

### Full PR or merge tier

- Electron E2E;
- visual/accessibility tests;
- full engine fixtures;
- migration/fault suites;
- package builds for all targets;
- install/launch smoke;
- sample/model manifest validation.

### Hardware/release tier

- signed/notarized artifacts;
- updater end-to-end through a test channel;
- DirectML/CUDA/CoreML real hardware;
- large-corpus benchmarks;
- cloud sync and scheduler platform tests;
- final SBOM/notices/checksums;
- clean-machine installation and uninstall/update tests.

## 11. Flaky-test policy

- Tests MUST NOT be blindly retried to create green status.
- A retry may collect diagnostics, but the original failure remains visible.
- Quarantine requires an issue, owner, expiry date and scope justification.
- Release-blocking security, migration, update, data-integrity and checkpoint tests cannot be quarantined.
- Time/network/provider tests use deterministic simulators plus separate real integration runs.

## 12. Definition of done

A v1 requirement is done only when:

- specification and decision records are current;
- tests were added at the correct layers;
- production implementation passes them;
- fault/recovery behavior is proven;
- migration and update implications are handled;
- docs/i18n/accessibility are complete;
- platform artifacts are installed and exercised;
- performance, security, licensing and SBOM gates pass;
- evidence is linked from the PR and Release manifest.

A feature with untested recovery, installer or migration behavior is incomplete even when its happy-path UI works.