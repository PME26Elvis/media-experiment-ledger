# 00 — Product Charter

## 1. Document purpose

This document defines what Media Experiment Ledger Desktop is, who it serves, which problems it solves, how it differs from the existing repository and which boundaries later specifications must preserve.

This is a normative product document. Feature specifications may add detail but must not quietly change the product identity described here.

## 2. Product vision

Media Experiment Ledger Desktop is a local-first desktop workbench for collecting, generating, organizing, analyzing, comparing and publishing AI-generated image and video corpora.

The app should let a user begin with either:

- their own image/video folders;
- an imported project;
- one or more curated sample-corpus ZIP assets downloaded from a GitHub Release;
- media generated through an optional supported API provider;
- media already published by this repository, imported through a controlled Release importer.

From that starting point, the user can run independent analysis products such as Prompt Repeatability Atlas and multi-model object detection, inspect results at scale, resume interrupted work, create polished reports and preserve enough provenance to reproduce or audit the result later.

The application is not only an offline viewer for precomputed repository output. It must be capable of executing meaningful local workflows on user-selected data.

## 3. Product positioning

### 3.1 What it is

- A desktop data workspace.
- A media-generation automation client when the user chooses to configure API credentials.
- A large-corpus asset browser.
- A job orchestration and recovery system.
- An Atlas analysis and document-authoring studio.
- A multi-model object-detection workbench.
- A report and evidence export tool.
- A reproducible project container with explicit schemas and migration history.

### 3.2 What it is not

- Not a browser shell around the current GitHub Pages site.
- Not a mandatory cloud service.
- Not a model-training platform in v1.
- Not a replacement for immutable `media-exp-*` Releases on `main`.
- Not a collaborative multi-user SaaS editor.
- Not a general-purpose photo editor.
- Not a promise that every model artifact can legally be redistributed inside app packages.
- Not an accuracy-benchmarking product unless the user imports human-verified ground-truth labels.

## 4. Core principles

### P-001 — Local-first by default

Projects, configuration, job state, media indexes and analysis results must remain usable without a network connection. Network access is required only for actions that inherently need it, such as API calls, model downloads, sample-corpus downloads, update checks or remote Release import.

### P-002 — API generation is optional

A user must be able to install the app, download or import sample data and run Atlas or object detection without providing any API key. API automation is an additional capability, not an onboarding gate.

### P-003 — Source media is immutable

The app must never rewrite the user's source image or video files during indexing, analysis, annotation, report authoring or export. Generated thumbnails, proxies, annotations and documents live in app-managed derived-data locations.

### P-004 — Every long-running operation is a durable job

Media generation, imports, checksum verification, thumbnail creation, Atlas processing, model download, detector inference, PDF export and project migration must have durable job identity, state, progress, logs and recovery behavior.

### P-005 — Evidence before claims

The UI may summarize findings, but it must preserve links to source assets, configuration snapshots, model identities, hashes and result manifests. The product must not call detector agreement an accuracy score when no ground truth exists.

### P-006 — Polished does not mean opaque

The app should look and feel premium, but visual polish must not hide important errors, provenance, configuration or recovery controls. Complex information should be organized through hierarchy, tabs, filters, drawers and progressive disclosure rather than removed.

### P-007 — Large corpus is a first-class case

The design target is not a 20-image demo. The app must remain responsive with thousands of images, hundreds or thousands of videos, large result tables and multi-gigabyte project assets.

### P-008 — Portability with explicit boundaries

A project should be exportable and importable, but the app must distinguish:

- portable project metadata;
- app-managed relative assets;
- externally referenced absolute paths;
- secrets that must not be exported by default;
- model files that may have redistribution restrictions;
- caches that may be regenerated rather than transferred.

### P-009 — Updates preserve user intent

App updates must migrate settings, projects and credentials without asking the user to remember which fields changed. Migrations must be versioned, backed up and recoverable.

### P-010 — Desktop security is designed, not assumed

The renderer is treated as unprivileged. Filesystem, secret, process and update operations require typed IPC through preload and main-process validation.

## 5. Primary user profiles

The initial product is optimized for a single technically capable local user, but the UI must not require command-line expertise for ordinary workflows.

### Persona A — Experiment collector

Goals:

- configure an image/video API provider;
- queue a large set of prompts;
- define rate and stop policies;
- let the run continue for hours or days;
- recover from 429s, network loss, provider errors or app restart;
- preserve raw responses and downloaded media with clear provenance.

