# v1 Scope and Acceptance Matrix

Status: **accepted and release-blocking**  
Purpose: map every v1 product area to implementation and evidence requirements.

## 1. Release rule

Media Experiment Ledger Studio v1 is not a reduced MVP. Stable `1.0.0` MUST satisfy every row marked `required`. A capability may be optional for the end user while still being required to exist, be documented and pass tests.

Legal inability to redistribute a third-party artifact changes its acquisition mode to download-on-demand or user-supplied; it does not remove the surrounding workflow.

## 2. Platform and packaging

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-PKG-001 | Windows x64 NSIS installer | required | clean install, launch, update, uninstall, data preservation |
| V1-PKG-002 | Windows x64 portable package | required | extract/run, guided verified replacement, data preservation |
| V1-PKG-003 | macOS arm64 DMG + update ZIP | required | signed/notarized install, launch, update |
| V1-PKG-004 | macOS Intel x64 DMG + update ZIP | required | signed/notarized install, launch, update |
| V1-PKG-005 | Linux x64 AppImage | required | clean launch, permissions, signed update manifest, updater |
| V1-PKG-006 | Linux x64 `.deb` | required | install/upgrade/remove on supported Debian/Ubuntu matrix |
| V1-PKG-007 | electron-builder/electron-updater | required | generated target/update metadata validation |
| V1-PKG-008 | online and offline updates | required | signed test-channel update and offline import |
| V1-PKG-009 | Windows signing + Apple signing/notarization | required for stable | signature verification in CI and clean machines |
| V1-PKG-010 | SBOM, notices, checksums, manifest | required | Release asset set verifier |

## 3. Application shell and UX

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-UX-001 | Vue 3 + Vuetify 3 + `<script setup lang="ts">` | required | lint/static rule and component tests |
| V1-UX-002 | `v-row`/`v-col` responsive layouts | required | visual tests at required widths/locales |
| V1-UX-003 | semantic color/icons | required | component/visual review gates |
| V1-UX-004 | `v-hover` and meaningful transitions | required | pointer and reduced-motion tests |
| V1-UX-005 | light/dark/system themes | required | visual/accessibility matrix |
| V1-UX-006 | keyboard and screen-reader support | required | automated + manual accessibility evidence |
| V1-UX-007 | five complete locales | required | missing-key/overflow/E2E locale matrix |
| V1-UX-008 | tray/background lifecycle | required | close-choice, resume, notification tests |

## 4. Security and credentials

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-SEC-001 | sandboxed renderer, context isolation, no Node integration | required | runtime configuration tests |
| V1-SEC-002 | typed allowlisted preload IPC | required | 100% channel contract coverage |
| V1-SEC-003 | CSP/navigation/external link protections | required | security E2E/fuzz tests |
| V1-SEC-004 | OS-backed `safeStorage` | required | Windows/macOS/Linux keyring tests |
| V1-SEC-005 | reject Linux `basic_text` persistence | required | backend detection tests |
| V1-SEC-006 | session and expert `.env` modes | required | warnings, import/export, redaction tests |
| V1-SEC-007 | portable encrypted vault | required | Argon2id/XChaCha20 tamper/wrong-password/migration tests |
| V1-SEC-008 | secret-free logs/support bundles | required | automated secret injection/redaction suite |
| V1-SEC-009 | dependency/license/secret scans | required | CI release gates |

## 5. Project, media and sample data

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-DATA-001 | SQLite project database and versioned JSON manifest | required | schema/migration fixtures |
| V1-DATA-002 | independent image/video/Atlas/detection/generated paths | required | project-path E2E |
| V1-DATA-003 | browse, drag/drop, open-folder, relink | required | platform E2E |
| V1-DATA-004 | adaptive managed-copy/external-reference import | required | disk estimate and behavior tests |
| V1-DATA-005 | resumable hash/dedup/index/proxy generation | required | crash/fault tests |
| V1-DATA-006 | portable project materialization | required | export/import round trip |
| V1-DATA-007 | Quick Start corpus | required | download/import/rights manifest smoke |
| V1-DATA-008 | Full Research corpus | required | multipart verification and scale test |
| V1-DATA-009 | sanitized complete prompts/provenance | required | redaction/privacy/license verifier |
| V1-DATA-010 | dedicated immutable corpus releases | required | manifest/tag/asset consistency test |

