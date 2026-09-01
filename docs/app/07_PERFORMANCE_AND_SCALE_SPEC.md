# 07 — Performance and Scale Specification

## 1. Scope

This document defines how the app remains responsive with large projects. The design target is not limited to current repository totals.

Required design corpus:

- 10,000 images;
- 1,000 videos;
- multiple Atlas snapshots;
- two or more detection models;
- hundreds of thousands of detection rows/boxes;
- multi-gigabyte sample/project archives;
- long-running jobs across app restarts.

The app may support larger projects, but these numbers define the first mandatory benchmark suite.

## 2. Performance principles

### PP-001 — Never eagerly decode the corpus

The renderer must not load full-resolution images or videos for every visible database item. It loads only optimized representations required by the current viewport and zoom.

### PP-002 — Work follows visibility and priority

Visible items and user-requested details receive higher priority than offscreen cache generation. Background work must not starve active jobs or interactive actions.

### PP-003 — Derived media is a pyramid

One thumbnail size cannot serve every UI. The app generates/selects a proxy level near the actual display requirement.

### PP-004 — The database is the index

Large collections are queried through indexed/paginated database operations, not held as one giant reactive JavaScript array.

### PP-005 — Renderer events are aggregated

Workers may process many items per second, but Vue receives bounded snapshots/deltas rather than every low-level event.

### PP-006 — Memory and concurrency are budgeted

Caches, workers, decoders, model sessions and exports have explicit limits and backpressure.

### PP-007 — Every expensive preprocessing stage is resumable

Hashing, thumbnail creation, video proxying and indexing persist checkpoints.

## 3. Asset indexing

### 3.1 Discovery

Directory discovery streams entries in batches. It must not build a complete in-memory file tree before showing progress.

Stages:

1. enumerate paths;
2. quick classify by extension/signature;
3. stat and create provisional asset record;
4. schedule metadata/decode verification;
5. schedule full hash;
6. schedule thumbnail/proxy;
7. mark index completeness.

Users can browse provisional assets before all expensive stages complete. Status badges indicate unverified items.

### 3.2 Incremental change detection

For external folders:

- initial scan records path, size and mtime hints;
- subsequent scan compares hints;
- changed/new candidates receive full verification;
- deleted paths become missing records rather than immediate deletion;
- filesystem watchers are hints, never the only source of truth;
- periodic/manual reconciliation remains available.

### 3.3 Hashing

- stream files in bounded chunks;
- limit concurrent disk readers;
- prioritize files needed by active jobs;
- pause/recover hashing jobs;
- cache hash by stable file identity/size/mtime but revalidate when uncertainty exists;
- expose bytes hashed and throughput.

## 4. Thumbnail and proxy architecture

### 4.1 Image pyramid

Provisional long-edge levels:

- 160 px: compact list/grid;
- 320 px: normal gallery card;
- 640 px: large card/inspector preview;
- 1280 px: detail view/document editing proxy;
- original: explicit high zoom/export only.

The actual set may be tuned by benchmarks. Each proxy key includes:

- source image SHA-256;
- level;
- orientation/color transform version;
- encoder/version;
- crop/contain policy;
- output format/quality.

### 4.2 Display-pixel-aware selection

The thumbnail component computes required physical pixels from:

- rendered CSS dimensions;
- device pixel ratio;
- current zoom;
- image fit mode.

It requests the smallest proxy that satisfies the requirement with a modest quality margin. It upgrades progressively when needed and never downloads/decodes original merely because it exists.

### 4.3 Progressive presentation

- optional low-quality placeholder or dominant-color placeholder;
- fade transition to final proxy;
- cancel stale request when item scrolls offscreen;
- reuse by image hash across modules;
- failure placeholder with retry action.

### 4.4 Proxy formats

Provisional:

- WebP or JPEG for ordinary image proxies depending on alpha/content;
- PNG only where lossless/alpha is required;
- generated proxies strip unnecessary metadata;
- proxy manifest retains source orientation/profile decisions.

### 4.5 Video proxies

Video browsing must not decode original videos continuously.

Derived forms:

- poster thumbnail;
- 3-frame strip;
- short low-resolution preview clip, optional;
- Atlas GIF proxy;
- keyframe contact sheet.

Proxy generation is background, resumable and limited by FFmpeg worker concurrency.

