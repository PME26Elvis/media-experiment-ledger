# 01 — UX and Design System Specification

## 1. Scope

This document defines the UI/UX contract for the Electron renderer. It applies to every app route, dialog, wizard, editor, result browser and settings surface.

The app must feel like a premium desktop product while remaining responsive on narrow windows and usable on touch-capable devices. “Premium” is defined by coherent hierarchy, precise spacing, meaningful motion, responsive feedback and excellent state handling—not by excessive gradients or constant animation.

## 2. Technology and coding rules

### 2.1 Required stack

- Vue 3 Single-File Components.
- Vuetify 3 current stable release at implementation time.
- TypeScript strict mode.
- Composition API only for ordinary component logic.
- Every Vue component MUST use `<script setup lang="ts">` unless a documented build/compiler limitation makes that impossible.
- Props and emits MUST be typed with `defineProps`, `withDefaults`, `defineEmits`, `defineModel` or equivalent current Vue syntax.
- Reusable logic MUST live in typed composables rather than mixins.
- Options API MUST NOT be introduced for convenience.

### 2.2 Component boundaries

- Route components orchestrate data and layout; they should not contain low-level media rendering logic.
- Domain components own one coherent behavior, such as a job progress panel or model card.
- Primitive visual components remain presentation-focused.
- Privileged Electron actions are invoked through typed service/composable APIs and never through direct global object access scattered across templates.
- Components over approximately 400 lines SHOULD be reviewed for decomposition; this is a review trigger, not an automatic rule.

## 3. Application shell

### 3.1 Desktop shell

The default wide-window shell consists of:

- `v-app` root;
- optional custom title bar only if platform testing proves native frame limitations justify it;
- `v-navigation-drawer` for primary modules;
- `v-app-bar` for project context, global search and status actions;
- `v-main` route content;
- persistent or temporary right-side inspector drawer for selected items;
- bottom `Job Shelf` that can collapse into a compact indicator.

Primary navigation groups:

1. Workspace
2. Import & Corpus
3. Automation
4. Atlas Studio
5. Detection Studio
6. Jobs
7. Reports
8. Models
9. Settings
10. Updates

Every item MUST include a semantic icon. Labels must remain visible in expanded mode; icon-only navigation requires tooltips.

### 3.2 Narrow-window shell

At narrow breakpoints:

- primary navigation becomes temporary/overlay drawer;
- the app bar retains project name, navigation trigger and the highest-priority contextual action;
- secondary actions move into an overflow menu or bottom sheet;
- inspectors become full-width dialogs or bottom sheets;
- dense multi-column tables switch to card/list representations where horizontal scrolling would hide essential context;
- editors may use step-based or tabbed panels rather than forcing simultaneous desktop panes.

The app MUST remain functionally complete in a narrow window. RWD is not only visual shrinking.

## 4. Responsive layout contract

### 4.1 Grid requirement

All primary route layouts MUST use Vuetify grid primitives:

```vue
<v-container fluid>
  <v-row>
    <v-col cols="12" lg="8">
      <!-- primary content -->
    </v-col>
    <v-col cols="12" lg="4">
      <!-- secondary content -->
    </v-col>
  </v-row>
</v-container>
```

- `v-row` and `v-col` are mandatory for macro RWD layout.
- CSS Grid MAY be used inside specialized editors, galleries or canvases when it provides better virtualization or page-layout behavior.
- Fixed pixel widths MUST NOT define the primary route structure.
- Minimum widths are allowed for tables, canvases and timeline editors, but the route must provide a deliberate overflow or alternative layout.

### 4.2 Breakpoint behavior

The implementation must define and test at least:

- compact: approximately 360–599 px;
- small: 600–959 px;
- medium: 960–1279 px;
- large: 1280–1919 px;
- extra large: 1920 px and above.

Use Vuetify display composables rather than duplicated `window.innerWidth` checks.

### 4.3 Density modes

User-selectable density:

- comfortable (default);
- compact;
- presentation/touch-friendly.

Density changes spacing and control height but MUST NOT remove labels or reduce hit targets below accessibility thresholds.

## 5. Color system

### 5.1 Semantic use

Interactive controls MUST use explicit semantic colors where appropriate:

- `primary`: main actions, selected module, active step;
- `secondary`: supporting action or alternate emphasis;
- `success`: verified, completed, valid;
- `warning`: recoverable risk, missing optional item, approaching limit;
- `error`: failed, destructive, invalid, security issue;
- `info`: neutral operational information.

Buttons, chips, progress indicators and alerts should use meaningful colors, for example:

```vue
<v-btn color="primary" prepend-icon="mdi-play">
  Start analysis
</v-btn>
```

Random color variation between cards is prohibited. Module identity may use accent colors, but state color always takes precedence.

### 5.2 Theme requirements

- Light and dark themes are required.
- System-following theme is the default.
- Theme changes apply without restart.
- Contrast must meet WCAG AA for ordinary text and controls.
- Images and result overlays require neutral surfaces that do not distort perceived colors.
- Detector bounding-box colors must be distinguishable in both themes and should not rely on red/green alone.

