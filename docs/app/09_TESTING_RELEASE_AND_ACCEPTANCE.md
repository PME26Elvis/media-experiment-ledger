# 09 — Testing, Release Validation and Acceptance Specification

## 1. Scope

This document defines how the desktop product proves correctness. Passing a UI build or unit test is not proof that installers, model downloads, long-running jobs, PDFs, updates or migrations work in production.

Each milestone must have executable acceptance evidence. The project should prefer real lightweight fixtures over mocks for media decoding, model inference, filesystem behavior and updates where practical.

## 2. Quality goals

- Prevent data loss and source-media mutation.
- Keep renderer/main processes responsive.
- Verify IPC and secret boundaries.
- Verify durable pause/resume/crash recovery.
- Verify real image/video decoding.
- Verify real ONNX execution for supported models.
- Verify large-corpus behavior.
- Verify PDF output and document migration.
- Verify platform packages install, launch and update.
- Verify Release assets and manifests after upload.
- Make regressions reproducible with deterministic fixtures.

## 3. Test pyramid

### 3.1 Static checks

- TypeScript strict type check.
- Vue SFC type check.
- ESLint with Vue/Composition API/security rules.
- Prettier/format validation.
- JSON/YAML/TOML schema validation.
- machine product contract validation.
- dependency/license notice validation.
- forbidden renderer imports and Electron security lint.
- IPC channel/schema synchronization.
- migration graph consistency.
- model registry hash/license completeness.

### 3.2 Unit tests

Domains:

- path canonicalization;
- archive safety;
- config parsing/migration;
- retry/backoff/stop policies;
- circuit breaker;
- job state machine;
- checkpoint compatibility;
- cohort identity and temporal selection;
- exact deduplication;
- detector preprocessing/postprocessing/NMS;
- comparison matching;
- thumbnail proxy selection by display pixels;
- cache eviction;
- update package compatibility;
- migration ordering;
- secret redaction;
- document command/undo model;
- template/style resolution;
- PDF preflight rules.

### 3.3 Component tests

Vue/Vuetify components:

- responsive breakpoints;
- hover/focus/touch equivalence;
- reduced motion;
- loading/empty/error/partial/completed states;
- form validation;
- path browse/reveal actions through mocked typed bridge;
- secret masking;
- config import preview;
- job progress aggregation;
- virtualized selection;
- model card license states;
- Atlas document editor controls;
- update package review.

Snapshots alone are insufficient; tests must assert behavior and accessibility.

### 3.4 IPC contract tests

- every preload method has schema and authorization;
- unknown channel impossible from renderer API;
- invalid payload rejected;
- oversized payload rejected;
- renderer cannot request arbitrary file/process;
- event unsubscribe works;
- main errors map to stable safe envelope;
- API version mismatch produces explicit compatibility state;
- path grants are project-scoped;
- secret methods never return plaintext metadata accidentally.

### 3.5 Engine integration tests

Real engine process with structured protocol:

- launch/handshake/version;
- heartbeat;
- malformed/oversized message;
- worker crash isolation;
- cancellation;
- pause/checkpoint;
- output path restrictions;
- image decode;
- synthetic FFmpeg video validation;
- thumbnail/contact-sheet generation;
- Atlas rendering;
- real supported-model ONNX smoke;
- PDF asset rendering;
- engine upgrade compatibility.

### 3.6 App end-to-end tests

Through packaged or production-like Electron:

- first launch;
- create/open/rename project;
- import files/folder/drag-drop;
- sample corpus import;
- config import/export/reveal folder;
- credential profile workflow with test vault;
- automation dry-run/fixture provider;
- Atlas analysis and document PDF;
- detection job and resume;
- Job Center recovery;
- offline update import;
- migration/recovery mode;
- keyboard navigation and themes.

## 4. Real media fixtures

### 4.1 Images

Generate or version small fixtures covering:

- JPEG/PNG/WebP;
- alpha;
- EXIF orientation;
- color profile;
- very wide/tall;
- high resolution;
- truncated/corrupt;
- duplicate bytes;
- same visual/different bytes;
- unsupported extension/content mismatch.

### 4.2 Videos

Generate deterministic short clips during tests with FFmpeg:

