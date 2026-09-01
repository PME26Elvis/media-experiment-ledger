# 02 — Desktop Architecture and Security Specification

## 1. Architecture goals

The desktop architecture must support:

- a responsive Vue/Vuetify renderer;
- privileged filesystem and OS integration without exposing Node.js to UI code;
- long-running image/video/API/model jobs that survive UI navigation and recover after process restart;
- thousands of indexed assets and large result sets;
- deterministic project schemas and migrations;
- cross-platform packaging;
- signed updates and offline update import;
- reuse or porting of existing repository analysis logic without coupling the UI directly to scripts.

## 2. Provisional technology baseline

| Layer | Provisional choice | Decision state |
|---|---|---|
| Desktop shell | Electron, current stable at implementation start | Accepted concept, version unpinned |
| Build/scaffold | Electron Forge with Vite integration | Provisional |
| Renderer | Vue 3 + Vuetify 3 + TypeScript | Accepted |
| State | Pinia for renderer session/view state | Provisional |
| Routing | Vue Router | Accepted |
| Runtime validation | Zod or equivalent typed schema validation | Provisional |
| Project database | SQLite | Accepted |
| SQLite binding | `better-sqlite3` or maintained equivalent | Provisional |
| Image proxies | Sharp/libvips or engine-side equivalent | Provisional |
| Video inspection | Bundled FFmpeg/FFprobe sidecars | Accepted concept |
| Detection runtime | ONNX Runtime through a versioned engine adapter | Accepted concept |
| Engine implementation | Hybrid TypeScript/Node workers plus packaged Python sidecar where reuse is valuable | Provisional |
| Logging | Structured JSON logs with secret redaction | Accepted |
| Testing | Vitest, Vue Test Utils, Playwright Electron, engine unit/integration tests | Provisional tools |

Versions must be pinned only when implementation begins, using current stable versions and lockfiles. “Latest” must never mean unpinned floating dependencies in a released app.

## 3. Process model

### 3.1 Electron main process

Responsibilities:

- application lifecycle;
- window creation and restoration;
- native menu and dialog integration;
- filesystem permission boundary;
- project open/close lock management;
- update checks and installer handoff;
- secret encryption/decryption requests;
- engine process supervision;
- IPC request authorization and validation;
- protocol/deep-link handling if later enabled;
- crash and recovery bootstrap.

The main process MUST NOT perform CPU-heavy image processing, model inference, PDF rendering or large synchronous directory scans on its event loop.

### 3.2 Preload process

The preload layer exposes one narrow, versioned API through `contextBridge`.

Requirements:

- no generic `invoke(channel, ...args)` exposed to the renderer;
- no direct `fs`, `child_process`, `shell`, `process.env` or arbitrary Electron object exposure;
- every method has explicit input/output TypeScript types;
- runtime payload validation on both renderer boundary and main handler;
- event subscriptions return unsubscribe functions;
- renderer cannot choose arbitrary IPC channel names;
- API version is queryable for migration/compatibility diagnostics.

Illustrative shape:

```ts
interface DesktopBridgeV1 {
  projects: {
    chooseDirectory(): Promise<DirectorySelection | null>
    openProject(projectId: string): Promise<ProjectSummary>
    revealPath(pathToken: string): Promise<void>
  }
  jobs: {
    create(input: CreateJobInput): Promise<JobSnapshot>
    pause(jobId: string): Promise<JobSnapshot>
    resume(jobId: string): Promise<JobSnapshot>
    subscribe(listener: (event: JobEvent) => void): () => void
  }
  secrets: {
    listProfiles(providerId?: string): Promise<SecretProfileMetadata[]>
    saveProfile(input: SaveSecretProfileInput): Promise<SecretProfileMetadata>
    testProfile(profileId: string): Promise<CredentialTestResult>
  }
}
```

The renderer must never receive decrypted secret values from `listProfiles`.

### 3.3 Renderer process

Responsibilities:

- route rendering;
- user interaction;
- form state;
- display-level filtering and sorting;
- virtualized media views;
- document editing commands;
- subscribing to aggregated job snapshots;
- invoking typed bridge actions.

Prohibited:

- direct filesystem traversal;
- direct network calls that require secrets;
- arbitrary process spawn;
- loading `file://` paths supplied by project content without sanitization;
- trusting HTML from API responses or imported projects;
- retaining decrypted API keys in Pinia/localStorage.

### 3.4 Job supervisor

A main-process-owned supervisor manages durable jobs but delegates heavy work to workers/engines.

Responsibilities:

- state transitions;
- queue and priority;
- concurrency limits;
- cancellation tokens;
- pause checkpoints;
- lease/heartbeat tracking;
- restart recovery;
- progress aggregation;
- log routing;
- final verification;
- cleanup policy.

The job supervisor writes state transactionally before notifying the renderer.

### 3.5 Worker execution domains

At least three execution domains are required:

