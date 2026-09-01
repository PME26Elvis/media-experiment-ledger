# 03 — Data, Project, Import/Export and Release Specification

## 1. Scope

This document defines how the desktop app represents projects, input/output paths, imported media, configurations, derived results, sample corpora, app packages and GitHub Releases.

The app must support users who prefer GUI-managed files and users who want to inspect or edit configuration files directly. It must therefore make paths discoverable and formats documented without exposing internal databases as the only interface.

## 2. Project concept

A project is the durable unit that groups:

- image and video inputs;
- generated-media outputs;
- API automation runs;
- Atlas jobs/results/report drafts;
- detection jobs/results;
- model/config references;
- thumbnails/proxies/caches;
- report exports;
- project-scoped settings;
- audit and migration history.

A project may be self-contained or reference external media folders.

## 3. Project directory structure

Provisional managed project layout:

```text
<ProjectName>.mel-project/
├─ project.json
├─ project.db
├─ configs/
│  ├─ automation/
│  ├─ atlas/
│  ├─ detection/
│  └─ report-templates/
├─ media/
│  ├─ images/                 # copied/managed image inputs, optional
│  ├─ videos/                 # copied/managed video inputs, optional
│  └─ generated/
│     ├─ images/
│     └─ videos/
├─ derived/
│  ├─ thumbnails/
│  ├─ proxies/
│  ├─ atlas/
│  ├─ detection/
│  └─ reports/
├─ jobs/
│  └─ <job-id>/
├─ logs/
├─ migrations/
├─ exports/
└─ .locks/
```

The layout is user-visible but not every internal file is intended for manual editing. `project.json` and files under `configs/` are documented interoperability surfaces. `project.db` is app-managed.

## 4. `project.json` manifest

Required fields:

```json
{
  "schemaVersion": 1,
  "projectId": "uuid",
  "name": "My Media Study",
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601",
  "appVersionCreated": "semver",
  "appVersionLastOpened": "semver",
  "databaseSchemaVersion": 1,
  "defaultLocale": "zh-TW",
  "storageMode": "hybrid",
  "pathBindings": [],
  "featureFlags": {},
  "migrationHistory": []
}
```

Rules:

- unknown fields are preserved when safely possible;
- required fields are validated before write access;
- project ID never changes during ordinary rename or move;
- name is user-facing and may differ from directory name;
- app version and schema versions are distinct;
- secrets are never embedded;
- manifest writes are atomic: write temp, fsync where possible, replace;
- a backup of the last valid manifest is retained.

## 5. Path model

### 5.1 Independent path categories

The following paths are independent and configurable:

- image input;
- video input;
- generated image output;
- generated video output;
- Atlas derived output;
- detection derived output;
- report export output;
- temporary/cache root;
- model storage root;
- config root when external configs are enabled.

Changing one must not silently change the others.

### 5.2 Defaults

For a managed project:

- image input defaults to `media/images/`;
- video input defaults to `media/videos/`;
- generated outputs default under `media/generated/`;
- Atlas output defaults to `derived/atlas/`;
- detection output defaults to `derived/detection/`;
- reports default to `derived/reports/` and user-selected export destination;
- caches default under `derived/thumbnails/` and `derived/proxies/`.

Global model storage belongs under the app user-data directory by default, not duplicated into every project.

### 5.3 Path binding modes

Each binding has one mode:

- `managed-relative`: copied inside project and referenced relatively;
- `external-absolute`: referenced in place;
- `external-relocatable`: stores absolute path plus a relocation signature;
- `read-only-release-cache`: imported from a verified sample/experiment archive;
- `temporary`: disposable and excluded from project export.

### 5.4 Relinking missing paths

When an external path is unavailable:

- project opens with degraded status, not fatal failure;
- missing binding shows expected path, media count and optional fingerprint;
- user may locate replacement folder;
- app previews match quality before accepting;
- matching uses relative filenames, sizes, hashes where available and directory fingerprint;
- existing analysis results remain visible but are marked source-unavailable when necessary.

## 6. File and folder browser UX requirements

Every path field includes:

- path text display;
- browse button;
- reveal/open containing folder button;
- validation/status icon;
- storage/free-space summary when relevant;
- reset-to-default action;
- recent locations where platform privacy permits;
- clear indication of managed versus external path.

The user can type/paste a path in expert mode, but it is validated through the main process.

## 7. Drag-and-drop import

Supported drops:

- individual image files;
- individual video files;
- multiple mixed files;
- directories;
- app project package;
- supported config file;
- sample corpus part/manifest;
- supported model artifact only through Model Manager validation.

When an individual media file is dropped, the app offers:

1. import only selected file(s);
2. scan the containing directory;
3. bind the containing directory as an input path.

The app must never scan the whole containing directory without user confirmation.

Import preview displays:

- detected type;
- count and total size;
- supported/unsupported count;
- duplicate count if quickly knowable;
- copy/reference choice;
- destination;
- potential conflicts;
- estimated indexing work.

## 8. Media identity and deduplication

