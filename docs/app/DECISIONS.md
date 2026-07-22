# Desktop Product Decision Log

This log records durable desktop-product decisions. The machine-readable source of stable invariants is `app-product-contract.json`; detailed accepted amendments live in the specification-round documents.

## Decision state

- `accepted` — implementation may rely on it;
- `provisional` — coherent default, still replaceable;
- `rejected` — intentionally excluded;
- `superseded` — replaced by a newer accepted decision.

## Governing decisions

### APP-D-001 — Separate desktop product line

- State: `accepted`
- `main` remains the web/analysis/Release product line.
- `app-main` is the long-lived desktop integration branch.
- The desktop app is not a browser wrapper and does not silently inherit Web-specific assumptions.

### APP-D-002 — Local-first workspace

- State: `accepted`
- Projects, corpora, jobs, reports and analysis work locally without mandatory accounts or API credentials.
- Optional network capabilities remain explicit and observable.

### APP-D-003 — Electron/Vue/Vuetify baseline

- State: `accepted`
- Electron, Vue 3, Vuetify 3, TypeScript strict, Composition API and `<script setup lang="ts">`.
- Primary layout uses `v-container`, `v-row` and `v-col`.
- Meaningful interaction uses semantic color/icons, `v-hover`, transitions and reduced-motion support.

### APP-D-004 — Renderer privilege boundary

- State: `accepted`
- `nodeIntegration` false, `contextIsolation` true, renderer sandbox where compatible.
- Typed/versioned allowlisted preload IPC only.
- Renderer has no direct filesystem, process, environment, secret or updater access.

### APP-D-005 — Durable job architecture

- State: `accepted`
- Long-running import, download, automation, Atlas, detection, PDF, sync, publishing, update and migration operations use durable jobs with state machines, progress, checkpoints, cancellation and restart recovery.

### APP-D-006 — Immutable source media

- State: `accepted`
- Source media and immutable analysis snapshots are never rewritten by editing or derived processing.

### APP-D-007 — SQLite project authority

- State: `accepted`
- SQLite is authoritative project state; versioned JSON manifests support portability and inspection.
- Large collections use indexed/keyset pagination rather than complete renderer arrays.

### APP-D-008 — Independent Atlas and Detection domains

- State: `accepted`
- Atlas and Detection use independent job/config/output histories and cannot mutate each other.

### APP-D-009 — Static PDF contract

- State: `accepted`
- PDF export is a deterministic static document workflow.
- GIF/video animation inside PDF is not promised.

### APP-D-010 — Artifact-level rights

- State: `accepted`
- Source-code licenses do not automatically license model weights, data, fonts, themes or provider assets.
- Unknown redistribution rights default to `do_not_distribute`.

## Specification round 2 decisions

Round 2 is fully recorded in `SPECIFICATION_ROUND_02.md` and includes:

- **APP-D-021** — public name Media Experiment Ledger Studio;
- **APP-D-022** — six mandatory package types;
- **APP-D-023** — Quick Start and Full Research corpora;
- **APP-D-024** — dedicated immutable corpus Releases;
- **APP-D-025** — encrypted credentials plus expert `.env` mode;
- **APP-D-026** — system-tray background execution;
- **APP-D-027** — hybrid Atlas editor and seven templates;
- **APP-D-028** — representative detector model tiers;
- **APP-D-029** — Apache-2.0 app-specific source and public accepted binaries;
- **APP-D-030** — conservative model/data/font/template rights manifests.

All are `accepted`.

## Specification round 3 decisions

Detailed normative behavior is in `SPECIFICATION_ROUND_03.md`.

### APP-D-031 — Complete Mature v1

- State: `accepted`
- Mature capabilities are not deferred merely because they add engineering volume, cross-platform work, CI cost or testing complexity.
- Complete error, interruption, migration, accessibility, localization and recovery behavior is part of each v1 feature.
- Scope reduction requires explicit user approval.

### APP-D-032 — electron-builder/electron-updater

- State: `accepted`
- Vite + electron-builder + electron-updater.
- GitHub Releases is the initial public artifact/update source.

### APP-D-033 — Stable signing and notarization

- State: `accepted`
- Windows signing and Apple signing/notarization are required for stable `1.0.0`.
- Unsigned artifacts are prerelease-only.

### APP-D-034 — Self-contained Python engine

