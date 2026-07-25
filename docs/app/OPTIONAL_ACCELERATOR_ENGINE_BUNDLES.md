# Optional Accelerator Engine Bundles

Status: `implemented_in_rc_6_external_production_signing_key_pending`

## Purpose

Media Experiment Ledger Studio keeps a universal CPU-capable engine inside every application package. Optional accelerator bundles replace only the engine process selected for new work; they do not replace or patch the Electron application, SQLite data, renderer, recovery data or the embedded CPU fallback.

Profiles defined by v1:

- `directml` for Windows x64;
- `coreml` for macOS arm64 and Intel x64;
- `cuda` for compatible Linux x64 and, when separately qualified, Windows x64.

## Trust model

An accelerator bundle is fail-closed. Installation requires all of the following:

1. schema version and identifier validation;
2. a canonical manifest payload whose serialized fields exactly match the signed payload;
3. an Ed25519 signature from the installed accelerator-bundle trust key;
4. safe relative paths with no traversal, absolute path or symbolic-link entries;
5. exact size and SHA-256 verification for every inventoried file;
6. exact engine-entrypoint SHA-256 verification;
7. host platform and architecture compatibility;
8. compatible Studio and operating-system versions;
9. profile/provider consistency;
10. CUDA runtime, cuDNN and minimum NVIDIA driver checks when declared;
11. a real invocation of the copied engine's `providers` operation;
12. exact ONNX Runtime version and required provider registration.

Provider registration remains distinct from model-specific assigned-node evidence. Installing a CUDA or DirectML bundle does not close the real-hardware qualification items in issue #49.

## On-disk layout

```text
<userData>/accelerator-bundles/
  active.json
  installed/<bundle-id>/<version>/
    accelerator-bundle-manifest.json
    verification.json
    engine/...
    SBOM.spdx.json
    THIRD_PARTY_NOTICES.txt
    native-library-inventory.json
  staging/<transaction-id>/
  quarantine/<bundle-id>/<version>-<timestamp>/
```

Installation copies verified files into a staging directory under the same filesystem and renames the complete directory into `installed`. The active pointer is written to a temporary file and atomically renamed. This prevents a crash from exposing a partially copied runtime as active.

## Activation and rollback

Activation is allowed only when no running or queued job exists. Before switching:

- the installed entrypoint hash is verified again;
- provider inventory is executed again;
- warm Detection workers are destroyed;
- cached provider inventory and active engine resolution are cleared.

`active.json` retains a bounded history of the ten most recent runtime identities. Rollback selects the newest still-installed and still-self-testable runtime. If no valid previous bundle exists, rollback removes the optional pointer and returns to the embedded CPU engine.

## Quarantine

A bundle is moved to quarantine when installation, file verification, runtime compatibility or provider self-test fails after staging begins. Operators may also quarantine an installed bundle manually. Quarantining the active bundle removes the active pointer first, resets engine workers and returns the application to the universal CPU engine.

Quarantine preserves:

- the manifest where available;
- verification evidence;
- the failure or operator reason;
- all copied files for later diagnosis.

## Bundle evidence

Every bundle build produces:

- `accelerator-bundle-manifest.json`;
- `SBOM.spdx.json`;
- `THIRD_PARTY_NOTICES.txt`;
- `native-library-inventory.json`;
- `bundle-build-evidence.json`;
- a ZIP transport archive;
- a release-level SHA-256 catalog when the full matrix is finalized.

The builder rejects engines that do not register the profile's required provider. The application repeats provider inventory after copying, so CI build evidence alone is not trusted for local activation.

## Build and publication workflow

`.github/workflows/app-accelerator-bundles.yml` builds four profiles:

1. Windows x64 DirectML;
2. macOS Apple Silicon CoreML;
3. macOS Intel x64 CoreML;
4. Linux x64 CUDA with packaged CUDA 12 and cuDNN 9 dependencies.

Pull requests use ephemeral Ed25519 keys only to prove deterministic signing and verification behavior. These artifacts are explicitly non-publishable. Public bundle publication requires the repository secret `ACCELERATOR_BUNDLE_ED25519_PRIVATE_KEY`; the workflow refuses publication without it and refuses any matrix containing development-key evidence.

A user-specific public key at `<userData>/accelerator-bundle-public-key.pem` overrides the packaged trust key, enabling controlled key rotation and private enterprise/testing bundle channels. The existing update public key remains a fallback trust location until a production accelerator-specific key is provisioned.

## Hardware Runtime Center

The Hardware Runtime Center exposes:

- current base or optional runtime identity;
- host platform, architecture, Studio version and NVIDIA driver detection;
- trust-anchor availability;
- installed profile, ORT version and required providers;
- signature, file and self-test evidence;
- install, activate, rollback, quarantine and remove operations;
- quarantined bundle reasons.

The resource scheduler continues to operate independently. A bundle provides a runtime implementation; scheduler policies still govern provider/device concurrency, declared memory budgets and safety reserves.

## Stable boundary

RC.6 completes the software implementation and CI build matrix. Stable `1.0.0` still requires the external trust and hardware evidence in issue #49, including a real production signing key, signed release verification, DirectML/CUDA assigned-node evidence and final operator acceptance.