Each indexed asset has:

- stable asset UUID;
- media type;
- source binding ID;
- relative/source path;
- byte size;
- modified time as non-authoritative hint;
- SHA-256 after full verification;
- fast fingerprint before full hash, optional;
- dimensions;
- format/container;
- image orientation/color metadata;
- video duration/codec/frame-rate metadata;
- decode validation status;
- prompt/provider/run associations when known.

Byte-identical assets may share derived thumbnails/inference cache within one project, but all aliases remain visible. Deduplication must not silently delete user files.

## 9. Supported media formats

The front end must display the actual supported format list derived from engine capabilities.

Initial target image imports:

- JPEG/JPG;
- PNG;
- WebP;
- GIF, treated as image or animated media according to module;
- TIFF provisional;
- BMP provisional.

Initial target video imports depend on bundled FFmpeg support, with expected containers:

- MP4;
- WebM;
- MOV;
- MKV provisional;
- AVI provisional.

“File extension supported” does not guarantee codec support; decode validation determines usability.

## 10. Configuration files

### 10.1 Canonical user-editable format

YAML is the canonical human-editable format because it supports comments and readable nested policies. JSON is the canonical machine-interchange export.

Supported import extensions:

- `.yaml`;
- `.yml`;
- `.json`;
- `.toml`.

Supported export extensions in v1:

- `.yaml`;
- `.json`.

TOML export is deferred until nested configuration behavior and comments are defined.

### 10.2 Config envelope

Every config contains:

```yaml
kind: automation | atlas | detection | report-template
schemaVersion: 1
name: Human readable name
createdByAppVersion: 0.1.0
updatedAt: 2026-07-22T00:00:00Z
providerOrEngine: optional-id
settings: {}
secretRefs: []
```

### 10.3 Import behavior

1. Parse without applying.
2. Validate schema and unknown fields.
3. Migrate older schema in memory.
4. Display a change preview against current/default config.
5. Resolve secret references separately.
6. Resolve path bindings separately.
7. Let user save as a new preset or replace current config.
8. Preserve comments where parser support makes this reliable; otherwise warn before round-trip rewrite.

### 10.4 Export behavior

- secret values excluded by default;
- path export mode selectable: absolute, project-relative, placeholder variables;
- include schema/version metadata;
- optionally include comments/help text in YAML;
- atomic destination write;
- reveal exported file action;
- deterministic JSON ordering for diffability.

## 11. Project package import/export

### 11.1 Package extension

Provisional extension: `.melproj` as a ZIP container with a strict manifest.

### 11.2 Export profiles

- **Metadata only**: manifests, configs, DB snapshot, report drafts; no source media.
- **Portable project**: copied media, derived results and required assets; excludes regenerable caches by default.
- **Analysis evidence**: selected input hashes, configs, model identities, results and reports.
- **Support package**: sanitized diagnostics, no media/secrets by default.

### 11.3 Security

- reject absolute archive member paths;
- reject `..` traversal;
- limit total uncompressed size and compression ratio;
- verify manifest member sizes/hashes;
- extract to staging directory;
- validate before move into final location;
- imported project cannot execute code;
- imported HTML is sanitized or opened in isolated viewer.

## 12. Sample corpus product

### 12.1 Purpose

Every user should be able to experience the app without an API key or their own corpus. Releases therefore provide one or more curated sample-corpus assets derived from appropriately reviewed existing repository data.

### 12.2 Product name and naming

Product-facing name: **Media Experiment Ledger Sample Corpus**.

Asset prefix: `mel-sample-corpus`.

Examples:

```text
mel-sample-corpus-manifest-v1.json
mel-sample-corpus-images-v1-part001.zip
mel-sample-corpus-images-v1-part002.zip
mel-sample-corpus-videos-v1-part001.zip
mel-sample-corpus-checksums-v1.txt
```

Rules:

- version refers to sample-corpus composition/schema, not app version;
- media types are split;
- parts use zero-padded three-digit numbering;
- no single part should exceed 1.9 GB, leaving margin below 2 GB transport/consumer constraints;
- part membership is deterministic;
- manifest records every part, byte size, SHA-256, media count and uncompressed size;
- app supports downloading only image, only video or complete sample set;
- app supports resuming individual part downloads;
- app verifies each part before extraction.

### 12.3 Sample manifest

Required fields:

- corpus ID/version;
- display name and description;
- source provenance;
- review/approval timestamp;
- data license/usage notice;
- prompt/metadata privacy review status;
- media counts;
- logical categories;
- total compressed/uncompressed bytes;
- part list with URL/name/hash/size/type;
- minimum app version;
- schema version;
- import defaults;
- expected Atlas/detection demo presets.

### 12.4 Raw data review gate

Existing personal/raw inputs must not automatically become sample assets. Before publication, review:

- whether prompts contain personal or sensitive content;
- provider response metadata;
- URLs/tokens/query strings;
- usernames/local paths;
- embedded EXIF/location metadata;
- third-party copyrighted or private source material;
- model/provider redistribution terms;
- whether video frames contain sensitive content.

