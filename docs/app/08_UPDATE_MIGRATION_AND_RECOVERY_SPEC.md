# 08 — Update, Migration and Recovery Specification

## 1. Scope

This document defines how users move from one app version to another without manually re-creating settings, paths, projects, credentials, models, job state or report drafts.

The product must support:

- online update discovery and installation where the platform/package supports it;
- user-imported offline update packages/files;
- platform-specific installer handoff;
- pre-update compatibility checks;
- automatic schema migrations;
- backup, verification and recovery;
- clear handling of unsupported downgrade.

## 2. Principles

### U-001 — User data is outside replaceable app binaries

Projects, settings, credentials, models and caches live in stable user/project locations, never inside the application installation directory.

### U-002 — Update and migration are separate

Installing new binaries does not itself prove user data is compatible. First launch runs explicit migrations and records evidence.

### U-003 — Backup before irreversible change

Any migration that writes persistent user data requires a pre-migration backup or a transactional strategy that provides equivalent restoration.

### U-004 — No silent incompatible package

The app validates platform, architecture, version, channel, signature/checksum and minimum/current schema compatibility before installer handoff.

### U-005 — Failed migration enters recovery mode

The app must not repeatedly launch into the same destructive failure loop.

### U-006 — Linux is not assumed to have built-in self-update

Linux packages differ. The design includes AppImage/manual package flows and does not promise the same mechanism as signed Windows/macOS auto-update.

## 3. Update channels

- `stable`: production releases.
- `beta`: prereleases with migration compatibility expectations.
- `nightly`: optional development builds; may require separate data directory by default.

Rules:

- stable users do not receive beta/nightly automatically;
- changing to a less stable channel requires confirmation;
- channel metadata is signed/verified;
- project schema compatibility remains explicit across channels;
- nightly may refuse to open stable projects read-write unless backup/clone is created.

## 4. Version identities

Track separately:

- app semantic version;
- Electron/runtime version;
- local engine version;
- global settings schema version;
- project manifest schema version;
- project database schema version;
- config schema versions;
- credential record schema;
- model registry schema;
- Atlas/detection/document output schemas;
- IPC bridge version.

An update manifest declares source/target compatibility for each.

## 5. Update manifest

Required fields:

```json
{
  "schemaVersion": 1,
  "appVersion": "1.2.3",
  "channel": "stable",
  "releaseTag": "desktop-v1.2.3",
  "publishedAt": "ISO-8601",
  "minimumSupportedAppVersion": "1.0.0",
  "minimumProjectSchema": 1,
  "targetSchemas": {},
  "packages": [],
  "releaseNotes": {},
  "migrationSummary": [],
  "knownIssues": [],
  "signature": {}
}
```

Each package entry includes:

- platform;
- architecture;
- package type;
- filename;
- URL;
- byte size;
- SHA-256;
- signing/notarization status;
- required free space;
- install strategy;
- whether in-app handoff is supported.

## 6. Online update flow

1. App checks update metadata according to user policy.
2. Renderer receives only sanitized update summary.
3. User sees version, size, release notes, migration impact and restart requirement.
4. App downloads in backend with resume where supported.
5. Package and metadata are verified.
6. App performs preflight and creates backup plan.
7. User selects install now or later.
8. Running jobs are handled according to safe-shutdown policy.
9. Platform installer/updater executes.
10. New version launches into migration bootstrap.
11. Migration verification completes before normal workspace opens.
12. Backup retention is scheduled after successful use period.

Automatic background download is configurable. Automatic installation without user awareness is not the default.

## 7. Offline update import

### 7.1 Entry points

- Update Center → Import update package;
- drag-and-drop supported update file;
- command-line file association/protocol provisional;
- open downloaded installer outside app as fallback.

### 7.2 Accepted inputs

The app should recognize:

- update manifest plus package directory;
- signed platform installer/package;
- maintainer-created update bundle containing manifest and package;
- platform-native file selected directly.

Direct installer import without manifest may be allowed only when signature/version metadata can be verified from the package and the user accepts reduced preflight detail.

### 7.3 Validation

Before enabling install:

- file exists and is readable;
- platform matches;
- architecture matches or package is universal;
- version is newer unless expert reinstall is selected;
- channel policy permits it;
- signature/notarization/checksum is valid;
- package type is supported by current install type;
- disk space is sufficient;
- no known migration gap from current version;
- package is not a model/sample/project archive misidentified by extension.

### 7.4 UX

A review card shows:

