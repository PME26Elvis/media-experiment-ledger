# Desktop Product Primary References

This file records the primary upstream documentation and repository materials that informed the initial specification. It is not a substitute for a dependency/license audit at implementation or Release time.

Versions and external capabilities can change. Before implementation begins and before every stable Release, re-check current official documentation, package support, security guidance and artifact licenses.

## 1. Electron

### Core documentation

- Electron documentation: https://www.electronjs.org/docs/latest/
- Process model: https://www.electronjs.org/docs/latest/tutorial/process-model
- Context isolation: https://www.electronjs.org/docs/latest/tutorial/context-isolation
- Security checklist: https://www.electronjs.org/docs/latest/tutorial/security
- BrowserWindow/webPreferences: https://www.electronjs.org/docs/latest/api/browser-window
- contextBridge: https://www.electronjs.org/docs/latest/api/context-bridge
- IPC tutorial: https://www.electronjs.org/docs/latest/tutorial/ipc

Specification implications:

- renderer privilege must be minimized;
- `contextIsolation` and narrow preload APIs are mandatory;
- arbitrary navigation/windows/permissions are denied by default;
- a generic IPC pass-through is not acceptable.

### Secret storage

- `safeStorage`: https://www.electronjs.org/docs/latest/api/safe-storage

Review notes:

- uses operating-system-provided cryptography/storage behavior;
- Windows, macOS and Linux backend behavior differs;
- Linux may not provide a secure keyring in every environment;
- current APIs and re-encryption guidance must be rechecked at implementation time;
- no plaintext fallback is allowed without explicit user choice.

### Updates and distribution

- `autoUpdater`: https://www.electronjs.org/docs/latest/api/auto-updater
- Updating applications tutorial: https://www.electronjs.org/docs/latest/tutorial/updates
- Application distribution: https://www.electronjs.org/docs/latest/tutorial/application-distribution
- Code signing: https://www.electronjs.org/docs/latest/tutorial/code-signing
- macOS notarization: https://www.electronjs.org/docs/latest/tutorial/code-signing#signing-and-notarizing-macos-builds

Review notes:

- Electron's built-in autoUpdater is oriented to macOS and Windows; Linux update behavior must be package-specific;
- macOS automatic update/signing identity requirements must be verified with the selected packager;
- installer/update success is distinct from project/settings migration success;
- package signing/notarization strategy remains a Phase 0 decision.

### Packaging

- Electron Forge documentation: https://www.electronforge.io/
- Forge Vite plugin: https://www.electronforge.io/config/plugins/vite
- Forge makers: https://www.electronforge.io/config/makers

Review notes:

- Forge + Vite is provisional rather than permanently fixed;
- compare current maintained maker/updater support after the v1 package matrix is approved;
- native Node modules require Electron ABI rebuilds and platform CI.

## 2. Vue 3

- Vue Composition API FAQ: https://vuejs.org/guide/extras/composition-api-faq.html
- `<script setup>` documentation: https://vuejs.org/api/sfc-script-setup.html
- TypeScript with Composition API: https://vuejs.org/guide/typescript/composition-api.html
- Single-File Components: https://vuejs.org/guide/scaling-up/sfc.html
- Vue Router: https://router.vuejs.org/
- Pinia: https://pinia.vuejs.org/

Specification implications:

- Composition API and `<script setup lang="ts">` are the renderer convention;
- component props/emits/models are typed;
- state tooling does not replace SQLite as the large-data source of truth;
- exact stable versions are pinned when implementation starts.

## 3. Vuetify 3

- Vuetify documentation: https://vuetifyjs.com/en/
- Grid system: https://vuetifyjs.com/en/components/grids/
- Hover component: https://vuetifyjs.com/en/components/hover/
- Transitions: https://vuetifyjs.com/en/styles/transitions/
- Display and breakpoints: https://vuetifyjs.com/en/features/display-and-platform/
- Theme: https://vuetifyjs.com/en/features/theme/
- Accessibility: https://vuetifyjs.com/en/getting-started/accessibility/

Specification implications:

- `v-container`, `v-row` and `v-col` define primary responsive layouts;
- `v-hover` is required on meaningful interactive surfaces but cannot be the only interaction path;
- built-in/custom transitions must honor reduced-motion preferences;
- semantic colors and icons are part of component acceptance criteria;
- current stable Vuetify 3 syntax must be revalidated at implementation time.

## 4. SQLite and project storage

- SQLite documentation: https://www.sqlite.org/docs.html
- Write-Ahead Logging: https://www.sqlite.org/wal.html
- Backup API: https://www.sqlite.org/backup.html
- Foreign keys: https://www.sqlite.org/foreignkeys.html
- Transaction documentation: https://www.sqlite.org/lang_transaction.html

Specification implications:

- per-project indexed state uses SQLite with foreign keys and transactions;
- WAL suitability depends on filesystem behavior;
- cloud/network filesystems require explicit support policy;
- migration and backup logic must be tested under interruption.

Potential Node binding (provisional, not selected):

- better-sqlite3: https://github.com/WiseLibs/better-sqlite3

## 5. Media processing

### FFmpeg

- FFmpeg documentation: https://ffmpeg.org/documentation.html
- FFprobe documentation: https://ffmpeg.org/ffprobe.html
- FFmpeg legal/licensing information: https://ffmpeg.org/legal.html

Review notes:

- app packaging must review the exact FFmpeg build configuration and license obligations;
- critical video tests use real FFmpeg/FFprobe with generated fixtures;
- video format/container support is derived from the packaged build, not only file extension.

### Image proxy candidate

- Sharp: https://sharp.pixelplumbing.com/
- Sharp repository/license: https://github.com/lovell/sharp

Review notes:

