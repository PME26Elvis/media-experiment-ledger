# Desktop Product Decision Register

Status: **no blocking product questions remain**  
Specification baseline: `2026-07-22.3`

This file preserves the history of questions that previously shaped the product. The controlling decision for round 3 is:

> Mature capabilities are completed in v1 when their main cost is engineering volume, cross-platform integration or testing effort. They are not deferred merely to create a smaller MVP.

The product specification is now `implementation_ready`. Implementation remains `not_started` until the user explicitly requests it.

## Resolved in specification round 2

### APP-Q-001 — Public identity

- Status: `resolved`
- Answer: **Media Experiment Ledger Studio**.
- Descriptor: **Atlas · Detection · Media Automation**.
- Slug: `media-experiment-ledger-studio`.
- Application ID: `io.github.pme26elvis.media-experiment-ledger-studio`.
- `MEL Studio` is not used as the sole public brand.

### APP-Q-002 — Mandatory packages

- Status: `resolved`
- Required:
  - Windows x64 NSIS installer;
  - Windows x64 portable;
  - macOS arm64 DMG/update ZIP;
  - macOS Intel x64 DMG/update ZIP;
  - Linux x64 AppImage;
  - Linux x64 `.deb`.

### APP-Q-004 — Sample corpus Release architecture

- Status: `resolved`
- Dedicated immutable corpus Releases are referenced by app Release manifests.
- Unchanged multi-gigabyte corpus data is not re-uploaded with every app release.

### APP-Q-005 and APP-Q-019 — Sample tiers

- Status: `resolved`
- Both Quick Start and sanitized Full Research corpora are mandatory.
- Publication remains blocked until privacy, provenance and rights manifests pass.

### APP-Q-006 — `.env` and encrypted credentials

- Status: `resolved`
- Encrypted profiles are default.
- `.env` import/export and explicit persistent expert mode are supported.
- Warnings and confirmations are mandatory.
- There is no silent plaintext fallback.

### APP-Q-009 — Tray/background execution

- Status: `resolved`
- Active jobs can remain in the system tray.
- Closing offers keep-running, pause-and-quit and cancel-and-quit.
- Launch at login is opt-in.

### APP-Q-010 — Atlas editor

- Status: `resolved`
- Hybrid structured/freeform editor is required.
- Structured pages remain the default foundation.

### APP-Q-011 — Templates

- Status: `resolved`
- Seven built-in templates are required:
  1. Research Light;
  2. Editorial Dark;
  3. Gallery Minimal;
  4. Technical Audit;
  5. Executive Review;
  6. Traditional Chinese Academic;
  7. 16:9 Presentation Report.

### APP-Q-012 — Model artifact distribution

- Status: `resolved`
- Hybrid by exact artifact rights.
- Weights are bundled only after artifact-level redistribution approval.
- Download-on-demand and user-supplied modes remain available.

### APP-Q-013 — Required detector variants

- Status: `resolved`
- YOLOX-Tiny/S/L.
- NanoDet-Plus-m-320/m-416/m-1.5x-416.

### APP-Q-020 — Licensing

- Status: `resolved`
- App-specific source is Apache-2.0.
- Accepted source and binaries are public.
- Notices, SBOM, license scans and separate rights manifests are mandatory.
- Unknown redistribution rights default to `do_not_distribute`.

## Resolved in specification round 3

### APP-Q-003 — Packaging/updater

- Status: `resolved`
- Use Vite + `electron-builder` + `electron-updater`.
- GitHub Releases is the initial public update/artifact source.
- Online and offline update workflows are both required.

### APP-Q-007 — Linux credential fallback

- Status: `resolved`
- Detect and reject insecure `basic_text` persistence.
- Support session-only entry and expert `.env` mode.
- v1 also includes a password-encrypted portable vault using Argon2id and XChaCha20-Poly1305 through a reviewed library.

### APP-Q-008 — Python engine

- Status: `resolved`
- Ship a self-contained version-pinned Python runtime for each supported platform.
- No user-installed Python requirement.
- Use a versioned pipe-based protocol and capability-scoped staging files.
- Reuse existing Atlas/YOLOX/NanoDet logic behind golden equivalence tests.

