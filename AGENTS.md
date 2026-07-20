# AGENTS.md

## Scope

This file applies to the entire repository. A more specific `AGENTS.md` in a subdirectory may override it for that subtree.

## User and communication preferences

- Default user-facing language is **Traditional Chinese**.
- When the user has granted broad permission, make mainstream and reasonable implementation decisions directly instead of repeatedly asking about minor details.
- Prefer a working, production-ready implementation over a plan-only response.
- Keep progress updates concise and honest. Never claim that a workflow, Release, or deployment succeeded until it has been checked.
- Do not promise asynchronous work. Complete as much as possible in the current session.

## Git and GitHub workflow

- Work on a feature branch, open a pull request, run validation, and use a normal merge commit unless the user explicitly requests another method.
- Do not delete branches unless asked.
- Prefer a focused but complete pull request: implementation, regression tests, documentation, workflow updates, and user-facing entry points should stay synchronized.
- When GitHub connector or Actions access is unavailable, run all feasible checks locally and provide either a unified patch or Codespaces-ready commands as the fallback.
- Never use a passing unit test as proof that a production Release was published; verify the actual Release/index/writeback when the task includes publication.

## Contract hierarchy

- Read `project-contract.json` first for machine-enforced values and `docs/PROJECT_CONTRACT.md` for rationale.
- Apply `config/release-quarantine.json` to every canonical corpus consumer.
- When a contract changes, update all synchronized surfaces in the same PR and run `python tools/validate_project_contract.py`.
- YOLOX-Tiny object detection is currently specified, not implemented; do not present planned behavior as production.

## Repository source-of-truth rules

- Formal experiment data comes only from immutable `media-exp-*` Releases.
- `media-input-*` Releases are transport/snapshot artifacts. Do not include them in formal statistics or Atlas source data.
- Existing published experiment Releases are immutable. New data for an existing date must use the established supplemental Release flow.
- Historical invalid runs remain as evidence but are excluded through `config/release-quarantine.json`; never silently delete them.
- Distinguish API completion events from archived media files. Publication must fail when their counts differ.
- Prompt Repeatability Atlas rebuilds scan the complete currently published corpus. Avoid hidden incremental state or processing caches unless there is a documented, compelling reason.
- Release assets remain ZIP-only. Inline JPEG/GIF previews are served from versioned repository paths rather than uploaded as naked Release assets.
- Image and video Atlas bundles contain up to 15 prompt IDs each.

## Atlas behavior

- Image and video samples must remain in separate cohorts.
- Video seed is retained as sample evidence but excluded from the repeatability cohort identity because the harvester intentionally randomizes it for each run.
- Image Release Notes previews use an evidence-rich dynamic policy:
  - at most 15 image cohorts;
  - at least 4 verified unique samples by default;
  - cover distinct categories first using the strongest cohort in each category;
  - fill remaining slots by descending sample count with deterministic tie-breaking.
- Video Release Notes previews include all eligible comparable video cohorts by default. The current corpus contains seven video prompt cohorts.
- Release Notes should use separate **Image highlights** and **Video highlights** sections and may be long when the entries materially improve inspection.
- Every highlighted entry must link to its containing ZIP bundle.
- Keep backward-compatible combined `highlights` metadata when adding media-specific highlight fields.

## Documentation and UX direction

- `README.md` is the default Traditional Chinese landing page; `README.en.md` is the English companion.
- Update README, Atlas specifications, Visual Lab, and workflow descriptions whenever an implementation contract changes.
- The project should feel polished and complete rather than intentionally minimal. Rich but coherent UI/UX is preferred.
- Avoid hiding evidence merely to shorten a page. Use grouping, filters, headings, and downloadable bundles to manage density.

## Validation expectations

Before merging relevant changes, run or verify:

```bash
python tools/validate_project_contract.py
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt
sudo apt-get install -y --no-install-recommends ffmpeg
python -m compileall tools tests
python -m unittest discover -s tests -v
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
python tools/validate_site_build.py
```

For video Atlas work, tests must exercise real `ffmpeg`/`ffprobe` behavior with generated media rather than only mocking subprocess calls.
