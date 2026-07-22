# AGENTS.md — Media Experiment Ledger Studio

## Scope

This file applies to the `app/` desktop implementation subtree on `app-main`. It supplements the repository root `AGENTS.md`. More specific nested instructions may add constraints but MUST NOT weaken accepted v1 scope, security, data integrity, licensing, migration or test gates.

## Read order

Before changing app code, schemas, workflows or packages, read:

1. `/app-product-contract.json`;
2. `/docs/app/README.md`;
3. `/docs/app/SPECIFICATION_ROUND_03.md`;
4. `/docs/app/V1_SCOPE_ACCEPTANCE_MATRIX.md`;
5. `/docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md`;
6. the affected numbered module specification;
7. `/docs/app/LICENSING_AND_DISTRIBUTION_POLICY.md`;
8. `/docs/app/OPEN_QUESTIONS.md`;
9. the root `AGENTS.md` and `project-contract.json` when reusing existing algorithms/data.

The product is `implementation_ready` but `not_started` until the user explicitly authorizes implementation.

## Controlling v1 rule

A mature capability MUST NOT be moved out of v1 merely because it adds code, platform work, tests, CI time or integration complexity.

If a required item appears difficult:

1. decompose it;
2. specify interfaces/state/failure modes;
3. write executable tests;
4. implement it in stages behind stable contracts;
5. use optional signed packs or platform adapters where appropriate;
6. keep the v1 acceptance requirement intact.

Only evidence-backed legal, security or actual platform impossibility may change acquisition/implementation mode. Scope reduction requires an explicit user decision and synchronized contract update.

## Communication and Git workflow

- Default user-facing language is Traditional Chinese.
- Make mainstream implementation decisions directly under broad permission.
- Do not repeatedly ask minor questions already covered by the contract.
- Keep progress updates concise and factual.
- Never claim installer, update, GPU provider, Release, model, PDF, sync, migration or recovery success without testing the actual flow.
- Feature branches start from `app-main`.
- Use normal merge commits.
- Preserve branches unless asked to delete them.
- Keep implementation, tests, schemas, migrations, docs, localization, workflows and visible UI entries synchronized.

## SDD and TDD

Every feature uses this chain:

```text
Decision -> Requirement ID -> Failing test -> Implementation -> CI evidence -> Release manifest
```

Before implementation:

- identify requirement IDs from `V1_SCOPE_ACCEPTANCE_MATRIX.md`;
- define success/loading/empty/offline/error/interrupted/recovery states;
- define persistent schemas and migrations;
- define security/privacy boundaries;
- define performance budgets;
- define platform differences;
- define acceptance tests.

For deterministic domain and boundary behavior, use red/green/refactor. A feature PR must list decision IDs, requirement IDs, test IDs, schemas/migrations and platform artifacts affected.

Do not use test quantity as a substitute for risk coverage. Do not waive recovery, migration, updater, signing or real hardware tests merely because unit tests are green.

## Required stack

### Desktop and renderer

- Electron.
- Vite.
- Vue 3.
- Vuetify 3 current stable syntax at implementation time.
- TypeScript strict.
- Composition API and `<script setup lang="ts">` for ordinary components.
- Pinia for UI/session state.
- `@tanstack/vue-query` for bounded asynchronous query state.
- SQLite as authoritative project data.

### Packaging and updates

- `electron-builder`.
- `electron-updater`.
- Windows NSIS x64 and portable x64.
- macOS arm64/x64 DMG + update ZIP.
- Linux x64 AppImage + `.deb`.
- Stable release requires Windows signing and Apple signing/notarization.
- Unsigned builds are prerelease-only.

### Engine

- Self-contained version-pinned Python runtime for each platform/architecture.
- No user-installed Python.
- Versioned framed JSON-RPC-style protocol over child-process pipes.
- Large/binary data through capability-scoped staging files.
- No public listening port.
- Runtime/engine hashes and SBOM entries required.

## Frontend rules

- Primary layouts use `v-container`, `v-row` and `v-col`.
- Every primary page works in wide, narrow and minimum supported windows.
- Meaningful interactive surfaces use `v-hover`; hover is never the sole path.
- Use Vuetify/Vue transitions for route, panel, disclosure and state changes.
- Respect reduced motion.
- Use semantic `color`, `prepend-icon` and `append-icon` values.
- Required themes: light, dark and system.
- Required locales: `zh-TW`, `en`, `zh-CN`, `ja`, `ko`.
- Do not hard-code user-visible text.
- Every route implements relevant loading, empty, partial, offline, error, interrupted, recovery and complete states.
- Virtualized collections and query caches remain bounded.
- Never load an entire large corpus into Pinia or one reactive array.

## Renderer and IPC security

- `nodeIntegration` false.
- `contextIsolation` true.
- sandbox renderer where compatible.
- no renderer filesystem, `child_process`, shell, updater, secret or environment access.
- preload exposes only typed/versioned allowlisted methods.
- runtime validation on both sides of IPC.
- deny navigation, popup, permission and external URL behavior by default.
- imported/API HTML and Markdown are sanitized.
- decrypted secrets never enter Pinia, TanStack persisted cache, localStorage, logs, command-line arguments or project configs.
- custom model postprocessing may use capability-restricted, resource-limited WASM only; arbitrary native/Python plugins are prohibited.

## Credentials

