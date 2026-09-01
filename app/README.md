# Media Experiment Ledger Studio

**Atlas · Detection · Media Automation**

Cross-platform local-first Electron desktop application for Atlas analysis, object detection and durable media automation. The implementation is integrated on [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main); normative requirements and release gates are defined by `../app-product-contract.json` and `../docs/app/`.

## Download and release status

Studio builds use the `studio-v*` Release family:

- Optional accelerator engine bundle RC.6 is requested by PR #56
- [Download resource-aware scheduler RC.5](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.5)
- [Download Hardware Runtime Center RC.4](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.4)
- [Download provider-qualified RC.3](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.3)
- [Download lifecycle-qualified RC.2](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.2)
- [Browse all Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v)
- [Open the app-main source branch](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main/app)
- [Read the desktop specification and evidence index](../docs/app/README.md)
- [Read the H1/H2 runtime delivery record](../docs/app/HARDWARE_RUNTIME_AND_RESOURCE_SCHEDULER.md)
- [Read the H3 optional accelerator bundle specification](../docs/app/OPTIONAL_ACCELERATOR_ENGINE_BUNDLES.md)
- [Track stable 1.0.0 external qualification](https://github.com/PME26Elvis/media-experiment-ledger/issues/49)

| Platform | Packages |
|---|---|
| Windows x64 | NSIS installer and portable `.exe` |
| macOS Apple Silicon | arm64 DMG and update ZIP |
| macOS Intel | x64 DMG and update ZIP |
| Linux x64 | AppImage and `.deb` |

RC.2 proves the install, in-place upgrade, independent portable/AppImage launch, removal and user-data-retention lifecycle. RC.3 adds truthful packaged provider inventory, real CoreML execution evidence and fail-closed DirectML/CUDA hardware gates. RC.4 adds the Hardware Runtime Center, generated provider self-tests and persisted production provider policy. RC.5 adds resource-aware admission, memory safety reserves, bounded warm Detection workers and actionable OOM recovery. RC.6 keeps the embedded CPU engine while adding signed, hash-pinned optional DirectML, CoreML and CUDA engine profiles with compatibility checks, atomic activation, rollback and quarantine.

Prerelease application packages may be unsigned and can show an operating-system publisher warning. Pull-request accelerator bundles use ephemeral development keys and are deliberately non-publishable. Production accelerator bundle publication requires a separately provisioned Ed25519 key. Verify public downloads with their `SHA256SUMS`. Stable publication remains blocked until Windows signing, Apple signing/notarization, signed update and bundle evidence, real DirectML/CUDA hardware qualification, Full Research corpus rights and the remaining manual evidence in issue #49 are complete.

## Development

Requirements:

- Node.js 22.x;
- Python 3.12 for engine development/building;
- platform packaging prerequisites required by `electron-builder`.

```bash
cd app
npm ci
python -m pip install -r engine/requirements.txt -r engine/requirements-build.txt
npm run dev
```

The renderer has no direct Node.js access. Privileged operations use closed typed preload bridges, durable jobs persist in SQLite/WAL, and media work runs through isolated one-shot or persistent JSON-lines Python engine protocols. Detection may use a bounded persistent worker keyed by model/provider/device so compatible ONNX Runtime sessions can remain warm until configured idle eviction.

The universal packaged engine always remains available. An optional engine is selected only when its active pointer resolves to an Ed25519-authenticated manifest and every inventoried file still matches its signed size and SHA-256. Invalid or missing optional runtimes fall back to the embedded CPU engine.

## Validation

```bash
npm audit --omit=dev --audit-level=high
npm run typecheck
npm test
python scripts/run_python_tests.py
npm run release:tools:test
python scripts/build_engine.py
npm run build
npm run package
python scripts/smoke_packaged_app.py
```

`Desktop App CI` executes the complete build and packaged-launch chain on Windows, macOS and Ubuntu. Release-request pull requests additionally build Windows x64, Linux x64, macOS arm64 and macOS Intel x64, finalize the complete evidence set and verify the public asset allowlist without creating a tag or Release.

`Optional Accelerator Engine Bundles` independently builds DirectML Windows x64, CoreML macOS arm64/x64 and CUDA Linux x64 engines. Each profile freezes and smokes the engine, materializes platform symlinks into regular transport files, signs a canonical manifest, verifies every file, and contributes a hash-pinned four-profile catalog.

## Implemented executable scope

- hardened Electron window, sandboxed renderer and system tray lifecycle;
- Vue 3 + Vuetify 3 responsive application shell and five complete locales;
- SQLite settings, migrations, recovery records and durable job state;
- adaptive managed-copy/external-reference import, hashes, deduplication, proxies and video posters;
- bounded image/video automation with retries, budgets, circuit breakers and restart recovery;
- mixed image/video Atlas generation with evidence strips and resumable manifests;
- hybrid report editor, autosave, revisions, built-in/custom templates and static PDF export;
- YOLOX and NanoDet-Plus ONNX detection with packaged provider inventory and explicit fallback semantics;
- Hardware Runtime Center with Electron adapter evidence, packaged ORT inventory and profiling-based self-tests;
- resource-aware Job Scheduler with CPU/provider-device admission, memory budgets, safety reserves and warm Detection workers;
- signed optional accelerator engine install, activate, rollback, quarantine and removal lifecycle;
- Model Manager, Job Center, Sample Corpora, Settings, Updates, Recovery and diagnostics;
- self-contained Python engine, application package matrix, per-bundle SBOM/notices/native inventory, checksums and consolidated launch evidence.

## Release workflow

[`release-request.json`](release-request.json) is the canonical Studio application release request. Updating it on `app-main` triggers the reusable release core.

- `version: "auto"` chooses the next unused `alpha.N` or `beta.N` version.
- Existing `studio-v*` tags are never edited or clobbered.
- Comma-, newline- or array-based feature lists become Markdown bullets.
- All platform jobs build the same resolved source commit.
- Pull requests force `publish=false` and `draft=true` while executing the complete release matrix.
- Publication first creates a private draft, uploads and verifies every asset, then publishes only when `draft` is false.
- Taipei release date and UTC timestamps are both retained in release evidence.

The accelerator bundle workflow is separate because production bundle signing, runtime redistribution rights and host compatibility have a different trust boundary from the Electron application package.

See [`docs/app/RELEASE_RUNBOOK.md`](../docs/app/RELEASE_RUNBOOK.md) for the complete release and qualification rules.

## Rights boundary

Model weights, sample data, ONNX Runtime distributions and native accelerator libraries are not licensed merely because the application source is Apache-2.0. Public bundle distribution remains blocked until artifact-level redistribution rights, provenance, hashes, SBOM and notices are approved.
