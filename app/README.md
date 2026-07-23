# Media Experiment Ledger Studio

Implementation branch for the Electron desktop product defined by `../app-product-contract.json` and `../docs/app/`.

## Development

```bash
cd app
npm install
python -m pip install -r engine/requirements.txt
npm run dev
```

The renderer has no direct Node.js access. Privileged operations use the typed preload API, durable jobs persist in SQLite/WAL, and media work runs through the JSON-lines Python engine protocol.

## Validation

```bash
npm run typecheck
npm test
PYTHONPATH=engine python -m unittest discover -s engine/tests -p 'test_*.py'
npm run build
npm run package
```

## Current executable scope

- hardened Electron window and system tray;
- Vue 3 + Vuetify 3 responsive application shell;
- five-language navigation foundation;
- SQLite settings and durable job records;
- independent Import, Automation, Atlas and Detection routes;
- Python engine operations for media scan/hash, image Atlas sheets, Agnes submission, verified ONNX session execution and sample downloads;
- updater IPC and six-target electron-builder configuration;
- cross-platform Actions validation.

Model weights are never bundled without artifact-level redistribution approval. Detection jobs require Model Manager to provide a verified `model_path`; family-specific output decoding is tracked by the model registry and must not be inferred from arbitrary ONNX output.