- current → target version;
- source file;
- verified publisher/signature;
- platform/package type;
- download/import hash;
- required restart;
- backup location;
- migration list;
- incompatible or deferred jobs;
- primary install action with `color="primary"` and update icon.

Invalid packages show precise reasons and cannot be forced through ordinary mode.

## 8. Platform-specific behavior

### 8.1 Windows

Supported package strategy to be finalized between Squirrel/NSIS/MSIX/other packaging choice.

Requirements regardless of packager:

- signed installer for stable channel target;
- package architecture validation;
- install path may differ from user data path;
- running app exits cleanly before replacement;
- restart after update supported;
- per-user install preferred unless system-wide requirements justify elevation;
- portable build, if shipped, uses a distinct update strategy and cannot pretend to be installed build;
- installer logs captured/referenced for failure recovery;
- Windows file locks handled before engine/app replacement.

Offline flow may launch the verified installer and exit. The app should not manually overwrite its own executable.

### 8.2 macOS

Requirements:

- stable app signed and notarized;
- architecture: arm64 required; x64 provisional; universal package possible after size/build review;
- app bundle replacement uses supported updater/installer behavior;
- DMG alone is primarily distribution; automatic update may require compatible archive/feed format;
- Keychain credential access after update is verified under the same application identity;
- quarantine/Gatekeeper status handled;
- update package signature validated;
- migration begins after updated app successfully launches.

User may be instructed to drag a new app bundle only as fallback; the product goal is guided verification and preserved data, not manual settings transfer.

### 8.3 Linux

Initial packages:

- AppImage required target;
- `.deb` provisional.

Because update behavior depends on distribution/package:

- AppImage may support download-and-replace or external AppImage updater only after validation;
- `.deb` update normally hands off to package manager/installer and may require elevation;
- built-in Electron auto-update is not assumed;
- app always provides verified download and “reveal package / open install instructions” fallback;
- user data path remains independent;
- Secret Service availability is rechecked after update;
- executable permissions and mount behavior are validated.

### 8.4 Package-type migration

Moving from portable to installed, AppImage to `.deb`, or x64 to arm64 is a migration, not a routine patch. The app provides:

- export/backup;
- new installation instructions;
- user-data detection/import;
- duplicate installation warning;
- explicit credential availability check;
- old install cleanup guidance only after successful new launch.

## 9. Running jobs during update

Before install:

- short foreground operations complete or cancel;
- API jobs pause after safe request boundary;
- asynchronous provider submissions are checkpointed for later polling;
- Atlas/detection workers stop scheduling and flush checkpoints;
- downloads pause with range metadata;
- PDF export should complete or cancel; partial final PDF is not considered valid;
- project DB transactions finish;
- app records update shutdown reason.

The user sees which jobs will resume. Force update remains expert-only and records risk.

## 10. Migration framework

### 10.1 Migration identity

Every migration has:

- stable ID;
- from/to schema range;
- app version introduced;
- data scope;
- estimated cost;
- free-space requirement;
- reversible flag;
- backup requirement;
- implementation checksum/version;
- progress units;
- validation function.

### 10.2 Migration ordering

1. global settings;
2. credential metadata/encrypted payload migration;
3. model registry/cache metadata;
4. known project registry;
5. each opened project manifest/DB;
6. configs;
7. report drafts;
8. derived result indexes where required.

Projects not opened immediately may migrate lazily on first open, but the app shows pending migration state.

### 10.3 Transactional behavior

Preferred:

- SQLite transaction for DB-only migration;
- write-new-then-atomic-swap for files;
- staged directory for multi-file transformations;
- migration journal updated after each durable step;
- validation before deleting/replacing old form.

For large migrations that cannot fit one transaction:

- resumable checkpoints;
- source remains untouched until final cutover where possible;
- explicit rollback path;
- progress and disk estimates.

## 11. Backup strategy

### 11.1 Global backup

Contains:

- settings DB/config;
- project registry;
- credential encrypted records/metadata;
- update channel and model registry metadata;
- migration journal.

It does not need to duplicate large model binaries or regenerable caches by default.

### 11.2 Project backup

Profiles:

- schema backup: manifest + DB + configs + report drafts;
- full managed-data backup: optional and potentially large;
- external-media project: records bindings/hashes, not external file copy by default.

### 11.3 Backup naming

```text
backups/<scope>/<id>/<timestamp>-before-<target-version>/
```

Manifest records contents/hashes and restore compatibility.

### 11.4 Retention

Default provisional:

- keep latest three successful pre-update backups;
- keep failed-migration backup until user resolves/deletes;
- warn before cleanup;
- respect disk threshold;
- allow user-selected backup root.