## 5. Virtualized UI collections

### 5.1 Required virtualization

Virtualization is required for:

- media gallery/list;
- task/request table;
- job event log;
- detection result list;
- class/detection tables;
- Atlas cohort gallery;
- report/document page thumbnails;
- model benchmark history.

### 5.2 Data windowing

- query by stable sort and cursor/keyset pagination;
- retain a bounded window around viewport;
- prefetch next/previous pages based on scroll direction;
- cancel irrelevant DB queries;
- preserve selection by stable ID outside loaded window;
- filter/sort in database when possible;
- avoid client-side sorting of 100,000-row sets.

### 5.3 Variable-size grids

Media cards may vary in aspect ratio. Preferred strategies:

- fixed card frame with contained thumbnail for maximum virtualization stability;
- optional masonry mode only after performance validation;
- measurement cache invalidated by breakpoint/density changes;
- anchor scroll position when items above viewport change height.

## 6. Renderer state boundaries

### 6.1 Pinia/state usage

Renderer state contains:

- current project summary;
- route filters;
- current selection IDs;
- small page windows;
- UI preferences;
- aggregated job snapshots.

It must not contain:

- entire media corpus objects;
- all detection boxes;
- original binary media;
- raw logs;
- decrypted secrets;
- full document raster pages.

### 6.2 Reactivity control

- use shallow refs for large immutable snapshots;
- stable object identity for virtualized items;
- batch updates;
- debounce filter inputs;
- use web workers only for renderer-safe computations, not privileged file access;
- avoid deep watchers on large structures;
- isolate editor state by document/page/block.

## 7. Main-thread budgets

Targets on reference hardware after warm-up:

- ordinary UI interaction response: under 100 ms;
- no repeated renderer long tasks over 50 ms during scrolling;
- route shell visible under 500 ms for opened project when DB is healthy;
- virtualized gallery first useful content under 1 s for local indexed project;
- filter update feedback under 150 ms, with progressive results allowed;
- app main event loop must not execute heavy synchronous scans/decodes;
- progress UI update frequency normally 4–10 Hz maximum depending on view.

These are test targets, not guarantees for slow storage or first-time indexing.

## 8. Worker pools and backpressure

### 8.1 Separate pools

- filesystem/hash pool;
- image decode/proxy pool;
- video/FFmpeg pool;
- API network pool;
- inference pool;
- PDF/export pool.

### 8.2 Scheduler inputs

Scheduler considers:

- user-visible priority;
- active module job priority;
- disk type/throughput;
- CPU load;
- memory budget;
- execution provider/model memory;
- power/eco mode;
- app foreground/background state;
- thermal indicators where reliable.

### 8.3 Backpressure

- bounded queue per pool;
- producer pauses when queue exceeds limit;
- downloads stream to disk;
- decoders limit simultaneous uncompressed frames;
- inference queue waits when model worker is saturated;
- PDF export has exclusive/high-memory mode when needed;
- user can reduce resource preset without restarting job.

## 9. Cache architecture

### 9.1 Cache categories

- image thumbnails/proxies;
- video posters/strips/proxies;
- decoded metadata;
- Atlas render outputs;
- detection overlay tiles/previews;
- document page thumbnails;
- downloaded sample/model archives;
- network metadata.

### 9.2 Cache key

Content-addressed where possible:

```text
<source-hash>/<transform-version>/<parameters-hash>.<ext>
```

### 9.3 Budgets

User-configurable:

- total cache disk size;
- per-project cache limit;
- memory cache limit;
- minimum free disk threshold;
- retain recent projects priority;
- keep exported/document assets priority.

Derived evidence explicitly retained by a completed analysis is not evicted as ordinary cache unless marked regenerable in its manifest.

### 9.4 Eviction

- LRU weighted by regeneration cost;
- never evict in-use files;
- transactional cache index;
- evicted entry remains safely regenerable;
- cleanup can run incrementally;
- user sees reclaim estimate;
- low disk automatically pauses heavy jobs before corruption risk.

## 10. Database performance

### 10.1 Index requirements

Indexes for common queries:

- asset media type/status/path/hash/date;
- prompt/task/model/provider;
- job state/type/updated time;
- detection class/confidence/count/comparison state;
- Atlas media type/category/sample count/status;
- report updated time/template;
- full-text search fields where adopted.

