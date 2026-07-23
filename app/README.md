# Media Experiment Ledger Studio

Cross-platform Electron desktop application for Atlas analysis, object detection and durable media automation. The implementation is integrated on `app-main`; normative requirements and release gates are defined by `../app-product-contract.json` and `../docs/app/`.

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
python scripts/build_engine.py
npm run build
npm run package
python scripts/smoke_packaged_app.py
```

`Desktop App CI` executes the full chain on Windows, macOS and Ubuntu. Run `29972465923` passed on all three platforms for implementation head `447ed656375c6fe934953a0991f2bf4fbcd88122`.

## Implemented executable scope

- hardened Electron window, sandboxed renderer and system tray lifecycle;
- Vue 3 + Vuetify 3 responsive application shell and five-locale navigation foundation;
- self-contained sandbox-compatible preload with separate app, diagnostics, report-template and custom-model bridges;
- SQLite settings, migrations, recovery records and durable job state;
- adaptive managed-copy/external-reference media import, hashes, deduplication, proxies and video posters;
- Agnes image/video orchestration with retries, budgets, circuit breakers, polling and restart recovery;
- Generated Media verification, quarantine and optional named-corpus enrollment;
- mixed image/video Atlas generation with 10/50/90 evidence strips and resumable manifests;
- hybrid report editor, autosave, revisions, seven built-in templates and validated custom-template snapshots;
- sandboxed PDF generation with preflight warnings and deterministic manifest;
- YOLOX and NanoDet-Plus ONNX detection, model registry, CPU fallback and optional hardware providers;
- declarative user-supplied model manifests restricted to built-in verified decoders;
- Model Manager, Job Center, Sample Corpora, Settings, Update & Recovery and Support & Privacy surfaces;
- PyInstaller self-contained engine and electron-builder platform package matrix;
- release evidence generation, checksums, SBOM, notices and signing gates.

## Packaging targets

- Windows x64 NSIS installer and portable executable;
- macOS arm64 and x64 DMG/update ZIP;
- Linux x64 AppImage and `.deb`.

Unsigned artifacts are restricted to labeled prereleases. Stable publication requires Windows code signing, Apple signing/notarization and release checksum/update signing credentials.

## Rights boundary

Model weights and sample data are not licensed merely because the application source is Apache-2.0. The Model Manager accepts verified user-supplied artifacts; repository distribution remains blocked until artifact-level redistribution rights, provenance and hashes are approved.