## 6. API automation

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-API-001 | Agnes image generation | required | fake-provider + controlled real smoke |
| V1-API-002 | Agnes asynchronous video generation | required | submit/poll/recover/download tests |
| V1-API-003 | credential profiles and rotation | required | policy/state tests |
| V1-API-004 | pacing/concurrency/jitter | required | deterministic scheduler tests |
| V1-API-005 | retry/backoff/Retry-After/circuit breaker | required | complete error decision table |
| V1-API-006 | quota/time/request/size/disk stop guards | required | boundary and fault tests |
| V1-API-007 | pause/checkpoint/resume/restart recovery | required | kill/restart E2E |
| V1-API-008 | Generated Media collection | required | validation/quarantine/enrollment tests |
| V1-API-009 | optional named-corpus auto enrollment | required | success-only rule tests |
| V1-API-010 | per-user OS scheduling helper | required | Task Scheduler/LaunchAgent/systemd-user tests |

## 7. Atlas Studio and document production

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-ATL-001 | complete image and video cohort pipeline | required | golden corpus equivalence |
| V1-ATL-002 | immutable analysis snapshots | required | mutation-prevention tests |
| V1-ATL-003 | primary/extended/full evidence | required | deterministic rendering fixtures |
| V1-ATL-004 | hybrid structured/freeform editor | required | editor command/migration/E2E tests |
| V1-ATL-005 | rich text, undo/redo, autosave, revisions | required | crash-safe journal tests |
| V1-ATL-006 | seven built-in templates | required | visual and PDF golden matrix |
| V1-ATL-007 | declarative custom template import/export | required | schema/quarantine/security tests |
| V1-ATL-008 | static PDF export and preflight | required | fonts/page breaks/manifest tests |
| V1-ATL-009 | 10/50/90 video strip default | required | frame extraction golden tests |
| V1-ATL-010 | poster/timestamp/strip/keyframe overrides | required | block and batch tests |
| V1-ATL-011 | 500-page report support | required | performance/memory benchmark |

## 8. Detection Studio

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-DET-001 | YOLOX-Tiny/S/L | required | real inference, adapter and license manifest tests |
| V1-DET-002 | NanoDet-Plus m-320/m-416/m-1.5x-416 | required | real inference, adapter and license manifest tests |
| V1-DET-003 | model registry, hash and provenance | required | registry schema/signature tests |
| V1-DET-004 | bundled/download/user-supplied/blocked rights states | required | model acquisition E2E |
| V1-DET-005 | CPU ONNX Runtime | required | all-platform smoke |
| V1-DET-006 | DirectML Windows | required | real hardware test |
| V1-DET-007 | CUDA Windows/Linux | required | real hardware test |
| V1-DET-008 | CoreML macOS | required | arm64/x64 supported-hardware test |
| V1-DET-009 | provider packs and CPU fallback | required | install/failure/fallback tests |
| V1-DET-010 | job/stage/item progress | required | event aggregation tests |
| V1-DET-011 | checkpoint/pause/resume/cancel/partial results | required | kill/restart and data-integrity tests |
| V1-DET-012 | multi-model comparison without false accuracy claims | required | schema/UI wording tests |
| V1-DET-013 | user-supplied ONNX known/declarative adapters | required | validation and golden tests |
| V1-DET-014 | sandboxed WASM postprocessor | required | capability, timeout, memory and fuzz tests |