1. **I/O workers** — download, checksum, copy, archive and filesystem indexing.
2. **Media workers** — thumbnail/proxy generation, decode validation, Atlas rendering, PDF assets.
3. **Inference workers** — model loading and detector inference.

API automation may use a dedicated network worker or supervised main-side service, but secrets must never be passed to renderer workers.

Worker crashes must not crash the app shell. The supervisor records crash context, marks the active item recoverable/failed according to policy and may restart within bounded limits.

## 4. Local analysis engine boundary

### 4.1 Why an engine boundary exists

The existing repository contains Python analysis logic and real FFmpeg/ONNX workflows. Rewriting everything into renderer TypeScript would increase risk and UI coupling. Shipping an uncontrolled Python environment would harm installation reliability.

The app therefore defines a versioned local engine protocol independent of implementation language.

### 4.2 Engine protocol

Requirements:

- engine process launched only by trusted main-process code;
- executable path resolved from signed app resources or an explicitly trusted development path;
- no shell interpolation;
- arguments passed as arrays;
- per-job working directory;
- structured NDJSON over stdin/stdout or authenticated local IPC;
- stderr captured as diagnostics, never parsed as primary protocol;
- protocol messages include `protocol_version`, `job_id`, `request_id` and schema version;
- maximum message sizes enforced;
- binary media is exchanged by validated file paths/tokens, not embedded base64 messages;
- engine may access only project/job paths granted by the main process;
- heartbeat and graceful shutdown supported;
- cancellation is cooperative first, forced termination after timeout.

### 4.3 Engine implementation strategy

Provisional phased approach:

- Reuse verified Python Atlas/detector components behind the engine protocol for early correctness.
- Package a platform-specific self-contained engine; do not require users to install Python.
- Move suitable high-frequency operations to Node/native libraries only when benchmarks justify it.
- Keep result schemas identical across implementations.

A language rewrite must pass golden-corpus equivalence tests before replacing an established engine stage.

## 5. Filesystem security and path tokens

### 5.1 Renderer path handling

The renderer may display user paths but privileged actions should prefer opaque path tokens or project-relative identifiers.

A `PathGrant` record contains:

- grant ID;
- canonical path;
- grant type: file/directory/output;
- project scope;
- allowed operations;
- created time;
- last verified time;
- platform identity metadata where available.

IPC calls use the grant ID rather than accepting arbitrary path strings whenever practical.

### 5.2 Canonicalization

Before privileged use:

- normalize separators;
- resolve `.` and `..`;
- resolve symlinks/junctions according to policy;
- compare canonical path against allowed roots;
- reject NUL and invalid path sequences;
- reject archive traversal paths;
- apply Windows reserved-name and long-path handling;
- avoid case-sensitive assumptions on case-insensitive filesystems.

### 5.3 Open/reveal folder

“Open folder” actions invoke OS shell integration only after path validation. Imported configs cannot trigger automatic path opening.

### 5.4 Drag and drop

Dropped renderer objects are treated as untrusted references. The main process resolves and validates native paths, detects files versus directories and returns a sanitized preview before import.

## 6. Electron security baseline

Every production window MUST use:

- `nodeIntegration: false`;
- `contextIsolation: true`;
- renderer sandbox enabled where compatible;
- no `enableRemoteModule`;
- restrictive `webPreferences`;
- navigation and new-window deny-by-default handlers;
- explicit allowlist for external `https` URLs opened in the system browser;
- Content Security Policy without arbitrary inline script/eval;
- no remote web content in privileged windows;
- permission request handler that denies capabilities not required by the app;
- session partition review for any embedded help/web content.

Developer tools must be disabled or gated in production according to release channel.

## 7. Secrets and credential architecture

### 7.1 Storage model

A credential profile has:

- profile ID;
- provider ID;
- user-visible name;
- optional account label;
- encrypted payload reference;
- last test result/time;
- created/updated timestamps;
- non-secret capability metadata.

The secret value is encrypted in the main process using Electron `safeStorage` asynchronous APIs when available. OS-backed providers include Keychain on macOS, DPAPI on Windows and a Secret Service/keyring backend on compatible Linux desktops.

### 7.2 Linux fallback

Linux environments may lack a working secret service. The app must detect this and offer explicit choices:

1. configure a supported keyring;
2. use an environment-only session secret that is not persisted;
3. use a password-protected portable vault if that feature is approved;
4. decline provider setup.

The app must not silently fall back to plaintext.

### 7.3 `.env` support

`.env` is supported as an import/edit interoperability source, not as the preferred internal vault.

Rules:

- imported secret values are transferred into encrypted profiles by default;
- `.env` remains user-editable only when the user selects file-backed mode;
- file-backed mode displays a plaintext-at-rest warning;
- the app can reveal the containing folder;
- ordinary config export emits secret references, not values;
- exporting a secret-bearing `.env` requires explicit warning and destination selection;
- logs redact keys by known field names and detected value fingerprints.