### 10.2 Query rules

- no unbounded `SELECT *` for corpus views;
- explain/query-plan review for major filters;
- keyset pagination preferred over large offsets;
- count queries may use cached aggregates for huge tables;
- background aggregate refresh is transactional;
- renderer query cancellation supported;
- DB writes batched but checkpoint durability preserved.

### 10.3 Migration performance

Large data migrations must:

- be resumable or transactional;
- show progress;
- estimate free-space requirement;
- avoid loading entire tables into memory;
- create new indexes after bulk transformation where appropriate;
- retain backup until integrity verification.

## 11. Detection scale

- model session stays resident per worker;
- decode queue and inference queue are separate;
- normalized detection rows are written in batches per item transaction;
- visual overlays are generated on demand or for selected representatives;
- class summaries use incremental aggregates;
- comparison jobs operate by asset/model output IDs;
- full result table never materializes in renderer;
- optional raw tensor retention is off by default.

## 12. Atlas/document scale

- cohort construction streams/query-groups metadata;
- evidence render jobs checkpoint per cohort/page;
- result gallery virtualizes cohorts;
- document editor renders visible/nearby pages only;
- page thumbnails are cached;
- document blocks reference proxies;
- PDF export requests export-resolution assets only during backend render;
- oversized report can split into volumes;
- batch style/layout changes invalidate only affected page hashes.

## 13. Video scale

- never open all videos simultaneously;
- FFprobe/decode workers bounded separately;
- poster/keyframe extraction scheduled before animated proxy;
- visible playback limited to one or a small configurable count;
- offscreen videos pause and release decoder;
- proxy bitrates/resolutions are configurable;
- contact sheets preferred for large overview pages.

## 14. Startup and project open

### 14.1 App startup

Do not block first window on:

- full model scan/hash;
- update download;
- every project validation;
- cache cleanup;
- provider network health.

Show shell, then progressively load.

### 14.2 Project open

Sequence:

1. acquire lock;
2. read manifest;
3. open DB and verify schema;
4. load summary aggregates;
5. restore UI context;
6. show project;
7. reconcile stale jobs/paths in background;
8. defer full external folder rescan until policy/user action.

## 15. Memory management

- hard memory cache limits;
- dispose object URLs and image bitmaps;
- release video decoders when offscreen;
- unload unused model sessions;
- avoid duplicate full-resolution buffers across processes;
- worker messages reference files, not binary copies;
- monitor process memory and cache pressure;
- enter degraded mode before OS termination where possible;
- log high-water marks in performance diagnostics.

## 16. Performance telemetry

Local-only by default:

- route/load timings;
- DB query durations;
- long tasks;
- thumbnail hit/miss;
- worker queue depth;
- throughput;
- memory high-water;
- model load/inference timing;
- PDF page render time;
- dropped/cancelled preview requests.

User can export sanitized performance report. No remote telemetry without separate approval.

## 17. Benchmark fixtures

Mandatory synthetic/curated fixtures:

- 10,000 JPEG/PNG images with varied dimensions;
- exact duplicates and corrupt files;
- 1,000 short videos with mixed containers/codecs plus invalid files;
- 10,000 automation tasks;
- two-model detection outputs with millions of boxes worst-case guard fixture;
- 2,000 Atlas cohorts;
- 500-page report draft;
- slow HDD simulation;
- low disk simulation;
- memory constrained run;
- app restart/crash at every major stage.

Tests must avoid committing huge binaries; CI can generate deterministic media or fetch versioned benchmark artifacts.

## 18. Acceptance budgets

Reference tiers must be defined before implementation release. Initial acceptance intent:

- scrolling remains visually smooth with virtualized 10,000-item gallery;
- renderer memory does not grow linearly with total corpus size;
- opening a detail view loads no more than required proxy/original;
- offscreen thumbnail requests are cancelled;
- first useful project summary appears without full rescan;
- hashing/proxy/inference jobs can be paused/resumed;
- renderer stays interactive during two-model inference;
- app restart continues without repeating verified items;
- cache eviction never removes non-regenerable evidence;
- document editor handles 500 pages through page virtualization;
- PDF export does not block renderer/main event loops;
- low disk pauses safely and explains recovery.

Exact numerical thresholds will be calibrated on at least one low/mid/high reference machine and recorded in the benchmark contract.