Needs:

- credential management;
- configuration presets;
- estimated call count and budget guards;
- detailed but readable execution progress;
- pause/resume;
- failed-item retry;
- clear output folders;
- exportable run manifests.

### Persona B — Local analyst

Goals:

- import folders or sample corpora;
- index a large collection;
- run Atlas and object detection independently;
- compare model outputs;
- filter, search and inspect evidence;
- export reusable reports.

Needs:

- fast browsing;
- path management;
- model manager;
- background jobs;
- checkpoint recovery;
- reproducible configuration snapshots.

### Persona C — Report author

Goals:

- turn Atlas output into a polished PDF;
- change headings, captions, fonts, spacing and page layouts;
- select representative images;
- use a template but retain control;
- preview page breaks and export quality.

Needs:

- document editor distinct from source analysis;
- styles and templates;
- undo/redo;
- autosave;
- print preview;
- missing-font and oversized-image warnings.

### Persona D — App maintainer

Goals:

- issue an app Release from GitHub Actions;
- optionally attach sample corpus parts;
- provide custom notes and feature bullets;
- build per-platform packages;
- verify hashes/signatures;
- publish prerelease or final Release;
- migrate users safely.

Needs:

- reproducible workflows;
- manual dispatch parameters;
- artifact manifests;
- platform smoke tests;
- migration tests;
- release evidence.

## 6. Top-level application areas

### 6.1 Workspace Home

A project-oriented dashboard that shows:

- recent projects;
- corpus totals;
- current storage footprint;
- active and recoverable jobs;
- last Atlas and detection results;
- provider health when API automation is configured;
- update availability;
- warnings requiring attention.

The Home page must not attempt to show every asset. It is a concise operational overview with links into the relevant modules.

### 6.2 Import and Corpus Manager

Responsible for:

- importing files or folders;
- accepting drag-and-drop;
- resolving the containing folder when an individual file is dropped and the user chooses folder import;
- importing sample-corpus Release parts;
- importing project packages;
- indexing media metadata;
- detecting duplicates;
- reporting missing, unreadable or unsupported files;
- selecting whether data is copied into the project or referenced externally.

### 6.3 API Automation

Optional provider-driven generation with:

- credential profiles;
- prompt/task source selection;
- image and video modes;
- provider capability discovery;
- rate, concurrency, retry and stop policies;
- execution simulation/validation before start;
- durable run state;
- response and file integrity tracking.

### 6.4 Atlas Studio

Independent analysis and authoring environment with:

- corpus/cohort selection;
- repeatability processing;
- comparison pages;
- video evidence views;
- result filtering;
- selection of report material;
- rich text and layout editing;
- static PDF export.

### 6.5 Detection Studio

Independent model-analysis environment with:

- model selection and model download/verification;
- per-model settings;
- single-model or comparison runs;
- durable item-level checkpointing;
- live progress and throughput;
- image review and class filters;
- agreement/disagreement views;
- exportable machine-readable and visual results.

### 6.6 Job Center

Cross-module job management:

- queued, running, pausing, paused, cancelling, cancelled, failed, recoverable and completed states;
- stage and item progress;
- estimated remaining work without false precision;
- logs and diagnostics;
- retry failed items;
- resume recoverable jobs;
- reveal output folder;
- export job report.

### 6.7 Settings, Configurations and Secrets

Includes:

- app settings;
- project defaults;
- provider profiles;
- API keys;
- config import/export;
- folder reveal actions;
- theme, density, language and motion preferences;
- performance/cache limits;
- update channel;
- diagnostics and privacy controls.

### 6.8 Reports Library

Stores and indexes:

- Atlas report drafts;
- PDF exports;
- detection summaries;
- job audit exports;
- project manifests;
- migration and integrity reports.

## 7. Canonical end-to-end user journeys

### Journey J-001 — First launch without API key

1. User installs the app.
2. App creates the user-data directory and initial settings database.
3. Onboarding explains three entry paths: import local data, download sample corpus, configure provider.
4. User chooses sample corpus.
5. App displays expected download size, parts, checksums and license/data notice.
6. App downloads parts with resumable transfer, verifies hashes and imports them into a new project.
7. Thumbnail/index jobs run in the background.
8. User opens Atlas or Detection Studio and runs a preset workflow.
9. No API key prompt blocks this journey.

### Journey J-002 — Import an existing folder