### 5.3 Module accents

Provisional module accents:

- Automation: primary/indigo family.
- Atlas: violet/purple family.
- Detection: cyan/blue family.
- Reports: amber/gold family.
- Jobs: neutral primary with state colors.

Exact palette remains tokenized and can change without rewriting components.

## 6. Iconography

### 6.1 Rules

- Every main navigation item uses a Material Design Icon.
- Primary buttons use `prepend-icon` by default.
- Buttons that reveal a next step, open a nested destination or download may use `append-icon`.
- Icon-only controls require accessible labels and tooltips.
- Destructive actions use a clear destructive icon and confirmation appropriate to consequence.
- Icons must communicate action or state; decorative icons should be rare.

### 6.2 Standard icon mapping

Provisional mapping:

- open folder: `mdi-folder-open-outline`
- import: `mdi-database-import-outline`
- export: `mdi-export-variant`
- image: `mdi-image-outline`
- video: `mdi-video-outline`
- API key/secret: `mdi-key-variant`
- start: `mdi-play`
- pause: `mdi-pause`
- resume: `mdi-play-circle-outline`
- cancel: `mdi-stop-circle-outline`
- retry: `mdi-refresh`
- verify: `mdi-shield-check-outline`
- Atlas: `mdi-view-grid-plus-outline`
- detection: `mdi-image-search-outline`
- PDF: `mdi-file-pdf-box`
- update: `mdi-update`
- checkpoint: `mdi-content-save-check-outline`
- warning: `mdi-alert-outline`

The implementation should centralize mappings where domain state is involved.

## 7. Hover and interaction quality

### 7.1 Mandatory `v-hover` use

`v-hover` MUST be used on meaningful interactive surfaces, including:

- project cards;
- sample-corpus cards;
- model cards;
- report templates;
- gallery/media cards;
- Atlas page thumbnails;
- job cards;
- update package cards.

A typical pattern:

```vue
<v-hover v-slot="{ isHovering, props }">
  <v-card
    v-bind="props"
    :elevation="isHovering ? 10 : 2"
    :class="{ 'surface-hovered': isHovering }"
    rounded="xl"
  >
    ...
  </v-card>
</v-hover>
```

Hover effects should combine at most two or three subtle changes:

- elevation;
- border/accent opacity;
- 1–3 px translate;
- action reveal;
- thumbnail zoom capped to a subtle amount.

### 7.2 Keyboard and touch equivalence

Hover must never be the only way to discover or execute an action.

- Focus-visible states mirror hover emphasis.
- Touch users can access actions through visible controls or tap selection.
- Hidden hover actions become persistently visible on compact/touch layouts.

### 7.3 Interaction feedback

- Buttons show loading state during bounded actions.
- Long actions create a Job Center entry instead of leaving a button spinner indefinitely.
- Save operations show saved/saving/error state.
- Drag-and-drop zones visually distinguish neutral, valid and invalid payloads.
- File/folder browse controls display the resulting path and validation status immediately.

## 8. Motion and transitions

### 8.1 Required motion patterns

The app MUST use Vuetify or Vue transitions for:

- route content entry/exit;
- expanding advanced settings;
- opening result inspectors;
- switching wizard steps;
- new job insertion and job completion;
- alerts and validation messages;
- gallery selection changes;
- template previews;
- drawer and bottom-sheet transitions.

Preferred built-ins include fade, scale, expand, slide-x and slide-y transitions. Custom transitions require design tokens and performance review.

### 8.2 Motion timing

Provisional timings:

- micro feedback: 100–160 ms;
- card/selection state: 160–220 ms;
- panel/drawer: 200–300 ms;
- route transition: 180–260 ms;
- large editor layout change: maximum 350 ms.

Continuous decorative animation is prohibited in data-heavy screens.

### 8.3 Reduced motion

When OS or app preference requests reduced motion:

- translation and scale animations are removed or shortened;
- opacity transitions may remain brief;
- progress indicators remain understandable without motion;
- no auto-panning or animated thumbnail zoom;
- chart updates avoid sweeping transitions.

Reduced-motion behavior must be covered by component tests.

## 9. Information architecture patterns

### 9.1 Progressive disclosure

Each complex page should expose:

1. essential summary;
2. primary action;
3. common settings;
4. advanced settings behind expansion panel, dialog or expert mode;
5. provenance and diagnostics in an inspector or dedicated tab.

Advanced options must remain searchable and exportable in configs even when hidden by default.

### 9.2 Tabs

Tabs are appropriate for stable peer views, such as:

- Overview / Inputs / Results / Logs;
- Gallery / Table / Comparison;
- General / Rate policy / Retry policy / Stop policy;
- Content / Typography / Layout / Export.

Tabs MUST preserve unsaved state or clearly prompt before discarding it.

### 9.3 Wizards

Use wizards for irreversible or multi-stage setup:

