# Desktop Product Open Questions

This register is the primary interface for future specification rounds. Resolved questions remain recorded so later work does not reopen accepted decisions without an explicit change request.

Priorities:

- **P0** — blocks secure architecture, package identity or the first implementation milestone.
- **P1** — materially changes v1 product scope or user workflow.
- **P2** — can be deferred without expensive architectural rework.

When an answer is accepted, update the machine contract, normative specification round, affected baseline documents before implementation, roadmap and acceptance tests.

---

## Resolved in specification round 2

### APP-Q-001 — Final public app name

- Status: `resolved`
- Answer: **Media Experiment Ledger Studio**.
- Descriptor: **Atlas · Detection · Media Automation**.
- Slug: `media-experiment-ledger-studio`.
- Application ID: `io.github.pme26elvis.media-experiment-ledger-studio`.
- Note: do not use `MEL Studio` as the sole public brand.

### APP-Q-002 — Mandatory v1 platforms/packages

- Status: `resolved`
- Required:
  - Windows x64 NSIS installer;
  - Windows x64 portable;
  - macOS arm64 DMG/update ZIP;
  - macOS x64 DMG/update ZIP;
  - Linux x64 AppImage;
  - Linux x64 `.deb`.
- A universal macOS artifact is optional, but Intel support is mandatory.

### APP-Q-004 — Sample corpus Release architecture

- Status: `resolved`
- Answer: dedicated immutable corpus Releases referenced by app Release manifests.
- Unchanged multi-gigabyte data is not re-uploaded with every app release.

### APP-Q-005 and APP-Q-019 — Sample corpus content/tiering

- Status: `resolved`
- Answer: provide both:
  - a small curated **Quick Start** corpus;
  - a sanitized **Full Research** corpus.
- Publication remains blocked until privacy, provenance and rights manifests pass review.

### APP-Q-006 — `.env` and encrypted credentials

- Status: `resolved`
- Answer:
  - encrypted credential profiles are default;
  - `.env` import/export is supported;
  - persistent external `.env` file-backed profiles are an explicit expert option;
  - plaintext warnings and confirmation are mandatory;
  - no silent plaintext fallback.

### APP-Q-009 — Tray/background jobs

- Status: `resolved`
- Answer: support tray/background execution.
- Closing with active jobs offers keep-running, pause-and-quit, and cancel-and-quit.
- Launch at login is opt-in; native notifications are supported.

### APP-Q-010 — Atlas editor freedom

- Status: `resolved`
- Answer: hybrid editor.
- Structured blocks/pages remain the default foundation; controlled freeform page mode is included without arbitrary executable HTML/CSS/plugins.

### APP-Q-011 — Atlas templates

- Status: `resolved`
- Required templates:
  1. Research Light;
  2. Editorial Dark;
  3. Gallery Minimal;
  4. Technical Audit;
  5. Executive Review;
  6. Traditional Chinese Academic;
  7. 16:9 Presentation Report.

### APP-Q-012 — Model artifact distribution

- Status: `resolved`
- Answer: hybrid by exact artifact rights.
- App may ship adapters, labels and manifests, but weights are bundled only after artifact-level redistribution review.
- Download-on-demand and user-supplied modes remain available.

### APP-Q-013 — Larger detector variants

- Status: `resolved`
- Representative v1 set:
  - YOLOX-Tiny, YOLOX-S, YOLOX-L;
  - NanoDet-Plus-m-320, NanoDet-Plus-m-416, NanoDet-Plus-m-1.5x-416.
- Other variants are deferred until the registry/adapter system is stable.

### APP-Q-020 — License and distribution posture

- Status: `resolved`
- Answer:
  - app source is fully open source under Apache-2.0;
  - source and accepted binaries are public;
  - notices, SBOM and license scans are mandatory;
  - model weights, data, fonts and third-party assets keep separate manifests/licenses;
  - unknown redistribution rights default to do not distribute.

---

## P0 — Third specification round

These P0 questions must be resolved before implementation is declared ready. Answering them is the recommended next action rather than beginning production code immediately.

### APP-Q-003 — Packaging and updater stack

- Priority: P0 before implementation scaffold.
- Status: `open`
- Why it matters: all six required artifact types, signing, update metadata and portable behavior should use one coherent toolchain.
- Current recommendation: **electron-builder + electron-updater** with Vite as the renderer build system.
- Rationale:
  - NSIS and Windows portable targets;
  - macOS DMG/update ZIP;
  - Linux AppImage and `.deb`;
  - update metadata/progress/signature support across installed targets;
  - fewer custom makers and less fragmented update behavior than the provisional Forge plan for this exact matrix.
- Proposed targets:
  - Windows: `nsis`, `portable`;
  - macOS: `dmg`, `zip` for x64 and arm64;
  - Linux: `AppImage`, `deb`.
- Portable Windows remains guided replace-and-relaunch rather than pretending to be an installed auto-update target.
- Decision requested: accept electron-builder/electron-updater, or require Electron Forge despite additional package/update integration work?

### APP-Q-007 — Linux credential fallback without Secret Service

- Priority: P0.
- Status: `open`
- Recommendation for v1:
  - detect whether Electron safeStorage is backed by a secure Linux provider;
  - when unavailable, allow session-only secret entry and external `.env` expert mode;
  - do not persist plaintext automatically;
  - show keyring setup guidance;
  - defer a portable password-encrypted vault until a dedicated cryptographic design/review.
- Decision requested: accept session-only/external-file fallback, or require a password-protected portable vault in v1?

### APP-Q-008 — Packaged Python engine boundary