1. User creates a project or opens an existing one.
2. User selects an image folder and a separate video folder, or drops files/folders.
3. App previews file count, supported/unsupported count, estimated storage and duplicate policy.
4. User selects copy-into-project or external-reference mode.
5. App indexes incrementally and exposes usable items before the full job completes.
6. Missing or unreadable files appear in a repair queue rather than silently disappearing.

### Journey J-003 — Configure Agnes and generate media

1. User creates an Agnes credential profile.
2. Secret value is encrypted through the OS credential provider; the renderer receives only masked metadata.
3. User imports or edits a generation configuration.
4. App validates prompts, paths, API capability, intervals, concurrency, stop rules and estimated maximum requests.
5. User starts a run.
6. The job records each attempt, provider response classification, retry timing and downloaded file checksum.
7. User may pause, quit the app and resume later.
8. Completed media is indexed into the configured generated-output corpus.

### Journey J-004 — Run Atlas and author a PDF

1. User selects a project corpus and Atlas configuration.
2. App builds cohorts and comparison evidence as a durable background job.
3. User reviews results while processing continues for remaining cohorts.
4. User creates a report draft from a template.
5. User edits titles, body text, captions, typography, image selections and page breaks.
6. GIF/video cohorts can be represented by a selected poster frame or contact sheet, but v1 PDF does not preserve animation.
7. App runs preflight checks and exports PDF plus a reproducibility manifest.

### Journey J-005 — Compare detectors

1. User opens Detection Studio and selects YOLOX-Tiny and NanoDet-Plus-m-320 or other installed compatible models.
2. Missing models are downloaded after the user reviews size, source, hash and license status.
3. User selects input corpus and thresholds.
4. App creates one logical comparison job with separate model stages.
5. Each completed item is checkpointed durably.
6. App restart resumes from the last verified item rather than restarting the corpus.
7. Result views distinguish detections, matching boxes and disagreement; they do not claim accuracy without labels.

### Journey J-006 — Offline update import

1. User downloads a signed update package or selects an app file supplied by the maintainer.
2. App identifies platform, architecture, version and signature/checksum.
3. App rejects incompatible or unsigned packages according to channel policy.
4. App creates a pre-update backup and validates free space.
5. Platform-specific installer/update flow runs.
6. On first launch, schema migrations run transactionally.
7. Projects, settings, credentials and job recovery state remain available.
8. On migration failure, the app enters recovery mode and offers restore/export diagnostics.

## 8. Data ownership and privacy

- User data remains local unless the user explicitly performs a network action.
- API request payloads are sent only to the selected provider.
- Secrets are never included in ordinary logs, config exports, project packages or support bundles.
- Raw API responses may contain sensitive provider metadata and are retained only according to project policy.
- Sample corpora derived from the repository owner’s existing Releases must be reviewed before redistribution, especially raw inputs and metadata.
- The app must display whether a project uses copied assets or external filesystem references.
- Deleting a project must clearly distinguish deleting app metadata, derived data and copied media from deleting externally referenced source files.

## 9. Success criteria

The product is successful when a technically curious user can:

- install on a supported platform;
- create a project without command-line work;
- obtain usable sample data without an API key;
- import thousands of media files without freezing the UI;
- configure paths and export/import configs;
- run a resumable Atlas job;
- run a resumable multi-model detection job;
- inspect results with responsive filters;
- author and export a polished static PDF;
- update the app without losing settings or projects;
- inspect enough provenance to understand how results were produced.

## 10. Explicit v1 non-goals

- Training, fine-tuning or labeling models as a full annotation platform.
- Remote multi-user collaboration.
- Hosting a central account system.
- Synchronizing projects to a proprietary cloud.
- Mobile-native applications.
- Browser-only parity.
- Preserving animated GIF playback inside exported PDF.
- Unlimited arbitrary provider scripting inside the renderer.
- Executing project-bundled code.
- Guaranteeing offline redistribution of every candidate model artifact before license review.

## 11. Future-compatible directions

The architecture should not block, but v1 does not promise:

- additional media-generation providers;
- plugin model adapters;
- ground-truth imports and real accuracy metrics;
- custom report templates;
- collaborative review comments;
- distributed/remote workers;
- GPU execution backends;
- OCR or embedding/search modules;
- project synchronization through user-selected storage providers;
- automated publication back to GitHub Releases.

These directions must use versioned interfaces rather than direct coupling to initial modules.