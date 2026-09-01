# 05 — Atlas Studio Specification

## 1. Scope

Atlas Studio is an independent desktop module that transforms a selected local corpus into controlled repeatability comparisons and then lets the user turn those results into a polished, editable, static document.

This specification restates the complete app behavior. Implementers must not assume familiarity with the existing web Prompt Repeatability Atlas.

Atlas Studio contains two related but separate layers:

1. **Atlas Analysis** — deterministic corpus validation, cohorting, deduplication, sample selection and evidence generation.
2. **Atlas Document Studio** — editable page/document composition, templates, typography, image selection and PDF export.

Analysis results are immutable evidence snapshots. Document drafts reference or copy from those snapshots but may change wording, selection and presentation without rewriting the underlying evidence.

## 2. Goals

- Run Atlas analysis on user-selected local images and videos.
- Preserve compatibility with current repository Atlas concepts where useful.
- Support thousands of media files through durable jobs.
- Make partial results inspectable while the job continues.
- Keep image and video cohorts separate.
- Provide primary, extended and full evidence views.
- Allow users to create rich report documents from analysis results.
- Export visually polished PDFs for static content.
- Represent GIF/video evidence through selected static frames/contact sheets in PDF.
- Preserve full reproducibility metadata outside and optionally inside the PDF.

## 3. Non-goals

- General raster image retouching.
- Video editing.
- Animated PDF playback.
- Treating visually similar but differently configured generations as the same cohort without an explicit normalization rule.
- Mutating original media.
- Publishing automatically to the existing `media-analysis-*` Release family in v1.

## 4. Input sources

Atlas jobs may consume:

- project image input binding;
- project video input binding;
- generated-media run output;
- selected folders/files;
- imported sample corpus;
- imported repository experiment Release data;
- a saved filtered asset set;
- another Atlas-compatible manifest.

Each input snapshot stores exact asset IDs/hashes. A later folder change does not silently alter an existing Atlas job.

## 5. Metadata sources and normalization

### 5.1 Preferred metadata

- app-generated task/request records;
- imported JSONL completion events;
- sample-corpus manifest;
- explicit user metadata mapping;
- filename/prompt mapping rules;
- manual assignment in corpus editor.

### 5.2 Required identity fields

For a controlled cohort:

- `media_type`;
- `prompt_id` or user-defined canonical task identity;
- model/provider model identifier;
- normalized appearance-relevant settings.

Prompt text may be stored as evidence but does not replace a stable prompt/task ID when one exists.

### 5.3 Appearance-relevant settings

Images may include:

- model revision;
- dimensions/aspect ratio;
- quality/mode;
- sampler/scheduler;
- steps;
- guidance;
- seed policy;
- negative prompt;
- reference/input media hashes;
- style controls;
- provider-specific rendering fields.

Videos may include:

- model revision;
- frame count;
- frame rate;
- dimensions/aspect ratio;
- negative prompt;
- motion/camera controls;
- quality controls;
- conditioning media hashes;
- duration-related parameters.

Transport-only fields such as response format or download URL are excluded.

### 5.4 Seed policy

Seed handling is configurable per imported source schema.

Default compatibility policy:

- image seed remains part of cohort identity when it controls appearance and the goal is same-seed repeatability;
- video seed is preserved as sample evidence but may be excluded from cohort identity when the collection process intentionally randomizes seed for every run;
- the job review page displays the effective seed rule;
- changing seed policy creates a new analysis snapshot and fingerprint.

## 6. Media validation

### 6.1 Image validation

An image is usable only when:

- file exists and can be opened;
- byte size is non-zero;
- supported decoder recognizes format;
- dimensions are valid;
- decode/verify succeeds;
- SHA-256 completes;
- required cohort identity can be resolved.

Warnings may include color profile, unusually large dimensions, truncated metadata or orientation normalization.

### 6.2 Video validation

A video is usable only when:

- file exists and byte size is non-zero;
- FFprobe finds a video stream;
- duration and dimensions are valid;
- frames near start, midpoint and end decode;
- SHA-256 completes;
- required cohort identity can be resolved.

Supported containers depend on bundled FFmpeg. Initial expected set includes MP4, MOV, M4V, WebM, MKV and AVI where codec support exists.

### 6.3 Invalid media behavior

Invalid files are never silently excluded. The analysis summary lists:

- asset/path;
- failure stage;
- error classification;
- repair/relink possibility;
- whether retry may help;
- whether the user can exclude explicitly.