## 12. Credential migration

Credentials require special handling because OS-backed encryption may depend on application identity/user context.

Requirements:

- same signed app identity across updates;
- decrypt-and-reencrypt only in main process;
- migration never exports plaintext to disk;
- each profile validation result recorded;
- if async safe-storage API indicates re-encryption/key rotation, update atomically;
- temporary provider unavailability does not cause secret deletion;
- failed credential migration leaves original encrypted record and offers recovery;
- changing package/app identity must have explicit credential transfer plan.

## 13. Project compatibility

### 13.1 Opening newer project in older app

Default: read-only compatibility screen or refusal with exportable diagnostics. Older app must not guess-write newer schema.

### 13.2 Opening old project in new app

- preview migration impact;
- create backup;
- migrate;
- validate counts/hashes/configs/jobs;
- record history in project manifest/DB;
- show completion summary.

### 13.3 Downgrade

Downgrade is not implicitly supported. Options:

- restore pre-update backup using older app;
- export to an explicitly supported backward-compatible package;
- open read-only;
- clone project before experimental upgrade.

The app must never silently downgrade schemas.

## 14. Recovery mode

Triggered by:

- failed global migration;
- repeated startup crash after update;
- missing/corrupt settings DB;
- incompatible engine/app versions;
- credential storage unavailable;
- project migration failure;
- incomplete installer handoff record.

Recovery Center offers:

- view failure summary;
- retry migration;
- restore backup;
- open project read-only;
- select alternate project;
- export support bundle;
- reveal logs/backups;
- reset only UI settings;
- start with workers/providers disabled;
- roll back binaries through platform instructions/package when available.

Resetting the app must not delete projects by default.

## 15. Update rollback

### 15.1 Binary rollback

Depends on platform/packager. Stable policy requires either:

- updater-supported rollback; or
- retained previous installer/package with guided reinstall; or
- manual download link plus compatible backup restore.

### 15.2 Data rollback

- restore global/project backup only after current state is preserved or user explicitly discards it;
- credential restore verifies decryptability;
- restored project lock/migration journals reset safely;
- post-restore integrity check required;
- report exact restored version/schema.

### 15.3 Failed first launch

A bootstrap marker distinguishes:

- installer success;
- app process launch;
- migration start;
- migration success;
- first workspace render.

Repeated failure before success prompts recovery rather than automatic migration loop.

## 16. Update Center UI

Sections:

- current version/channel;
- available update;
- downloaded update;
- import offline package;
- release notes;
- migration impact;
- backup status;
- update history;
- recovery/rollback;
- platform install guidance.

States use meaningful icons/colors and transitions. Update cards use `v-hover`. Long notes use headings/tabs rather than one dialog wall.

## 17. Update history record

Store:

- from/to version;
- channel;
- package identity/hash/signature;
- source online/offline;
- download/import time;
- install handoff time;
- migration IDs/results/durations;
- backup IDs;
- completion/failure;
- diagnostics ID;
- rollback/restore actions.

No secret values are included.

## 18. Security

- update metadata/package requires trusted transport and signature/checksum verification;
- renderer cannot choose executable path to launch arbitrarily;
- offline import validates format and publisher;
- no shell interpolation;
- installer handoff allowlists package types;
- update feed cannot deliver arbitrary engine/plugin code outside signed app package policy;
- release notes rendered as sanitized Markdown;
- backups containing encrypted secrets use restricted permissions;
- recovery support bundle redacts paths/secrets.

## 19. Testing matrix

For every supported platform/package:

- clean install;
- update from previous stable;
- update with projects/settings/credentials/models;
- update with paused/running jobs;
- offline package import;
- wrong architecture;
- corrupt package;
- wrong checksum/signature;
- insufficient disk;
- migration failure injection;
- crash during migration;
- restore backup;
- newer-project/older-app handling;
- package-type migration where supported;
- credential decrypt/re-encrypt;
- first launch recovery.

## 20. Acceptance criteria

- user never needs to manually re-enter ordinary settings after a supported update;
- project paths/configs/reports remain linked;
- credentials remain usable or a specific recoverable error is shown;
- running jobs pause/checkpoint and resume;
- incompatible offline package is blocked before execution;
- pre-migration backup is created and verified;
- migration history is durable;
- failed migration enters Recovery Center;
- restore does not delete current data without confirmation;
- Linux UI does not falsely promise Windows/macOS-style built-in updater behavior;
- stable Releases document package-specific update instructions;
- update success is not claimed until migration and workspace verification complete.