- Prefer real OS secure storage through Electron `safeStorage`.
- Reject automatic persistent storage when Linux backend is `basic_text`.
- Support session-only secrets.
- Support explicit warned `.env` expert profiles.
- Support portable encrypted vault using a reviewed libsodium-compatible design: Argon2id + XChaCha20-Poly1305, versioned envelope, unique salt/nonce, authenticated metadata and atomic writes.
- Never invent cryptographic primitives.
- Logs/support bundles/telemetry pass automated secret redaction tests.

## Main process and engine supervision

- Main process owns windows, dialogs, path grants, project locks, secrets, tray, schedulers, updates and engine supervision.
- Main event loop does not perform scanning, media decode, inference or PDF rendering.
- Spawn processes without shell interpolation.
- Use trusted resolved executable paths and argument arrays.
- Engine heartbeat, cancellation, checkpoint, crash and incompatible-version states are durable.
- Engine result completion includes output verification, not only process exit code.

## Durable jobs

Nontrivial import, hashing, proxies, downloads, API automation, Atlas, detection, PDF, publishing, sync, update, migration and export/import work are durable jobs.

Every durable job has:

- stable ID;
- versioned input/config snapshot;
- queued/running/pausing/paused/cancelling/cancelled/failed/recoverable/completed states;
- stage/item progress;
- bounded logs;
- transactional checkpoints;
- pause/resume/cancel;
- restart recovery;
- final integrity verification.

## Data and performance

- Source media is immutable.
- Use atomic files and database transactions.
- Archives reject absolute paths, traversal, symlink escape, compression bombs and manifest mismatch.
- Hash/model/config/input identities govern checkpoint reuse.
- Import behavior is adaptive: managed copy for small/sample imports, external reference for large folders, with user override.
- Portable export can materialize references.
- Design for 10,000 images, 1,000 videos, hundreds of thousands of boxes and 500-page reports.
- Use display-pixel-aware proxy pyramids.
- Use indexed keyset pagination and virtualized UI.
- Bound RAM/disk caches, decoder sessions, provider sessions and queues.
- Apply worker backpressure and cancellation.
- Test SSD and HDD cases on low/mid/high reference tiers.

## Atlas rules

- Image and video cohorts remain separate.
- Analysis snapshots are immutable/fingerprinted.
- Document drafts reference snapshots and do not mutate evidence.
- Hybrid structured/freeform editor is required.
- Seven built-in templates are required.
- Declarative external template import/export is required; templates cannot execute code.
- PDF is static.
- Default video representation is 10%/50%/90% frames.
- Poster, selected timestamp, configurable strip and full keyframe sheet are also required.
- PDF export includes preflight and reproducibility manifest.

## Detection rules

Required models:

- YOLOX-Tiny/S/L;
- NanoDet-Plus-m-320/m-416/m-1.5x-416.

Required providers:

- CPU fallback;
- DirectML Windows;
- CUDA Windows/Linux;
- CoreML macOS.

Rules:

- A GPU is usable only after provider smoke succeeds.
- Compare provider outputs to CPU golden results within model-specific tolerances.
- Record provider/runtime identity in manifests.
- Persist item-level checkpoints.
- Model files are hash-verified data, not executable plugins.
- Weight redistribution requires exact artifact approval.
- Support known adapters, declarative custom adapters and sandboxed WASM postprocessors.
- Without labels, use agreement/disagreement language—not accuracy, precision, recall, false-positive rate or mAP.
- Detection never mutates Atlas jobs/results/history.

## v1 integrations

Implement and test:

- Agnes image/video automation;
- Generated Media collection with optional named-corpus enrollment;
- Windows Task Scheduler, macOS LaunchAgent, Linux `systemd --user` and tray fallback;
- draft-first GitHub Release publisher with immutable-history guards;
- cloud-folder sync through content-addressed blobs, snapshots, journals and conflict resolution;
- local support bundles;
- default-off consent-based remote telemetry transport;
- Quick Start and sanitized Full Research corpora.

Never synchronize a live writable SQLite database through a cloud folder.

## Update and migration

- User data remains outside replaceable binaries.
- Validate platform, architecture, version, signature and checksum.
- Pause jobs at safe checkpoints before update.
- Back up before migration.
- Migrations are versioned, transactional/idempotent and recoverable.
- Migrate settings, projects, credentials, reports, templates, model registries, provider packs, scheduler definitions and sync journals.
- Update success requires new-app launch, migration and workspace verification.
- Failure enters Recovery Center with restore evidence.
- Downgrade is never silent.

## Required tests

Follow `/docs/app/V1_TDD_SDD_ENGINEERING_POLICY.md`.

At minimum:

- Vitest domain/process tests;
- Vue Test Utils component tests;
- 100% public IPC contract representation;
- pytest/property-based engine tests;
- real image, FFmpeg and ONNX tests;
- Playwright Electron E2E;
- visual/accessibility/all-locale matrix;
- migration and deliberate fault injection;
- real DirectML/CUDA/CoreML hardware runs;
- clean-machine install/update tests for all six packages;
- large-corpus benchmarks;
- security, license, SBOM, notices, signature and secret gates.

Coverage gates are defined in the contract and TDD/SDD policy. Release-blocking security/migration/update/checkpoint tests cannot be quarantined.

## Definition of done

A feature is done only when:

- contract/spec/decision state agree;
- requirement and test IDs are traceable;
- implementation and typed schemas exist;
- migration/update/recovery implications are handled;
- relevant fault paths are executed;
- UI/RWD/i18n/accessibility/polish are complete;
- performance is measured;
- security/privacy/rights review passes;
- actual packages/providers/artifacts are verified where relevant;
- documentation and release evidence are synchronized.

A happy-path-only feature is incomplete.