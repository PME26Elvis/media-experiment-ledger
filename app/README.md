# Media Experiment Ledger Studio

**Atlas · Detection · Media Automation**

Cross-platform local-first Electron desktop application for Atlas analysis, object detection and durable media automation. The implementation is integrated on [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main); normative requirements and release gates are defined by `../app-product-contract.json` and `../docs/app/`.

## Download and release status

Studio builds use the `studio-v*` Release family:

- [Browse Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v)
- [Download lifecycle-qualified RC.2](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/studio-v1.0.0-rc.2)
- [Open the app-main source branch](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main/app)
- [Read the desktop specification and evidence index](../docs/app/README.md)
- [Track stable 1.0.0 external qualification](https://github.com/PME26Elvis/media-experiment-ledger/issues/49)

| Platform | Packages |
|---|---|
| Windows x64 | NSIS installer and portable `.exe` |
| macOS Apple Silicon | arm64 DMG and update ZIP |
| macOS Intel | x64 DMG and update ZIP |
| Linux x64 | AppImage and `.deb` |

RC.2 proves the install, in-place upgrade, independent portable/AppImage launch, removal and user-data-retention lifecycle. RC.3 adds truthful packaged provider inventory, real CoreML execution evidence and fail-closed DirectML/CUDA hardware gates.

Prerelease packages may be unsigned and can show an operating-system publisher warning. Verify downloads with `SHA256SUMS`. Stable publication remains blocked until Windows signing, Apple signing/notarization, signed update evidence, real DirectML/CUDA hardware qualification, Full Research corpus rights and the remaining manual evidence in issue #49 are complete.

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

The renderer has no direct Node.js access. Privileged operations use closed typed preload bridges, durable jobs persist in SQLite/WAL, and media work runs through the isolated JSON-lines Python engine protocol.

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

## Implemented executable scope

- hardened Electron window, sandboxed renderer and system tray lifecycle;
- Vue 3 + Vuetify 3 responsive application shell and five complete locales;
- SQLite settings, migrations, recovery records and durable job state;
- adaptive managed-copy/external-reference import, hashes, deduplication, proxies and video posters;
- bounded image/video automation with retries, budgets, circuit breakers and restart recovery;
- mixed image/video Atlas generation with evidence strips and resumable manifests;
- hybrid report editor, autosave, revisions, built-in/custom templates and static PDF export;
- YOLOX and NanoDet-Plus ONNX detection with packaged provider inventory and explicit fallback semantics;
- Model Manager, Job Center, Sample Corpora, Settings, Updates, Recovery and diagnostics;
- self-contained Python engine, six package types, SBOM, notices, checksums and consolidated launch evidence.

## Release workflow

[`release-request.json`](release-request.json) is the canonical release request. Updating it on `app-main` triggers the reusable release core.

- `version: "auto"` chooses the next unused `alpha.N` or `beta.N` version.
- Existing `studio-v*` tags are never edited or clobbered.
- Comma-, newline- or array-based feature lists become Markdown bullets.
- All platform jobs build the same resolved source commit.
- Pull requests force `publish=false` and `draft=true` while executing the complete release matrix.
- Publication first creates a private draft, uploads and verifies every asset, then publishes only when `draft` is false.
- Taipei release date and UTC timestamps are both retained in release evidence.

See [`docs/app/RELEASE_RUNBOOK.md`](../docs/app/RELEASE_RUNBOOK.md) for the complete release and qualification rules.

## Rights boundary

Model weights and sample data are not licensed merely because the application source is Apache-2.0. Repository distribution remains blocked until artifact-level redistribution rights, provenance and hashes are approved.