A machine-readable sample publication audit must be stored with the Release build evidence.

### 12.5 Release placement

Default: include sample-corpus parts in the same GitHub Release as an app version when total size and build cadence remain manageable.

Allowed alternative: dedicated immutable sample-corpus Release when:

- corpus version changes independently;
- total size makes app Release navigation unwieldy;
- retrying app packaging should not re-upload corpus parts;
- platform packages plus corpus exceed practical workflow limits.

The app manifest, not hard-coded tag assumptions, determines download URLs.

## 13. Desktop app asset naming

Provisional product slug: `media-experiment-ledger-desktop`.

Expected assets:

```text
media-experiment-ledger-desktop-<version>-windows-x64-setup.exe
media-experiment-ledger-desktop-<version>-windows-x64-portable.zip   # provisional
media-experiment-ledger-desktop-<version>-macos-arm64.dmg
media-experiment-ledger-desktop-<version>-macos-x64.dmg              # provisional
media-experiment-ledger-desktop-<version>-linux-x64.AppImage
media-experiment-ledger-desktop-<version>-linux-x64.deb              # provisional
media-experiment-ledger-desktop-<version>-checksums.txt
media-experiment-ledger-desktop-<version>-manifest.json
media-experiment-ledger-desktop-<version>-sbom.spdx.json
```

Platform-native auxiliary metadata may also be required for online update feeds.

## 14. GitHub Release workflow

### 14.1 Trigger

Manual `workflow_dispatch` is mandatory. Optional push/tag automation may be added later but must not remove manual control.

### 14.2 Inputs

Required/provisional inputs:

- `version`: semver or controlled auto-bump mode;
- `channel`: stable/beta/nightly;
- `release_title`: optional;
- `release_notes`: optional multiline Markdown;
- `feature_list`: optional comma/newline-delimited list converted to Markdown bullets;
- `prerelease`: boolean;
- `draft`: boolean;
- `build_windows`: boolean;
- `build_macos_arm64`: boolean;
- `build_macos_x64`: boolean;
- `build_linux`: boolean;
- `include_sample_images`: boolean;
- `include_sample_videos`: boolean;
- `sample_corpus_version`: optional;
- `sample_release_mode`: same-release/dedicated/existing-tag;
- `existing_sample_release_tag`: optional;
- `notes_footer`: optional;
- `signing_mode`: required/allow-unsigned-dev;
- `publish_after_validation`: boolean.

Input validation must reject inconsistent combinations before expensive builds.

### 14.3 Release notes generation

Generated notes include:

1. human-provided release notes;
2. feature bullets converted to Markdown;
3. platform/package table;
4. update/migration notes;
5. sample corpus table and sizes;
6. checksums/SBOM links;
7. known limitations;
8. install/update instructions per platform;
9. build provenance: commit, workflow run, app/engine schema versions.

Human-provided notes are preserved verbatim within a clearly bounded section.

### 14.4 Build and publication stages

1. validate version and branch;
2. install locked dependencies;
3. run unit/component/type/lint tests;
4. build engine binaries;
5. run engine smoke tests;
6. package per-platform app;
7. sign/notarize where configured;
8. test install/launch/update artifacts;
9. build or fetch sample corpus parts;
10. verify asset sizes and hashes;
11. generate manifest, checksums, SBOM and notices;
12. create draft Release;
13. upload with retry and post-upload size/hash verification;
14. generate final notes;
15. publish only after required jobs pass;
16. record machine-readable Release evidence.

### 14.5 Failure and recovery

- failed platform does not produce a misleading complete Release;
- draft remains recoverable;
- rerun can reuse verified immutable artifacts only when commit/version match;
- sample corpus parts are content-address verified;
- partial uploads are detected and replaced;
- release finalizer verifies GitHub-side asset size/count;
- no final tag is marked stable when required signatures are absent.

## 15. Retention and cleanup

- source inputs: user-controlled, never auto-deleted;
- copied project media: deleted only through explicit project cleanup;
- derived results: per-job retention controls;
- thumbnails/proxies: regenerable cache with LRU/size policy;
- temporary extraction: cleaned after verified import or retained for recovery on failure;
- failed job workspace: retained for configurable period;
- downloaded model artifacts: user-managed through Model Manager;
- downloaded sample archives: keep/delete-after-import option.

Cleanup previews bytes and consequences before execution.

## 16. Data integrity acceptance criteria

- importing the same corpus twice produces stable hashes and explicit aliases/duplicates;
- moving a managed project preserves relative bindings;
- missing external paths enter relink flow without corrupting results;
- config import never applies before preview/validation;
- config export excludes secrets by default;
- project export/import is traversal-safe and hash-verified;
- sample corpus can be downloaded in parts, resumed and independently verified;
- no app/sample asset exceeds the declared maximum without explicit multipart handling;
- Release manifest matches uploaded GitHub assets;
- projects remain readable after app update migrations;
- external source files are never modified by analysis.