- Priority: P0.
- Status: `open`
- Why it matters: existing Atlas/detection Python is production-proven, while a complete rewrite raises correctness risk. Packaging Python increases app size and platform/SBOM work.
- Recommendation:
  - ship a self-contained, version-pinned Python engine with no user-installed Python requirement;
  - communicate over a language-neutral local protocol;
  - reuse current Atlas/detector code behind adapters;
  - migrate selected hot paths to Node/native only after profiling and golden equivalence tests;
  - keep renderer/main process independent from Python implementation details.
- Decision requested: accept packaged Python-first hybrid, or require a rewrite before the first usable app?

### APP-Q-029 — Signing/notarization expectation for pre-1.0 public builds

- Priority: P0 for automatic updates.
- Status: `open`
- Why it matters: macOS online updates require signed/notarized packages; Windows reputation and signature verification benefit from code signing, but certificates/accounts cost money and require secret management.
- Recommendation:
  - CI architecture supports signing from the first scaffold;
  - unsigned development artifacts are allowed only as clearly labeled prereleases;
  - stable auto-update channel is enabled only after real signing/notarization credentials exist;
  - Linux artifacts use checksums/signatures even without platform code signing.
- Decision requested: should stable `1.0.0` be blocked until Windows signing and Apple notarization are both operational?

---

## P1 — Primary workflow choices

### APP-Q-014 — GPU acceleration scope

- Priority: P1.
- Status: `open`
- Universal baseline: CPU ONNX Runtime is mandatory.
- Recommendation:
  - first usable release: CPU only;
  - next acceleration milestone: DirectML on Windows because it supports a broader GPU range;
  - later: CUDA Windows/Linux and CoreML macOS after packaged runtime validation;
  - CPU fallback must always remain available.
- Decision requested: CPU-only first stable, or require one acceleration provider in v1?

### APP-Q-015 — Default PDF representation for video/GIF cohorts

- Priority: P1.
- Status: `open`
- Recommendation: 10%/50%/90% three-frame contact strip by default, with poster-frame, selected timestamp and fuller keyframe sheet overrides.
- Decision requested: accept three-frame default?

### APP-Q-016 — Imported-media copy/reference default

- Priority: P1.
- Status: `open`
- Recommendation: adaptive wizard:
  - sample/small imports default to managed copy;
  - large existing folders default to external reference;
  - user confirms the choice;
  - preference may be remembered per project type;
  - project export can materialize referenced files into a portable package.
- Decision requested: accept adaptive behavior, or force one global default?

### APP-Q-017 — Generated-media enrollment

- Priority: P1.
- Status: `open`
- Recommendation:
  - verified API outputs enter a dedicated generated-media collection;
  - they are not silently merged into existing analysis inputs;
  - user may enable automatic enrollment into a named corpus only after successful run completion.
- Decision requested: accept explicit collection/link behavior?

### APP-Q-018 — Renderer state/query tooling

- Priority: P1 implementation detail.
- Status: `open`
- Recommendation:
  - Pinia for UI/session state;
  - typed repository/query composables over IPC for database pages;
  - SQLite remains source of truth;
  - bounded page caches and cancellation are mandatory;
  - evaluate a Vue query library only if it does not duplicate corpus state in memory.
- Decision requested: allow the implementation team to select the query library under these constraints?

### APP-Q-030 — Full Research corpus prompt/metadata detail

- Priority: P1 before publishing data.
- Status: `open`
- Recommendation:
  - include canonical prompt IDs, categories and sanitized prompt text where rights/privacy review passes;
  - include generation settings needed for Atlas identity;
  - exclude API keys, signed URLs, local paths and unnecessary raw provider payloads;
  - include normalized provenance rather than every raw response field.
- Decision requested: should sanitized full prompt text be public, or should the Full Research corpus publish only IDs/categories/settings?

---

## P2 — Deferrable enhancements

### APP-Q-021 — Remote telemetry

- Status: `open`
- Default: no remote telemetry; local diagnostics/support bundle only.

### APP-Q-022 — Languages

- Status: `open`
- Default: complete Traditional Chinese and English at first stable release; other languages deferred.

### APP-Q-023 — External custom template import

- Status: `open`
- Default: built-in templates plus in-project duplication/customization; external import deferred while the declarative schema is designed.

### APP-Q-024 — User-supplied ONNX models

- Status: `open`
- Default: allow user-supplied files only for known/allowlisted adapters and output schemas, not arbitrary model families.

### APP-Q-025 — Publish app results to GitHub Releases

- Status: `open`
- Default: local export only in v1; future explicit opt-in publisher.

### APP-Q-026 — OS service/helper for schedules

- Status: `open`
- Default: schedules run while app/tray process is active; no privileged service in v1.

### APP-Q-027 — Cloud-folder project sync

- Status: `open`
- Default: no live SQLite sync promise; support export packages and warn about network/cloud-folder locking.

### APP-Q-028 — Reference hardware

- Status: `open`
- Default: low/mid/high tiers, SSD and HDD scenarios, including the user's i7-10700F/32 GB/RTX 2070 system as a practical mid-tier reference.

---

## Recommended response format for round 3

```text
APP-Q-003: accept electron-builder/electron-updater / require Forge
APP-Q-007: accept session-only fallback / require encrypted portable vault
APP-Q-008: accept packaged Python hybrid / require rewrite
APP-Q-029: stable release requires signing+notarization / allow unsigned stable
APP-Q-014: CPU-first / require DirectML or another provider
APP-Q-015: accept three-frame PDF default / choose another
APP-Q-016: accept adaptive import / choose copy or reference
APP-Q-017: accept explicit generated collection / auto-enroll
APP-Q-018: allow implementation team to select query layer / specify one
APP-Q-030: publish sanitized full prompts / IDs and settings only
```
