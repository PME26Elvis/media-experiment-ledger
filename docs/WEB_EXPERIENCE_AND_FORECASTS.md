# Web experience and forecast architecture

## UI/UX direction

The redesign uses the open-source **UI UX Pro Max** design-intelligence skill as a design checklist and adopts its predictive-analytics dashboard guidance: bento-grid information hierarchy, restrained motion, keyboard-visible controls, high contrast, responsive layouts, and tooltips/export controls for charts.

The implementation stack is:

- Astro 7 and Starlight 0.41 for file-based documentation pages, navigation, search, responsive layout, and theme support;
- MDX and Astro components for composable documentation and focused interactive islands;
- ECharts 6 for interactive analytics and forecast visualizations;
- Mermaid 11 for system diagrams;
- Panzoom for wheel zoom, drag, reset, and fullscreen diagram interaction.

The live site includes dedicated **Frontend Stack**, **Visual Lab**, **Detector Lab**, and **YOLO Lab** primary pages documenting platform responsibilities and exposing independent analysis indexes.

## Extensibility

Primary pages live under `web/src/content/docs/` and share a registry in `web/navigation.mjs`. Adding a new primary page requires one MDX file and one navigation object. Reference pages can be added only to the Starlight sidebar.

All internal routes and browser-loaded artifacts use `web/src/lib/sitePath.ts`. The helper normalizes Astro's GitHub Pages base path to exactly one trailing slash before appending a route or data path.

After every production build, `tools/prepare_pages_artifact.py` first removes only the repository-backed preview mirrors that Astro copied into `site/`, then `tools/validate_site_build.py` confirms that:

- all eight primary routes have compiled `index.html` files;
- Overview contains base-safe links to every primary route;
- Analytics, Forecast, Visual Lab, Detector Lab, and YOLO Lab expose the correct base-prefixed JSON URLs;
- all five deployed JSON artifacts parse as objects;
- no malformed base paths are present;
- `site/data/visual-analysis/previews/`, `site/data/detection/previews/`, and `site/data/yolo/previews/` are absent from the deployable payload;
- the generated Pages artifact remains below the configured total/per-file size guards.

The same preparation and validation gate PR CI and the Pages deployment workflow.

## Pages build boundary

`web/` is source. `site/` is Astro build output.

Versioned Atlas, combined-detector, and legacy YOLO previews remain tracked under `web/public/` because Release Notes and Lab JSON deliberately reference their `raw.githubusercontent.com` URLs. Those repository files are the durable preview evidence and are not removed or rewritten during a Pages build.

Astro copies `web/public/` into `site/`, so an unprepared build would contain a second, unnecessary binary mirror of the full preview history. `tools/prepare_pages_artifact.py` removes those three preview subtrees **only from the ephemeral `site/` directory** before validation and `actions/upload-pages-artifact`. Routes and browser JSON stay in Pages; preview bytes continue to load from their versioned raw-GitHub source URLs. This preserves historical evidence while preventing repeated Atlas preview trees from consuming the supported Pages artifact budget.

The `site/` directory is generated only inside CI or a local build and is ignored by Git. The production workflow separates build, deploy, and canonical-data writeback. A concurrent bot commit can delay or fail the writeback after retries, but it cannot prevent deployment of an already validated Pages artifact.

## Forecast pipeline

`tools/forecast_experiments.py` consumes `site/data.json` after canonical analytics are generated. For each target it:

1. builds lag, rolling, exponentially weighted, gap, weekday, and month features;
2. applies domain transforms (`log1p` or logit);
3. evaluates eight candidate methods with rolling-origin backtests;
4. forms an inverse-error weighted ensemble;
5. bootstraps out-of-sample residuals for 80% intervals;
6. simulates 10,000 next-month paths using empirical active-day gaps;
7. writes JSON, Markdown, model-card, chart, and compact history artifacts under `forecasts/`.

The forecasts are explicitly confidence-scored because the current active-date sample is small.

<!-- NANODET:WEB:START -->
## Detector Lab integration

The site has **eight primary routes** and **five deployed JSON artifacts**. Detector Lab is the combined YOLOX/NanoDet route and reads `data/detection/latest.json`; YOLO Lab remains available for immutable legacy YOLO-only history. The route uses the same base-safe `sitePath()` helper, Astro build boundary, ephemeral `site/` artifact, and `actions/upload-pages-artifact` deployment contract. Detector preview images remain repository-backed raw-GitHub evidence rather than duplicate Pages payload bytes.
<!-- NANODET:WEB:END -->