### APP-Q-029 — Signing and notarization

- Status: `resolved`
- Stable `1.0.0` requires Windows signing and Apple signing/notarization.
- Unsigned builds are prerelease-only and are excluded from the stable automatic-update channel.

### APP-Q-014 — GPU acceleration

- Status: `resolved`
- CPU is universal fallback.
- v1 includes DirectML on Windows, CUDA on Windows/Linux and CoreML on macOS.
- Real hardware tests and CPU golden tolerances are required.

### APP-Q-015 — PDF representation for video/GIF

- Status: `resolved`
- Default is a deterministic 10%/50%/90% three-frame strip.
- Poster, selected timestamp, configurable strip and full keyframe sheet are also required.

### APP-Q-016 — Imported media storage

- Status: `resolved`
- Use adaptive recommendations: managed copy for small/sample imports and external references for large existing folders.
- Users may override; portable export can materialize references.

### APP-Q-017 — Generated media enrollment

- Status: `resolved`
- Verified outputs first enter a dedicated Generated Media collection.
- Per-job rules may enroll successful outputs into named corpora.
- Silent merging into existing corpora is prohibited.

### APP-Q-018 — Renderer state/query tooling

- Status: `resolved`
- Pinia owns UI/session state.
- `@tanstack/vue-query` owns bounded asynchronous query state over typed IPC.
- SQLite remains source of truth.
- Whole-corpus reactive storage is prohibited.

### APP-Q-030 — Full Research prompts

- Status: `resolved`
- Publish sanitized complete prompt text when privacy/rights review passes.
- Include prompt IDs, categories, settings and normalized provenance.
- Exclude secrets, signed URLs, local paths, unnecessary raw payloads and sensitive prompts.

## Previously P2 items promoted to v1

### APP-Q-021 — Diagnostics and telemetry

- Status: `resolved`
- Comprehensive local support bundles are required.
- Remote telemetry capability is required but default-off, consent-based, previewable and endpoint-configurable.

### APP-Q-022 — Languages

- Status: `resolved`
- v1 requires complete `zh-TW`, `en`, `zh-CN`, `ja` and `ko` UI localization.

### APP-Q-023 — External custom templates

- Status: `resolved`
- Declarative custom Atlas template import/export is required in v1.
- Templates cannot execute code or load arbitrary remote resources.

### APP-Q-024 — User-supplied ONNX

- Status: `resolved`
- v1 supports known adapters, declarative custom detection adapter manifests and a capability-restricted sandboxed WASM postprocessor path.
- Arbitrary native/Python plugins remain prohibited.

### APP-Q-025 — GitHub Release publishing

- Status: `resolved`
- v1 includes an explicit draft-first GitHub Release publisher with immutable-history safeguards.

### APP-Q-026 — Background scheduler helper

- Status: `resolved`
- v1 includes Task Scheduler, LaunchAgent, `systemd --user` and tray fallback integration.

### APP-Q-027 — Cloud-folder sync

- Status: `resolved`
- v1 includes provider-agnostic cloud-folder project synchronization using content-addressed blobs, snapshots, journals and conflict resolution.
- A live writable SQLite database is never directly synchronized.

### APP-Q-028 — Reference hardware

- Status: `resolved`
- v1 acceptance uses low/mid/high tiers and both SSD/HDD scenarios.
- The user's i7-10700F/32 GB/RTX 2070 machine is a named practical mid-tier reference.

## Remaining questions

There are no unresolved P0/P1/P2 product decisions required before implementation.

During implementation, an engineer may discover a platform API limitation, dependency regression, artifact rights problem, security issue or measurable performance contradiction. Such discoveries MUST produce an ADR/spec correction with evidence. They MUST NOT silently remove or defer a required v1 capability.

## Next authorized action

Wait for the user to explicitly request implementation. At that point development follows:

- `SPECIFICATION_ROUND_03.md`;
- `V1_TDD_SDD_ENGINEERING_POLICY.md`;
- `V1_SCOPE_ACCEPTANCE_MATRIX.md`;
- `app-product-contract.json` version `2026-07-22.3`.