- new project;
- sample corpus download/import;
- provider credential creation;
- API automation run creation;
- detection job creation;
- offline update import;
- project export.

Wizards must provide back navigation, validation summary and a final review page.

### 9.4 Empty states

Every primary page requires a useful empty state with:

- clear explanation;
- one primary action;
- optional sample-data path;
- link to documentation/help;
- no implication that missing API credentials are an error when API usage is optional.

## 10. Forms and configuration UX

### 10.1 Form behavior

- Validation runs on blur and on submit; expensive validation is debounced.
- Error messages explain how to fix the problem.
- Units are visible for intervals, sizes, concurrency and budgets.
- Path fields combine text display, browse button, reveal-folder action and status icon.
- Secret fields are masked, never prefilled into ordinary DOM as plaintext after save, and reveal requires an explicit temporary action.
- Dangerous advanced values display impact estimates.

### 10.2 Config actions

Every major config page includes:

- Save;
- Save as preset;
- Reset section;
- Import config;
- Export config;
- Reveal config folder;
- Validate;
- Show effective config;
- Show differences from default.

Supported import formats are displayed in the file dialog and UI: `.yaml`, `.yml`, `.json`, `.toml`. Export is YAML or JSON in v1.

### 10.3 Unsaved state

- Dirty forms show an indicator.
- Route/window close prompts only when data would be lost.
- Autosaved editors show last saved timestamp.
- Imported config changes are previewed before application.

## 11. Large media gallery UX

### 11.1 Gallery modes

- adaptive grid;
- compact list;
- metadata table;
- comparison mode;
- selection/contact-sheet mode.

### 11.2 Media cards

Cards may show:

- optimized thumbnail;
- media type;
- dimensions/duration;
- prompt/task identifier;
- provider/model;
- duplicate/invalid markers;
- analysis badges;
- selection checkbox;
- hover actions.

The card must not request the original full-resolution asset until the user opens a detail view or zooms beyond proxy capacity.

### 11.3 Selection

- shift/range selection;
- select visible;
- select filtered;
- invert selection;
- persistent selection across virtualized pages;
- explicit count and bulk action bar.

Bulk operations must show scope before execution.

## 12. Progress visualization

### 12.1 Levels

- Global job progress: overall items/stages.
- Stage progress: download, verify, decode, infer, render, package, export.
- Current item detail: filename or stable asset ID.
- Throughput: items/sec or media/minute where meaningful.
- Estimated remaining time: only after enough samples; label as estimate.

### 12.2 Visual components

- `v-progress-linear` for deterministic batch progress.
- `v-progress-circular` for short indeterminate operations only.
- State chips for queued/paused/recoverable/error.
- Expandable logs for technical detail.
- A progress bar reaching 100% must not imply success until final verification completes.

## 13. Error and recovery UX

Errors are classified as:

- input/configuration;
- permission/path;
- network/provider;
- model/runtime;
- media decode;
- storage/disk;
- migration/update;
- internal bug.

An error surface should provide:

- human explanation;
- affected scope;
- whether completed work is safe;
- recommended action;
- retry/resume where possible;
- open folder/log/report;
- copy diagnostic ID;
- technical details under disclosure.

Raw stack traces must not be the primary error message.

## 14. Accessibility

- WCAG 2.2 AA target for renderer UI.
- Full keyboard navigation for all ordinary workflows.
- Visible focus indicators.
- Logical heading and landmark structure.
- Accessible names for icon controls.
- Status must not rely on color alone.
- Text scaling to at least 200% without loss of essential operation.
- Screen-reader announcements for job state changes must be rate-limited to avoid noise.
- Drag-and-drop always has an equivalent browse action.
- Canvas-based editors provide accessible side-panel controls and document structure representation.

## 15. Localization

- Traditional Chinese is primary.
- English is required as a secondary language.
- User-visible strings must not be hard-coded in components.
- Dates, numbers, file sizes and durations use locale-aware formatters.
- Technical identifiers and filesystem paths are not translated.
- Layouts must tolerate English labels that are materially longer than Chinese labels.

## 16. UI performance rules

- Route transitions must not trigger re-render of the entire corpus.
- Virtualized lists must use stable item keys.
- Thumbnail components cancel requests when recycled/offscreen.
- Hover effects must use compositor-friendly properties where possible.
- Avoid heavy blur/backdrop effects across large scrolling surfaces.
- Charts update on throttled data snapshots rather than every item event.
- Progress events are aggregated before entering Vue reactivity.
- The document editor should isolate canvas/page rendering from settings-panel reactivity.

## 17. Visual acceptance checklist

A feature is not visually complete until:

- wide and narrow layouts are both reviewed;
- light and dark themes are reviewed;
- hover, focus and touch behavior are equivalent;
- loading, empty, error, partial and completed states exist;
- primary actions use semantic color and icons;
- route/panel transitions are present and reduced-motion compatible;
- no primary page depends on fixed desktop-only dimensions;
- large data does not cause layout thrash or eager original-media loading;
- screenshots at standard breakpoints pass visual regression review.