## 7. Deduplication

- Exact byte duplicates are detected by SHA-256.
- Only byte-unique samples count toward repeatability sample count by default.
- All source aliases remain in evidence.
- Perceptual similarity may be calculated in a future module but must not replace exact deduplication without explicit user choice.
- Duplicate policy is stored in the analysis fingerprint.

## 8. Cohort eligibility

- Image and video cohorts never mix.
- Minimum default: two verified byte-unique samples.
- User may increase minimum sample count for a job.
- Singleton and invalid cohorts remain visible in an excluded/incomplete view.
- Cohort IDs are deterministic hashes of normalized identity fields.
- Cohort display name combines prompt ID, model and concise settings summary.

## 9. Temporal selection

Samples are ordered by reliable generation/completion timestamp when available, then import timestamp/path as deterministic fallback.

Primary selection rules:

- 2 samples: both;
- 3 samples: all three with explicit empty fourth cell in a 2×2 layout;
- 4 samples: all four;
- more than 4: temporal anchors covering earliest, intermediate quantiles and latest;
- latest verified sample must be included;
- selection is deterministic for the same input snapshot and policy.

Extended selection:

- images: up to 16 temporal quantiles by default;
- videos: up to 8 temporal quantiles by default.

Full evidence includes all verified byte-unique samples in chronological order.

## 10. Image rendering

### 10.1 Primary comparison

Layouts:

| Unique samples | Layout |
|---:|---|
| 0–1 | no primary comparison |
| 2 | 1×2 |
| 3 | 2×2 with explicit empty cell |
| 4+ | deterministic 2×2 selection |

Default rendering characteristics:

- contain/letterbox, never crop by default;
- neutral background configurable by template;
- source aspect ratio preserved;
- sample label and concise provenance;
- optional timestamp/seed/model caption;
- high-resolution output suitable for screen and document use;
- derived files include source asset IDs and renderer version.

### 10.2 Extended and full sheets

- Extended: up to 16 selected samples.
- Full: every verified unique image.
- Default pagination: 16 images per page.
- User may choose 4, 6, 9, 12 or 16 cells per page for document drafts.
- Analysis evidence rendering remains deterministic; document layout may choose different presentation.

### 10.3 Color management

- honor embedded color profile where supported;
- normalize orientation;
- define sRGB export default;
- warn when conversion is unavailable;
- do not silently apply aesthetic enhancements.

## 11. Video and GIF evidence

### 11.1 Interactive app preview

Atlas result browser may show:

- animated GIF proxy;
- optimized video proxy;
- synchronized tile playback;
- keyframes;
- metadata and duration.

### 11.2 Primary video comparison

Default compatibility behavior:

- 2 samples: 1×2;
- 3: 2×2 with empty cell;
- 4+: deterministic 2×2;
- each tile starts at t=0;
- long clips use configured preview duration;
- short clips freeze on final frame rather than loop early;
- contain/letterbox without cropping;
- default 6 seconds, 6 FPS, 128 colors and 480×270 per tile for GIF proxies.

### 11.3 Full video evidence

- keyframe contact sheets for every verified unique video;
- default frames at 10%, 50% and 90%;
- default 16 videos per evidence page;
- each cell shows duration and stable sample label;
- frame extraction errors are recorded per sample.

### 11.4 PDF representation

PDF v1 does not claim animation support.

For each GIF/video item, the document author chooses:

- poster frame;
- 3-frame strip;
- 10/50/90% contact sheet;
- primary comparison still frame at selected time;
- omit from PDF while retaining link/reference;
- QR/link to external evidence only if enabled and privacy-reviewed.

The editor displays an “interactive media converted to static representation” badge. Export manifest records the selected representation and timestamp(s).

## 12. Atlas job pipeline

Stages:

1. freeze input asset snapshot;
2. load/normalize metadata;
3. validate paths and media;
4. calculate hashes and exact duplicates;
5. build cohort identities;
6. compute eligibility and temporal selections;
7. generate thumbnails/proxies;
8. render primary comparisons;
9. render extended evidence;
10. render full image/video evidence pages;
11. write sidecars and summary;
12. build searchable result index;
13. verify output completeness;
14. mark analysis snapshot complete.

Each stage is checkpointed. Completed media or cohort outputs are reused only within the same job fingerprint and renderer version.

## 13. Analysis fingerprint

Fingerprint includes:

- ordered input asset hashes/IDs;
- metadata snapshot hash;
- cohort normalization policy;
- seed policy;
- minimum samples;
- validation policy;
- deduplication policy;
- selection policy;
- rendering config;
- engine/renderer version;
- schema version.

A change creates a new snapshot rather than mutating a completed one.

## 14. Atlas result data model

### 14.1 Analysis snapshot

Fields include:

- snapshot ID;
- project/job ID;
- fingerprint;
- created/completed times;
- source asset count;
- valid/invalid/duplicate counts by media type;
- cohort counts by status;
- config snapshot;
- engine versions;
- output root;
- integrity state.

### 14.2 Cohort record

- cohort ID;
- media type;
- prompt/task ID;
- prompt text reference;
- provider/model;
- normalized settings;
- sample count and unique count;
- primary sample IDs;
- extended sample IDs;
- all sample IDs;
- render assets;
- warnings;
- tags/category;
- user annotations stored separately from evidence.

### 14.3 Sidecars

Every rendered comparison has a JSON sidecar containing:

- renderer/schema version;
- source asset IDs/hashes;
- layout;
- selection algorithm;
- cell coordinates;
- displayed labels;
- output dimensions/hash;
- warnings;
- source timestamps.

## 15. Atlas result browser

### 15.1 Main layout

Wide layout:

- left filter/navigation rail;
- center virtualized result gallery/table;
- right evidence inspector.

Narrow layout:

- filter dialog/bottom sheet;
- single-column cards;
- full-screen inspector.

### 15.2 Filters

- media type;
- prompt/task ID;
- model/provider;
- category/tag;
- sample count;
- eligible/incomplete/invalid;
- warning type;
- date range;
- settings fields;
- included in document;
- user rating/flag.

### 15.3 Views

- primary gallery;
- extended evidence;
- full evidence pages;
- metadata table;
- timeline;
- invalid/excluded queue;
- document selection tray.

Cards use `v-hover`, semantic badges/icons and optimized thumbnails. Full originals load only on explicit zoom/detail.

## 16. Document Studio model

### 16.1 Separation from analysis

A document draft stores references to an immutable analysis snapshot and user-authored content. Editing a document never changes the analysis snapshot.

### 16.2 Document hierarchy

```text
Document
├─ metadata
├─ theme/template
├─ global styles
├─ sections[]
│  ├─ heading/content blocks
│  ├─ cohort comparison blocks
│  ├─ gallery/contact-sheet blocks
│  ├─ statistics/table blocks
│  ├─ callout blocks
│  └─ page-break controls
├─ assets[]
├─ revision history
└─ export settings
```

### 16.3 Block types

Initial block types:

- title page;
- section heading;
- rich text;
- image;
- primary Atlas comparison;
- extended/full contact sheet;
- video static representation;
- caption;
- callout;
- key-value metadata;
- table;
- statistics summary;
- divider;
- spacer;
- page break;
- header/footer;
- appendix/provenance block.

Blocks have stable IDs and versioned schemas.

## 17. Rich text editing

Required formatting:

- font family;
- font size;
- bold/font weight;
- italic;
- underline;
- text color;
- background/highlight where accessible;
- alignment;
- line height;
- letter spacing provisional;
- paragraph spacing;
- heading levels;
- bullets/numbering;
- links;
- inline code/technical identifiers provisional.

Requirements:

- toolbar and inspector controls;
- keyboard shortcuts;
- style presets;
- paste sanitization;
- undo/redo;
- selection-preserving updates;
- IME-safe Traditional Chinese input;
- no arbitrary script/unsafe HTML;
- document content stored as structured JSON, not only HTML.

## 18. Template system

### 18.1 Built-in templates

At least five v1 templates:

1. **Research Light** — white, restrained, scientific.
2. **Editorial Dark** — dark premium presentation.
3. **Gallery Minimal** — image-forward, low text density.
4. **Technical Audit** — provenance, tables and evidence emphasis.
5. **Executive Review** — concise summaries and selected highlights.

### 18.2 Template contents

- page size/margins;
- color tokens;
- typography scale;
- heading/body/caption styles;
- default cover;
- grid/contact-sheet rules;
- headers/footers/page numbers;
- callout styles;
- default evidence appendix;
- light/dark image-frame treatments.

### 18.3 Template behavior

- switching template previews changes before applying;
- user-authored content remains;
- incompatible custom overrides are listed;
- user can reset a block to template style;
- custom template import/export is deferred until schema security is complete;
- templates cannot execute code or load remote fonts automatically.