- Sharp/libvips is provisional;
- verify Electron/native packaging, formats and licenses before selection;
- display-pixel-aware proxy architecture is independent of the chosen implementation library.

## 6. ONNX Runtime

- ONNX Runtime documentation: https://onnxruntime.ai/docs/
- JavaScript/Node API: https://onnxruntime.ai/docs/get-started/with-javascript/
- Execution providers: https://onnxruntime.ai/docs/execution-providers/
- ONNX Runtime repository/license: https://github.com/microsoft/onnxruntime

Specification implications:

- CPU is the universal baseline;
- CUDA, DirectML, CoreML and other providers are gated by packaged-platform tests;
- model adapters pin input/output/pre/postprocessing semantics;
- real runtime smoke is required, not only model-file parsing.

## 7. YOLOX

- Official repository: https://github.com/Megvii-BaseDetection/YOLOX
- Official model zoo in repository README: https://github.com/Megvii-BaseDetection/YOLOX#benchmark
- Source-code license: https://github.com/Megvii-BaseDetection/YOLOX/blob/main/LICENSE
- Releases: https://github.com/Megvii-BaseDetection/YOLOX/releases

Initial catalog references:

- YOLOX-Nano;
- YOLOX-Tiny;
- YOLOX-S;
- YOLOX-M;
- YOLOX-L;
- YOLOX-X.

Important review boundary:

- The official source repository is Apache-2.0, but each pretrained/downloaded/exported model artifact must still receive an explicit distribution and provenance review before it is bundled in the desktop installer.
- The existing repository currently pins and verifies a YOLOX-Tiny ONNX artifact through its own model lock; the desktop app must either reuse that exact identity or introduce a separately versioned, verified model registry entry.

## 8. NanoDet

- Official repository: https://github.com/RangiLyu/nanodet
- Model zoo: https://github.com/RangiLyu/nanodet#model-zoo
- Releases: https://github.com/RangiLyu/nanodet/releases
- Source-code license: https://github.com/RangiLyu/nanodet/blob/main/LICENSE

Initial catalog references:

- NanoDet-Plus-m-320;
- NanoDet-Plus-m-416;
- NanoDet-Plus-m-1.5x-320;
- NanoDet-Plus-m-1.5x-416.

Important review boundary:

- The official source repository is Apache-2.0.
- The current repository uses the official immutable pre-exported NanoDet-Plus-m-320 ONNX asset from the `v1.0.0-alpha-1` Release and pins size/SHA-256.
- Larger variants must independently verify exact artifact, format, output adapter, runtime, resource use and redistribution status.

## 9. Existing Media Experiment Ledger source material

These files are the current product/algorithm evidence that the app specifications deliberately restate or import through compatibility layers:

### Repository-wide contract and preferences

- `AGENTS.md`
- `project-contract.json`
- `docs/PROJECT_CONTRACT.md`

### Agnes automation

- `agnes_media_harvester.py`
- `agnes_media_config.yaml`
- `prompts/image_prompts.jsonl`
- `prompts/video_prompts.jsonl`

Key compatibility behavior to retain/expand:

- separate image and video phases;
- target-success counts;
- submission intervals;
- video polling interval/timeout;
- seed range and negative prompt;
- stop flags for quota/payment, rate limit and server busy;
- consecutive-error limits;
- atomic state writes;
- response/output JSONL and downloads.

### Prompt Repeatability Atlas

- `docs/PROMPT_REPEATABILITY_ATLAS.md`
- `docs/VIDEO_REPEATABILITY_ATLAS.md`
- `visual-analysis/config.json`
- `tools/prompt_atlas_core.py`
- `tools/prompt_atlas_data.py`
- `tools/prompt_atlas_video.py`
- `tools/prompt_atlas_build.py`
- `tools/prompt_atlas_packages.py`
- `tools/prompt_atlas_publish.py`
- `tests/test_prompt_atlas.py`
- `tests/test_prompt_atlas_video.py`

Key app compatibility areas:

- image/video cohorts remain separate;
- deterministic identity/selection;
- exact byte deduplication;
- actual decode verification;
- primary/extended/full evidence;
- video seed evidence policy;
- contain/letterbox rendering;
- all verified samples represented;
- no hidden source-media mutation.

### Detection

- `docs/YOLO_OBJECT_DETECTION_SPEC.md`
- `docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md`
- `object-detection/model-lock.json`
- `object-detection/nanodet-model-lock.json`
- `object-detection/coco-80.json`
- `tools/yolo_core.py`
- `tools/nanodet_core.py`
- `tools/build_detector_artifact.py`
- `tools/publish_detector_comparison.py`
- `tests/`

Key app compatibility areas:

- real ONNX Runtime smoke;
- pinned model and labels identity;
- original-coordinate recovery;
- class-aware NMS;
- exact workflow/run pairing in repository publication context;
- agreement/disagreement language;
- Atlas non-regression.

## 10. Release and artifact review checklist

Before any desktop stable Release, review and record:

- Electron, Node, Chromium and dependency versions;
- security advisories;
- package/signing/notarization state;
- native dependency ABI/platform builds;
- FFmpeg build and notices;
- fonts and embedding/redistribution licenses;
- Vuetify/icon assets and notices;
- model source, artifact URL, size, SHA-256 and weight license status;
- sample corpus privacy/licensing audit;
- checksums and SBOM;
- update manifest/package identity;
- migration support floor;
- actual uploaded GitHub asset size/count/hash evidence.

## 11. Reference freshness policy

- This document records the baseline as of 2026-07-22.
- External versions and platform behavior must be checked again at implementation start.
- Security and update documentation must be checked again for every stable Release.
- A changed external fact that alters an accepted contract requires a new decision-log entry rather than a silent implementation deviation.