- MP4/H.264 where legally/technically available;
- WebM;
- different duration/aspect/frame rate;
- short clip needing final-frame freeze;
- missing video stream;
- corrupt/truncated;
- duplicate bytes;
- decode failure near end.

Tests must invoke real FFprobe/FFmpeg for critical paths.

## 5. Model fixtures

### 5.1 Baseline model smoke

For every supported model/platform:

- download or locate immutable artifact;
- verify expected size/SHA-256;
- create real ONNX Runtime session;
- validate input/output names/shapes;
- run inference on deterministic test image;
- decode normalized boxes;
- compare to tolerance-based golden output;
- test zero-detection/high-detection cases;
- verify labels hash.

### 5.2 Larger model gating

A candidate model cannot become stable-supported until:

- artifact license status is accepted;
- runtime smoke passes all target platforms/providers;
- resource metadata exists;
- postprocessing golden tests pass;
- checkpoint/output schema compatibility is defined;
- package/download workflow validates hash.

## 6. Atlas tests

- metadata normalization;
- image/video separation;
- seed policy;
- duplicate removal with aliases retained;
- 2/3/4+ layout rules;
- latest sample included;
- extended temporal quantiles;
- all samples on full pages;
- contain/letterbox, no default crop;
- invalid media reporting;
- job restart after each stage;
- analysis fingerprint changes with policy;
- immutable snapshot behavior;
- document references snapshot safely;
- rich text formatting and IME;
- undo/redo/autosave/recovery;
- template switching;
- video static PDF representation;
- page break/preflight;
- PDF manifest/hash.

Visual golden tests use controlled fonts and rendering environment. Cross-platform differences require perceptual thresholds, not fragile byte-only image comparison.

## 7. Detection tests

- model registry parsing;
- license/distribution state;
- download resume/hash rejection;
- preprocessing for each adapter;
- coordinate recovery;
- class-aware NMS;
- finite/bounded outputs;
- item checkpoint transaction;
- pause/resume;
- worker crash and valid-output promotion;
- config/model/input invalidation;
- OOM fallback policy with simulated provider;
- two-model exact identity pairing;
- deterministic matching;
- allowed comparison language;
- 10,000-item virtualized result browser;
- partial export.

## 8. API Automation tests

### 8.1 Fixture provider

A local deterministic provider simulator supports:

- synchronous image success;
- asynchronous video success;
- polling;
- Retry-After;
- 401/402/429/5xx;
- timeout/disconnect;
- duplicate/ambiguous submission;
- expired URL;
- corrupt media output;
- large streaming download.

### 8.2 Required scenarios

- config import from current Agnes YAML/JSONL;
- multiple credentials without secret leakage;
- interval/concurrency calculation;
- exponential backoff/jitter with deterministic clock;
- stop current phase versus whole run;
- circuit breaker;
- pause during wait/poll/download;
- restart with submitted video;
- provider success but archive failure;
- disk low pause;
- raw response retention/redaction;
- 10,000 task UI/database behavior.

Live Agnes tests are manual/secured smoke tests and must not run on untrusted PRs or expose credentials.

## 9. Filesystem and project tests

Run on platform-specific filesystems where possible:

- Unicode and Traditional Chinese paths;
- spaces and long paths;
- case differences;
- Windows reserved names;
- symlink/junction traversal;
- external drive removal;
- read-only folder;
- insufficient permissions;
- project moved/renamed;
- stale lock/takeover;
- concurrent writer rejection;
- network/cloud-synced folder warning;
- atomic replacement interruption;
- archive zip-slip/compression bomb.

## 10. Secrets tests

- safeStorage available/unavailable;
- Windows DPAPI user boundary fixture where feasible;
- macOS signed identity/Keychain integration in release validation;
- Linux Secret Service available/unavailable;
- async encryption rotation/re-encrypt indicator;
- `.env` import;
- secret-bearing export warning;
- no secret in Pinia/localStorage/log/support bundle/CLI args;
- clipboard timeout;
- credential migration failure recovery;
- multiple credential profiles.

## 11. Performance benchmarks

### 11.1 Reference scenarios