## 19. Page layout editor

### 19.1 Editing modes

- structure outline;
- paged canvas;
- content inspector;
- style inspector;
- print preview.

### 19.2 Layout operations

- add/remove/reorder sections and blocks;
- drag selected cohorts from result browser;
- duplicate block/page;
- select image variants;
- set crop mode only in document copy, never evidence render;
- control span/full-width;
- set keep-with-next;
- avoid page break inside;
- force page break before/after;
- repeat table headers;
- choose caption placement;
- choose static video representation;
- lock block to prevent accidental edits.

### 19.3 Autosave and revisions

- debounce autosave;
- explicit saved state;
- crash-safe command journal;
- undo/redo command stack;
- named snapshots/checkpoints;
- restore previous revision;
- migration of document schema on app update.

## 20. PDF export

### 20.1 Export engine

Provisional implementation uses an isolated print renderer and Chromium/Electron PDF generation or an equivalent deterministic engine. The document renderer must not depend on the visible editor DOM.

### 20.2 Export settings

- A4, Letter and custom page size;
- portrait/landscape;
- margins;
- bleed provisional;
- image quality/downsampling;
- embed fonts where permitted;
- page numbers;
- metadata/title/author;
- include evidence appendix;
- include reproducibility manifest attachment or companion JSON;
- output path;
- overwrite/version naming policy.

### 20.3 Preflight

Block export or warn for:

- missing source/proxy;
- unsupported or unlicensed font embedding;
- overflow/clipped text;
- low effective image DPI;
- unresolved video representation;
- broken link;
- missing glyphs;
- unsupported transparency/color issue;
- invalid page size;
- insufficient disk space;
- document not fully saved;
- analysis snapshot integrity failure.

### 20.4 Output package

Default export:

```text
<report-name>.pdf
<report-name>.manifest.json
```

Optional evidence package:

```text
<report-name>-evidence.zip
```

Manifest includes:

- document ID/revision;
- template/version;
- analysis snapshot/fingerprint;
- block list;
- source asset hashes;
- selected frames/timestamps;
- fonts;
- export settings;
- app/engine version;
- PDF SHA-256.

### 20.5 Determinism

Same saved document revision, source assets, fonts and engine version should produce visually equivalent output. Byte-identical PDF is desirable but not mandatory when metadata timestamps differ; a deterministic-content mode may normalize them.

## 21. Batch document operations

Because Atlas can contain many cohorts:

- add all filtered cohorts to document;
- group by category/model/date;
- apply a layout preset to selected blocks;
- bulk caption template with variables;
- bulk static video representation;
- bulk style assignment;
- regenerate affected document proxies after template change;
- export section ranges;
- split oversized report into volumes;
- estimate page count and PDF size before rendering.

Batch operations display scope and are undoable where feasible.

## 22. Performance requirements

- result browser virtualizes thousands of cohort cards;
- editor loads page thumbnails and nearby pages, not every full page at once;
- document canvas uses optimized proxies matched to zoom/display pixels;
- originals load only for export or high zoom;
- PDF rendering runs outside the renderer and reports page progress;
- text editing remains responsive while background analysis runs;
- image decoding/conversion is bounded by worker concurrency and memory budget;
- page thumbnails are cached by document revision and block hashes;
- export can resume only at safe document/page stages; final PDF assembly is atomic.

## 23. Security

- rich text is sanitized structured content;
- imported templates cannot execute scripts;
- remote images/fonts are not fetched without explicit approval;
- file references use path grants;
- PDF hyperlinks are reviewed and can be disabled;
- export renderer has no secret access;
- analysis and document bundles use traversal-safe archive handling.

## 24. Acceptance criteria

- import or select a corpus and create deterministic cohorts;
- image/video cohorts remain separate;
- validation and duplicate exclusions are inspectable;
- primary/extended/full evidence covers every verified unique sample according to policy;
- job pauses/resumes without redoing verified completed cohorts;
- user can browse thousands of results responsively;
- user can create a document from a built-in template;
- user can edit text size, font, bold, italic, underline, alignment and styles;
- user can select static representations for GIF/video content;
- user can reorder blocks, control page breaks and undo changes;
- autosave/recovery restores an interrupted document session;
- PDF preflight catches missing media and text overflow;
- exported PDF is polished and accompanied by manifest;
- source media and analysis snapshot remain unchanged by document editing;
- no PDF claims to contain animated GIF playback.