## 9. Performance and large corpus

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-PERF-001 | 10,000-image / 1,000-video design corpus | required | benchmark dataset run |
| V1-PERF-002 | display-pixel-aware proxy pyramid | required | decode/network/memory test |
| V1-PERF-003 | virtualized large collections | required | scroll/frame benchmark |
| V1-PERF-004 | SQLite keyset pagination | required | 100k-row query benchmark |
| V1-PERF-005 | Pinia + TanStack Vue Query separation | required | cache/state tests |
| V1-PERF-006 | bounded worker pools/backpressure | required | load and starvation tests |
| V1-PERF-007 | bounded RAM/disk caches | required | pressure/eviction tests |
| V1-PERF-008 | low/mid/high, SSD/HDD reference tiers | required | published benchmark report |

## 10. Sync, publishing, telemetry and integration

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-INT-001 | GitHub Release publisher | required | draft/publish/test-repo E2E |
| V1-INT-002 | immutable namespace/history guards | required | destructive-operation rejection tests |
| V1-INT-003 | cloud-folder project sync | required | two-device/conflict/partial-sync tests |
| V1-INT-004 | content-addressed blobs + snapshot/journal protocol | required | deterministic merge/recovery fixtures |
| V1-INT-005 | local diagnostics/support bundles | required | redaction and round-trip tests |
| V1-INT-006 | default-off opt-in remote telemetry | required | consent/payload preview/endpoint tests |

## 11. Update, migration and recovery

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-UPD-001 | pre-update/migration backup | required | induced-failure restore test |
| V1-UPD-002 | transactional schema migrations | required | interruption/idempotence matrix |
| V1-UPD-003 | settings/project/credential/report/model/template/scheduler/sync migration | required | old fixture matrix |
| V1-UPD-004 | Recovery Center | required | corrupt/newer/incomplete state E2E |
| V1-UPD-005 | binary rollback guidance and data compatibility checks | required | update rollback scenario |
| V1-UPD-006 | no silent downgrade | required | newer-schema refusal tests |

## 12. Quality gates

| ID | Requirement | v1 | Required evidence |
|---|---|---:|---|
| V1-QA-001 | SDD traceability | required | decision→requirement→test→release mapping |
| V1-QA-002 | TDD for deterministic domain/boundary work | required | feature PR evidence |
| V1-QA-003 | unit/component/IPC/engine/E2E suites | required | CI matrices |
| V1-QA-004 | migration and fault injection | required | deliberate failure logs |
| V1-QA-005 | visual/accessibility/localization suites | required | reviewed artifacts |
| V1-QA-006 | real install/update tests for all packages | required | clean-machine runs |
| V1-QA-007 | real DirectML/CUDA/CoreML tests | required | hardware run evidence |
| V1-QA-008 | coverage and mutation gates | required | published reports |
| V1-QA-009 | license/SBOM/notices/rights checks | required | release verifier |
| V1-QA-010 | zero release-blocking quarantined tests | required | CI policy check |

## 13. Explicit non-goals that remain valid

The complete-v1 principle does not add:

- a repository-operated cloud account service;
- mandatory API usage;
- model training;
- collaborative simultaneous multi-user document editing;
- animated GIF playback inside PDF;
- a native mobile app;
- execution of untrusted native/Python scripts;
- unsupported claims of detector accuracy on unlabeled media;
- redistribution of assets without verified rights.

These are product or legal boundaries, not ordinary feature deferrals.

## 14. Final acceptance

Stable `1.0.0` requires:

1. every required row linked to passing evidence;
2. all six package types built and exercised;
3. signing/notarization and update paths operational;
4. CPU plus DirectML/CUDA/CoreML provider evidence;
5. large-corpus performance gates passed;
6. migrations and recovery proven through fault injection;
7. five locales, accessibility and visual review complete;
8. rights manifests, SBOM, notices and checksums complete;
9. no open P0/P1 product decision;
10. user approval of the release candidate.