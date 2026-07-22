# Specification Round 03 Primary References

Status: supporting reference record for accepted round-three decisions. Versions and maintenance status MUST be rechecked when implementation starts and before stable Release.

## Packaging and updates

- electron-builder documentation: https://www.electron.build/docs/
- electron-builder targets: https://www.electron.build/docs/targets/
- electron-builder auto update: https://www.electron.build/docs/features/auto-update/
- electron-updater API: https://www.electron.build/docs/api/electron-updater/
- macOS targets/signing configuration: https://www.electron.build/mac/
- AppImage behavior: https://www.electron.build/docs/appimage/

Relevant upstream statements at decision time:

- electron-builder supports NSIS and portable Windows targets, DMG on macOS, and AppImage/DEB on Linux;
- electron-updater supports NSIS, macOS, AppImage and DEB update flows;
- macOS app signing is required for auto update;
- macOS update metadata requires the ZIP target alongside DMG;
- Linux package behavior remains target-specific.

## Electron credentials and testing

- Electron safeStorage: https://www.electronjs.org/docs/latest/api/safe-storage
- Electron automated testing: https://www.electronjs.org/docs/latest/tutorial/automated-testing
- Playwright Electron API: https://playwright.dev/docs/api/class-electron

`safeStorage.getSelectedStorageBackend()` can report `basic_text` on Linux. The specification therefore rejects automatic persistent secret storage in that state and requires secure alternatives.

## Python engine runtime

- python-build-standalone repository: https://github.com/astral-sh/python-build-standalone
- releases: https://github.com/astral-sh/python-build-standalone/releases

The project describes its artifacts as standalone, redistributable Python builds. Exact runtime versions, licenses and hashes remain release-pinned.

## Portable encrypted vault

- libsodium documentation: https://doc.libsodium.org/
- password hashing: https://libsodium.gitbook.io/doc/password_hashing
- Argon2id API: https://libsodium.gitbook.io/doc/password_hashing/default_phf
- XChaCha20-Poly1305: https://libsodium.gitbook.io/doc/secret-key_cryptography/aead/chacha20-poly1305/xchacha20-poly1305_construction

The product uses reviewed library primitives and a versioned envelope. It does not implement a custom cipher, password KDF or authentication construction.

## ONNX Runtime execution providers

- execution providers: https://onnxruntime.ai/docs/execution-providers/
- DirectML: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html
- CUDA: https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html
- CoreML: https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html

CPU remains the universal fallback. DirectML, CUDA and CoreML packages and compatibility MUST be pinned/tested against the exact app engine release.

## Vue state and tests

- Vue state management guidance: https://vuejs.org/guide/scaling-up/state-management.html
- Pinia: https://pinia.vuejs.org/
- TanStack Vue Query installation: https://tanstack.com/query/latest/docs/framework/vue/installation
- Vue Test Utils: https://test-utils.vuejs.org/
- Vitest: https://vitest.dev/guide/
- Playwright best practices: https://playwright.dev/docs/best-practices

Pinia owns UI/session state. TanStack Vue Query owns bounded asynchronous query state over typed IPC. SQLite remains authoritative.

## Reference discipline

- Prefer official documentation and upstream repositories.
- Pin exact dependency/runtime versions in lockfiles and Release manifests.
- Recheck license and maintenance status before implementation and every stable Release.
- A supporting reference does not override the normative contract or grant rights to third-party artifacts.