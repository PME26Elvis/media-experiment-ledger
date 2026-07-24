# Primary References and Review Checklist

This file records the primary upstream references that implementation must re-check at the time each dependency or artifact is pinned. It is not a substitute for lockfiles, SBOMs, license texts or artifact-level review.

## Electron

- Electron documentation: `https://www.electronjs.org/docs/latest/`
- Security checklist: `https://www.electronjs.org/docs/latest/tutorial/security`
- Context isolation: `https://www.electronjs.org/docs/latest/tutorial/context-isolation`
- Process sandboxing: `https://www.electronjs.org/docs/latest/tutorial/sandbox`
- `safeStorage`: `https://www.electronjs.org/docs/latest/api/safe-storage`
- `autoUpdater`: `https://www.electronjs.org/docs/latest/api/auto-updater`
- License: `https://github.com/electron/electron/blob/main/LICENSE`

Implementation must pin an Electron version and verify all breaking changes/security guidance at scaffold time rather than relying on this specification date.

## Vue 3

- Vue documentation: `https://vuejs.org/`
- Composition API FAQ: `https://vuejs.org/guide/extras/composition-api-faq.html`
- `<script setup>`: `https://vuejs.org/api/sfc-script-setup.html`
- Vue core license: `https://github.com/vuejs/core/blob/main/LICENSE`

Required project use is Composition API with `<script setup lang="ts">` in ordinary components.

## Vuetify 3

- Documentation: `https://vuetifyjs.com/`
- Grid system: `https://vuetifyjs.com/en/components/grids/`
- Hover: `https://vuetifyjs.com/en/components/hover/`
- Transitions: `https://vuetifyjs.com/en/styles/transitions/`
- Framework repository/license: `https://github.com/vuetifyjs/vuetify`

Important boundary: the open-source Vuetify framework and separately sold Vuetify Store themes/templates are not the same licensing surface. Public repository code must use the framework and self-authored/open-licensed assets unless exact premium-asset redistribution rights are documented.

## Packaging and updates

### electron-builder / electron-updater candidate

- Configuration: `https://www.electron.build/docs/configuration/`
- Windows targets: `https://www.electron.build/docs/win/`
- macOS targets: `https://www.electron.build/mac/`
- AppImage: `https://www.electron.build/docs/appimage/`
- Auto update: `https://www.electron.build/docs/features/auto-update/`
- `electron-updater`: `https://www.electron.build/docs/api/electron-updater/`

This toolchain is the current recommendation for the accepted package matrix because it supports NSIS, Windows portable, DMG/update ZIP, AppImage and `.deb`, with update metadata for installed targets. It remains an open architecture decision until APP-Q-003 is accepted.

### Electron Forge alternative

- Documentation: `https://www.electronforge.io/`
- Auto update: `https://www.electronforge.io/advanced/auto-update`
- Repository/license: `https://github.com/electron/forge`

Forge remains a valid Electron build toolkit, but the implementation must compare its current maker/update coverage against all six required artifacts before selecting it.

## SQLite and persistence

The implementation must select a maintained SQLite binding only after checking Electron/native ABI packaging, transaction/WAL support, license, prebuilt binaries for every required architecture, migration behavior, SBOM provenance and crash recovery. No binding is fixed yet.

## Agnes integration

Repository baseline files:

- `agnes_media_harvester.py`
- `agnes_media_config.yaml`

Provider endpoints, models, error responses, terms and rate limits are external and may change. Before implementation, re-verify official API documentation/terms, keep provider adapters versioned, redact keys/signed URLs, and distinguish API success from durable local download/decode success.

## YOLOX

- Official repository: `https://github.com/Megvii-BaseDetection/YOLOX`
- Repository code license: Apache-2.0 as stated by upstream.
- Current repository model lock: `object-detection/model-lock.json`

Artifact review requirement:

- do not infer pretrained-weight redistribution permission solely from the source repository license;
- record exact artifact URL, tag, size, SHA-256, conversion provenance and artifact-specific terms/clarification;
- default to download-on-demand or user-supplied until bundling is explicitly approved;
- re-check upstream issue/discussion history for weight-license clarification before stable release.

## NanoDet-Plus

- Official repository: `https://github.com/RangiLyu/nanodet`
- Repository code license: Apache-2.0 as stated by upstream.
- Official Releases/model checkpoints: `https://github.com/RangiLyu/nanodet/releases`
- Current repository model lock: `object-detection/nanodet-model-lock.json`

Artifact review requirement is the same as YOLOX. An official Release asset and Apache-2.0 source repository are useful provenance, but installer redistribution still requires an explicit artifact record.

## ONNX Runtime

- Official documentation: `https://onnxruntime.ai/docs/`
- Repository: `https://github.com/microsoft/onnxruntime`
- Execution providers: `https://onnxruntime.ai/docs/execution-providers/`

Before selecting CPU/DirectML/CUDA/CoreML packages, verify platform/architecture availability, native library size, dependencies, license/notices, driver/runtime constraints, fallback behavior and packaged Python versus Node binding compatibility.

## FFmpeg

Atlas video validation/proxy generation depends on FFmpeg/FFprobe behavior. Distribution must review exact build source/configuration, codec libraries, LGPL/GPL implications, linking/packaging, notice/source obligations and whether the binary is bundled or system-discovered. Do not assume any arbitrary FFmpeg build is safe to redistribute.

## Fonts

Candidate CJK fonts require exact checks for redistribution, modification/subsetting, desktop bundling, PDF embedding and attribution. Templates must provide deterministic fallback chains and PDF preflight warnings.

## Apache-2.0 app license

- Canonical text: `https://www.apache.org/licenses/LICENSE-2.0`
- App copy: `app/LICENSE`
- App notice: `app/NOTICE`
- Project policy: `docs/app/LICENSING_AND_DISTRIBUTION_POLICY.md`

Apache-2.0 covers only app-authored work that this repository has authority to license. It does not automatically cover models, datasets, generated media, user files, trademarks or separately licensed assets.

## Sample corpus data license

Target public data license is CC BY 4.0 only when sufficient rights have been verified:

- `https://creativecommons.org/licenses/by/4.0/`

Every corpus part still needs an explicit manifest. If provider/user rights do not support CC BY 4.0, withhold the asset or use a reviewed explicit alternative. Unknown rights default to no redistribution.

## Required artifact-level review checklist

For every bundled/downloadable model, binary, font, icon pack or corpus:

1. stable identifier;
2. source URL/repository/release;
3. exact version/tag/commit;
4. filename;
5. byte size;
6. SHA-256;
7. author/publisher;
8. source-code license when applicable;
9. artifact/data/weight license or terms;
10. redistribution mode (`bundled`, `download`, `user-supplied`, `blocked`);
11. required notices/attribution;
12. patent/trademark concerns where relevant;
13. conversion/build provenance;
14. security scan result;
15. review date/reviewer;
16. re-review trigger;
17. takedown/correction contact/process.

## Review freshness

Dependencies, official guidance, API terms and packaging support may change. Every stable release must regenerate its SBOM/notices and re-check current primary documentation. These references describe the specification baseline, not permanent guarantees.
