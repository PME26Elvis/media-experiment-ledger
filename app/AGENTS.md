# AGENTS.md — Desktop Application Product Line

## Scope

This file applies to the future `app/` desktop implementation subtree on the `app-main` product-line branch. It supplements the repository root `AGENTS.md`. A more specific nested `AGENTS.md` may add constraints but must not weaken security, data-integrity or user-approved product contracts.

## Read order

Before changing desktop code or schemas, read:

1. `/app-product-contract.json`;
2. `/docs/app/README.md`;
3. the affected module specification under `/docs/app/`;
4. `/docs/app/DECISIONS.md`;
5. `/docs/app/OPEN_QUESTIONS.md`;
6. the repository root `AGENTS.md` and `project-contract.json` when reusing main-product algorithms/data.

Do not implement an unresolved product-shaping choice as if it were accepted. Use the documented provisional default only when the relevant milestone allows it, and preserve replaceability.

## Communication and Git workflow

- Default user-facing language is Traditional Chinese.
- When broad permission has been granted, make mainstream, reasonable implementation decisions directly instead of repeatedly asking minor questions.
- Keep progress updates concise and honest.
- Never claim an installer, update, Release, model, PDF or migration succeeded until the actual artifact/flow has been verified.
- Work on feature branches from `app-main`.
- Open pull requests and use normal merge commits unless the user requests otherwise.
- Do not delete branches unless asked.
- Keep implementation, tests, schemas, migrations, help/docs, workflow changes and visible UI entry points synchronized.

## Product-line boundaries

- `main` remains the existing web/analysis/Release product line.
- The app is not a browser wrapper and must not silently inherit Web-specific assumptions.
- App Releases use distinct desktop tags/assets.
- Existing immutable experiment/analysis/detector Releases remain immutable.
- Reuse algorithms through explicit modules, fixtures and versioned engine/data contracts.
- API generation is optional; local/sample analysis must work without credentials.
- Atlas Studio and Detection Studio are independent job/output domains.

## Frontend requirements

- Vue 3 and Vuetify 3 current stable syntax at implementation time.
- TypeScript strict mode.
- Ordinary Vue components use Composition API and `<script setup lang="ts">`.
- Do not introduce Options API for convenience.
- Primary responsive layouts use `v-container`, `v-row` and `v-col`.
- Every primary page must work in wide and narrow windows.
- Meaningful interactive surfaces use `v-hover`; hover is never the only interaction path.
- Use Vuetify/approved Vue transitions for route, panel, disclosure and state changes.
- Respect reduced-motion preferences.
- Controls use semantic colors and icons (`color`, `prepend-icon`, `append-icon`) rather than random decoration.
- Every route requires loading, empty, partial, error, recoverable and completed states as applicable.
- Traditional Chinese and English strings use i18n; do not hard-code user-visible strings.

## Renderer security

- `nodeIntegration` remains false.
- `contextIsolation` remains true.
- Use renderer sandbox where compatible.
- Renderer must not import/use filesystem, `child_process`, shell, environment variables, updater or secret APIs directly.
- Preload exposes explicit typed/versioned methods only; never expose generic arbitrary IPC invocation.
- Validate IPC payloads at runtime on both sides of the trust boundary.
- Deny navigation, popup, permission and external URL behavior by default; allowlist deliberate actions.
- Do not render unsanitized imported/API HTML or Markdown.
- Do not put decrypted secrets into Pinia, localStorage, logs, command-line arguments or project configs.

## Main process and engine

- Main process owns windows, dialogs, path grants, project locks, secrets, OS integration, update handoff and engine supervision.
- Main event loop must not perform CPU-heavy scans, media decode, inference or PDF rendering.
- Long work runs in bounded worker/engine domains behind the versioned protocol.
- Spawn processes without shell interpolation; arguments are arrays and executable paths are trusted/resolved.
- Binary media travels by validated path token/file, not huge IPC/base64 payload.
- Engine crashes must be isolated and produce durable recoverable/failed job state.

## Durable jobs

The following are always durable jobs when nontrivial:

- import/index/hash;
- thumbnail/video proxy generation;
- sample/model/update downloads;
- API automation;
- Atlas analysis/rendering;
- detector inference/comparison;
- project export/import;
- PDF export;
- migration/backup/restore.

Requirements:

- stable job ID;
- versioned config/input snapshot;
- queued/running/pausing/paused/cancelling/cancelled/failed/recoverable/completed states;
- stage/item progress;
- transactional checkpoints;
- bounded logs;
- pause/resume/cancel;
- crash recovery;
- final verification after apparent 100% progress.

## Data integrity