### 7.4 Secret lifecycle

- secret reveal requires explicit user action and auto-hides;
- clipboard copy clears after a configurable timeout where platform APIs permit;
- renderer memory receives plaintext only for the shortest possible operation, preferably never;
- API worker receives the credential through a protected process channel or short-lived in-memory handoff;
- secrets are not passed as command-line arguments;
- credential deletion removes encrypted records and invalidates dependent automation configs until relinked.

## 8. Database architecture

### 8.1 Database separation

- Global app database: settings, known projects, update metadata, global model catalog, credential metadata.
- Per-project database: assets, imports, prompts, jobs, results, report drafts, path grants, migrations.

Large binary files must not be stored as SQLite blobs by default.

### 8.2 SQLite requirements

- WAL mode where safe for the filesystem;
- foreign keys enabled;
- transactional writes;
- schema version table;
- migration journal;
- integrity checks after unclean shutdown or failed migration;
- indexes for filter/sort fields;
- cursor/keyset pagination for large tables;
- busy timeout and serialized write policy;
- backup API or filesystem-consistent backup strategy.

Network shares and cloud-synced folders require explicit support status because locking semantics may differ.

## 9. Project locking and concurrent instances

- Opening a project acquires a project lock with process identity and heartbeat.
- A second app instance may open the project read-only or request takeover after verifying stale lock.
- Forced takeover records an audit event.
- Two writers must not operate on the same project database simultaneously.
- Background engine processes inherit the project lease and terminate when ownership is lost.

## 10. IPC error model

IPC responses use a stable envelope:

```ts
interface AppResult<T> {
  ok: boolean
  value?: T
  error?: {
    code: string
    message: string
    recoverable: boolean
    diagnosticId?: string
    details?: Record<string, unknown>
  }
}
```

Rules:

- internal stack traces remain in diagnostics;
- renderer receives safe, localized message keys plus structured context;
- errors are categorized for retry/UI behavior;
- cancellation is distinct from failure;
- validation errors identify fields;
- IPC timeouts do not imply job cancellation; durable job state remains queryable.

## 11. Logging and diagnostics

### 11.1 Log streams

- app lifecycle log;
- renderer diagnostic log;
- job event log;
- engine stdout protocol archive (sanitized);
- provider request summary log;
- update/migration log;
- crash reports stored locally.

### 11.2 Redaction

Redact:

- API keys/tokens;
- authorization headers;
- signed URLs where query parameters contain credentials;
- user-selected secret fields;
- environment values;
- optionally full local paths in exportable support bundles.

### 11.3 Support bundle

User-triggered support bundle may include:

- app/version/platform;
- dependency/engine versions;
- sanitized settings;
- recent logs;
- project schema version and counts;
- job diagnostics;
- migration state;
- update state.

It excludes media, prompts, raw provider responses and secrets by default.

## 12. Network boundary

- Provider requests originate from supervised backend code, not the renderer.
- TLS certificate validation remains enabled.
- Redirect count is bounded.
- Download size and content type are validated.
- Model/sample/update downloads are verified by signed metadata or pinned checksums.
- Proxy support is configurable but credentials are treated as secrets.
- Offline mode disables background network checks.
- No analytics/telemetry leaves the device unless explicitly approved in a future decision.

## 13. Dependency and supply-chain controls

- Lock all production dependencies.
- Generate SBOM for Release builds.
- Review Electron/Vue/Vuetify/ONNX/native dependency security advisories before Release.
- Verify downloaded model and sample artifacts with SHA-256 or stronger manifest checks.
- Sign platform packages where feasible/required.
- Do not download executable engine plugins from arbitrary project metadata.
- Native modules must be rebuilt for the target Electron ABI in CI.
- Licenses for app dependencies, bundled binaries, fonts, icons, FFmpeg and model artifacts must be included in a generated notices package.

## 14. Crash recovery

At startup after unclean shutdown:

1. detect stale app/project locks;
2. open databases and run integrity checks as needed;
3. identify jobs left in running/pausing/cancelling states;
4. inspect durable checkpoints and worker lease expiration;
5. mark jobs recoverable or failed with explanation;
6. clean incomplete temporary files only after manifest comparison;
7. present a Recovery Center summary;
8. never auto-delete partial user results before the retention policy is evaluated.

## 15. Architecture acceptance criteria

The architecture baseline is accepted only when tests demonstrate:

- renderer has no Node global access;
- arbitrary IPC channels cannot be invoked;
- invalid paths and archive traversal are rejected;
- secrets never appear in renderer stores or exported configs by default;
- main process stays responsive during large scans and inference;
- worker crash is isolated and produces recoverable job state;
- project lock prevents concurrent writers;
- database migration can fail without corrupting the pre-migration backup;
- external navigation is deny-by-default;
- CSP blocks unapproved script execution;
- support bundles pass automated secret-redaction fixtures;
- packaged builds can locate engine, FFmpeg and model resources on each supported platform.