- open indexed 10,000-image project;
- first-time index/hash/proxy;
- scroll/filter/select gallery;
- 1,000-video poster extraction;
- two-model 10,000-image inference;
- browse million-box result fixture;
- 2,000-cohort Atlas;
- edit 500-page report;
- export large PDF;
- import/export multipart project/sample corpus;
- app restart during each.

### 11.2 Metrics

- renderer long tasks;
- frame/scroll smoothness;
- memory high-water by process;
- startup/project-open time;
- DB query latency p50/p95/p99;
- thumbnail latency/cache hit;
- worker queue depth;
- throughput;
- checkpoint overhead;
- recovery time;
- PDF page time/peak memory;
- disk amplification.

### 11.3 Regression policy

Baseline results are stored by platform/reference hardware. Material regressions require approval or mitigation. Benchmarks must distinguish cold/warm cache and SSD/HDD.

## 12. Accessibility and visual regression

Test:

- keyboard-only canonical journeys;
- screen-reader landmarks/names;
- focus order;
- color contrast;
- color-independent state;
- 200% text scale;
- Traditional Chinese and English overflow;
- light/dark/system themes;
- reduced motion;
- narrow/wide breakpoints;
- touch-equivalent actions;
- hover not being sole access.

Visual snapshots at multiple breakpoints use stable fixture data.

## 13. Migration tests

For every migration:

- previous-version fixture;
- success path;
- idempotent rerun or explicit non-rerunnable guard;
- interruption before/after each durable step;
- insufficient disk;
- corrupt input;
- backup verification;
- restore;
- unknown/newer schema refusal;
- counts/hashes/config equivalence;
- credentials remain encrypted;
- large project progress.

The test suite maintains fixtures from every supported upgrade floor, not only previous patch.

## 14. Packaging matrix

### Required initial targets

- Windows x64 installer.
- macOS arm64 signed/notarized target.
- Linux x64 AppImage.

### Provisional targets

- Windows portable.
- macOS x64 or universal.
- Linux `.deb`.

For each package:

- clean VM install;
- launch;
- app resources/engine/FFmpeg discovery;
- create/import project;
- baseline Atlas/model smoke;
- path/dialog integration;
- uninstall behavior does not remove projects by default;
- upgrade from previous Release;
- offline update/package handoff;
- signature/notarization verification.

## 15. CI workflow layers

### PR validation

- contracts/static/type/lint;
- unit/component;
- engine integration with small media;
- baseline ONNX smoke;
- renderer production build;
- Electron security assertions;
- package smoke on matrix where cost permits.

### Nightly/extended

- large generated corpus benchmarks;
- full platform package tests;
- multiple model variants;
- migration matrix;
- long-duration pause/resume;
- memory/leak tests;
- accessibility/visual suite.

### Release candidate

- exact release commit;
- all required platforms;
- signing/notarization;
- install/update tests;
- sample corpus validation;
- SBOM/licenses;
- checksums/manifests;
- GitHub draft asset verification;
- final publication gate.

## 16. GitHub Release verification

After upload, verify through GitHub API:

- expected asset names/count;
- byte sizes;
- no zero-byte/partial assets;
- checksums correspond to local build artifacts;
- app manifest references exact assets;
- sample corpus parts/manifest complete;
- only allowed prerelease/draft state;
- notes contain platform table/migration instructions;
- tag/commit correct;
- no secret-bearing artifacts/logs;
- final Release is immutable by policy after publication except managed notes correction with audit.

## 17. Acceptance evidence

Every milestone PR/release records:

- commit SHA;
- workflow runs;
- test suites and counts;
- platform/package results;
- benchmark summary;
- known limitations;
- screenshots/visual review where UI changes;
- model/hash/runtime evidence where relevant;
- migration/update evidence;
- Release asset audit for publication milestones.

## 18. Definition of done

A feature is done only when:

- behavior matches specification;
- data schema/version exists;
- loading/empty/error/recovery states exist;
- RWD/light/dark/reduced-motion behavior exists;
- unit/component/integration/E2E tests appropriate to risk pass;
- docs/config/help are synchronized;
- large-corpus impact is measured;
- security/privacy review passes;
- migration impact is handled;
- actual packaged behavior is verified when platform integration is involved.

A green unit test alone never proves a production installer, Release, update, PDF or model works.