- Source media is immutable and must never be rewritten in place.
- Derived thumbnails, annotations, analysis and documents live in managed output/cache paths.
- Use atomic writes for manifests/configs/sidecars.
- Use transactions for database state.
- Hash/model/config/input identities determine checkpoint reuse.
- Imported archives reject absolute paths, traversal, compression bombs and manifest mismatches.
- Project/config schema changes require migrations, fixtures, backup/recovery and documentation.
- A newer unknown schema must not be guessed-written by an older implementation.

## Paths and secrets

- All privileged paths pass canonicalization and project-scoped authorization/path grants.
- Drag-and-drop paths are untrusted until main-process resolution.
- Every configurable path has browse, reveal, validation and reasonable default behavior.
- Credential values use OS-backed encrypted storage when available.
- `.env` is an explicit interoperability/file-backed option, not a silent plaintext default.
- Ordinary config/project exports exclude secrets.
- Support bundles and logs pass automated redaction tests.

## Performance

- Design and benchmark for at least 10,000 images and 1,000 videos.
- Do not hold entire corpora/detection tables in renderer state.
- Use indexed/keyset-paginated database queries and virtualized lists/grids.
- Generate a proxy/thumbnail pyramid and request the smallest representation that satisfies actual display pixels/DPR/zoom.
- Cancel offscreen/stale media requests.
- Originals load only for explicit detail/high zoom/export.
- Bound memory/disk caches, decoder/model sessions and worker queues.
- Use backpressure and separate worker pools for I/O, image, video, API, inference and PDF work.
- Measure renderer long tasks, memory, DB latency and throughput; do not assume optimization without benchmark evidence.

## Atlas rules

- Follow `/docs/app/05_ATLAS_STUDIO_SPEC.md`; do not assume the current web implementation is a complete app specification.
- Image and video cohorts remain separate.
- Preserve exact source aliases while removing byte duplicates from unique sample counts.
- Analysis snapshots are immutable and fingerprinted.
- Document drafts are editable structured data that reference snapshots.
- Document editing must not alter source media or analysis evidence.
- PDF v1 uses explicit static representations for GIF/video; never claim animation.
- PDF export includes preflight and reproducibility manifest.

## Detection rules

- Follow `/docs/app/06_DETECTION_STUDIO_SPEC.md`.
- Baseline models are YOLOX-Tiny and NanoDet-Plus-m-320 with real ONNX Runtime smoke/golden tests.
- Candidate larger variants remain gated until artifact, adapter, license, runtime and resource review passes.
- Never infer that a source-code license alone settles every pretrained-weight redistribution question.
- Model files are hash-verified and are data, not executable plugins.
- Persist item-level checkpoints.
- Normalize boxes to original image coordinates and validate finite/bounded values.
- Without human ground truth, use agreement/disagreement language only—not accuracy, precision, recall, false-positive rate or mAP.
- Detection must not mutate Atlas jobs/results/history.

## Update and migration rules

- User data remains outside replaceable app binaries.
- Online/offline packages are platform/architecture/version/signature/checksum validated.
- Do not manually overwrite a running executable when platform installer/updater handoff is required.
- Linux update behavior is package-specific; never promise unsupported built-in auto-update.
- Running jobs pause at safe checkpoints before update.
- Migrations are versioned, backed up and transactional/resumable.
- Update success is declared only after new app launch, migration and workspace verification.
- Migration failure enters Recovery Center and preserves restore evidence.
- Downgrade is not silently supported.

## Tests required by change type

### Renderer/UI

- type/lint/component;
- wide/narrow RWD;
- light/dark;
- hover/focus/touch;
- reduced motion;
- Traditional Chinese/English;
- accessibility and visual regression.

### IPC/security

- allowlist/schema;
- invalid/oversized payload;
- path traversal/grants;
- renderer privilege assertions;
- secret redaction.

### Media/engine

- real lightweight image decode;
- real FFmpeg/FFprobe generated-video tests;
- pause/resume/crash recovery;
- output hash/integrity.

### Detection

- exact model size/SHA/labels;
- real ONNX session/output shape;
- preprocessing/postprocessing/golden outputs;
- checkpoint and comparison guardrails.

### Packaging/update

- actual packaged launch;
- resources/engine/native dependency discovery;
- install/update/offline package;
- migration/backup/recovery;
- signing/notarization evidence where required;
- GitHub-side Release asset verification.

## Definition of done

A desktop feature is not done until:

- specification and decision state agree;
- implementation and typed schemas exist;
- migration impact is handled;
- tests appropriate to risk pass;
- UI states/RWD/accessibility/polish are complete;
- large-corpus impact is measured;
- security/privacy review is complete;
- actual package/artifact behavior is verified when relevant;
- documentation and machine contract are synchronized.