- State: `accepted`
- Version-pinned redistributable Python runtime is packaged per platform.
- No user Python installation.
- Versioned pipe protocol; no public listening port.

### APP-D-035 — Portable encrypted vault

- State: `accepted`
- OS secure storage where available, session and expert `.env` modes, and a v1 portable encrypted vault.
- Argon2id + XChaCha20-Poly1305 through a reviewed libsodium-compatible implementation.
- Linux `basic_text` persistence is rejected.

### APP-D-036 — Full v1 acceleration

- State: `accepted`
- CPU fallback, DirectML Windows, CUDA Windows/Linux and CoreML macOS.
- Real hardware smoke and CPU golden-tolerance evidence required.

### APP-D-037 — Video/GIF PDF representations

- State: `accepted`
- Default 10%/50%/90% frame strip.
- Poster, selected timestamp, configurable strip and full keyframe sheet are also v1.

### APP-D-038 — Adaptive media import

- State: `accepted`
- Managed copy recommendation for small/sample imports; external reference recommendation for large folders; user override and portable materialization.

### APP-D-039 — Generated Media collection

- State: `accepted`
- Verified API outputs enter a dedicated collection before optional named-corpus enrollment.

### APP-D-040 — Pinia + TanStack Vue Query

- State: `accepted`
- Pinia owns UI/session state.
- TanStack Vue Query owns bounded asynchronous query state over typed IPC.
- SQLite remains authoritative.

### APP-D-041 — Sanitized complete Full Research prompts

- State: `accepted`
- Complete prompt text and normalized provenance are public when rights/privacy review passes; sensitive/secret fields are excluded with redaction reasons.

### APP-D-042 — Diagnostics and optional telemetry

- State: `accepted`
- Local support bundles and a default-off consent-based remote telemetry transport are v1.

### APP-D-043 — Five complete locales

- State: `accepted`
- `zh-TW`, `en`, `zh-CN`, `ja` and `ko` are required for stable v1.

### APP-D-044 — Declarative template import/export

- State: `accepted`
- Versioned, non-executable, validated Atlas template packages are v1.

### APP-D-045 — User-supplied ONNX

- State: `accepted`
- Known adapters, declarative detection manifests and capability-restricted WASM postprocessors are v1.
- Arbitrary native/Python plugins remain rejected.

### APP-D-046 — GitHub Release publisher

- State: `accepted`
- Draft-first explicit publication with manifest/checksum and immutable-history guards is v1.

### APP-D-047 — OS scheduler helper

- State: `accepted`
- Windows Task Scheduler, macOS LaunchAgent, Linux `systemd --user` and tray fallback are v1.

### APP-D-048 — Cloud-folder synchronization

- State: `accepted`
- Content-addressed blobs, snapshots, journals and conflict resolution are v1.
- Live writable SQLite synchronization is rejected.

### APP-D-049 — Reference hardware matrix

- State: `accepted`
- Low/mid/high and SSD/HDD test tiers are required; the user's i7-10700F/32 GB/RTX 2070 system is a named mid-tier reference.

### APP-D-050 — SDD/TDD release discipline

- State: `accepted`
- Decision → requirement → failing test → implementation → CI evidence → Release manifest traceability is mandatory.
- Unit, component, IPC, engine, E2E, migration, fault-injection, visual, accessibility, localization, hardware, package, performance and rights tests apply according to risk.
- Release-blocking security/migration/update/checkpoint tests cannot be quarantined.

## Rejected or constrained decisions

### APP-D-R01 — Mandatory API usage

- State: `rejected`
- Local/sample analysis works without API credentials.

### APP-D-R02 — Live cloud-synced SQLite

- State: `rejected`
- Use snapshots/journals/content-addressed blobs instead.

### APP-D-R03 — Arbitrary native/Python plugins

- State: `rejected`
- Custom detection extension is declarative or sandboxed WASM only.

### APP-D-R04 — Unsigned stable automatic updates

- State: `rejected`
- Stable automatic updates require the accepted signing/notarization contract.

### APP-D-R05 — Unverified third-party redistribution

- State: `rejected`
- Change acquisition mode or withhold the artifact.

## Current gate

- Product status: `implementation_ready`.
- Implementation status: `not_started`.
- Blocking product questions: `0`.
- Implementation begins only after explicit user instruction.