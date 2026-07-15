# Web experience and forecast architecture

## UI/UX direction

The redesign uses the open-source **UI UX Pro Max** design-intelligence skill as a design checklist and adopts its predictive-analytics dashboard guidance: bento-grid information hierarchy, restrained motion, keyboard-visible controls, high contrast, responsive layouts, and tooltips/export controls for charts.

The implementation stack is:

- Astro 7 and Starlight 0.41 for file-based documentation pages, navigation, search, responsive layout, and theme support
- MDX and Astro components for composable documentation and focused interactive islands
- ECharts 6 for interactive analytics and forecast visualizations
- Mermaid 11 for system diagrams
- Panzoom for wheel zoom, drag, reset, and fullscreen diagram interaction

The live site includes a dedicated **Frontend Stack** primary page documenting framework responsibilities, rendering boundaries, routing, JSON artifacts, repository structure, and deployment.

## Extensibility

Primary pages live under `web/src/content/docs/` and share a registry in `web/navigation.mjs`. Adding a new primary page requires one MDX file and one navigation object. Reference pages can be added only to the Starlight sidebar.

All internal routes and browser-loaded artifacts use `web/src/lib/sitePath.ts`. The helper normalizes Astro's GitHub Pages base path to exactly one trailing slash before appending a route or data path.

After every production build, `tools/validate_site_build.py` confirms that all primary route files exist, Overview contains base-safe links, Analytics and Forecast expose correct JSON URLs, and both deployed JSON artifacts are valid objects. The same validation gates PR CI and the Pages deployment workflow.

## Forecast pipeline

`tools/forecast_experiments.py` consumes `site/data.json` after canonical analytics are generated. For each target it:

1. builds lag, rolling, exponentially weighted, gap, weekday, and month features;
2. applies domain transforms (`log1p` or logit);
3. evaluates eight candidate methods with rolling-origin backtests;
4. forms an inverse-error weighted ensemble;
5. bootstraps out-of-sample residuals for 80% intervals;
6. simulates 10,000 next-month paths using empirical active-day gaps;
7. commits JSON, Markdown, model-card, and compact history artifacts.

The forecasts are explicitly confidence-scored because the current active-date sample is small.
