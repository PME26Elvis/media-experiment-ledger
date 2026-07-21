# GitHub Pages production verification

- Verified at: `2026-07-21T04:08:00+00:00`
- Fix merge SHA: `d5276ffb4b5aa5f28830f9f8beb38f0002ab590f`
- Production workflow run: [29800253872](https://github.com/PME26Elvis/media-experiment-ledger/actions/runs/29800253872)
- Workflow conclusion: **success**
- Jobs: **build / Deploy GitHub Pages / Commit canonical analytics and forecasts** all succeeded.
- Live site: <https://pme26elvis.github.io/media-experiment-ledger/>
- Live pages checked: root plus all seven primary routes.
- Live JSON artifacts checked: analytics, forecast, Visual Lab, and YOLO Lab.
- Compiled `site/` is an ephemeral Pages artifact and is no longer tracked by Git.
- Pages deployment is independent of canonical analytics/forecast Git writeback.

## Why the previous deployment failed

The failed runs had already completed Astro and the previous route validator. They stopped before `configure-pages`, artifact upload, and deployment because the same job first attempted `git push origin HEAD:main`. Another bot workflow had updated `main`, so GitHub rejected the push as non-fast-forward.

The repaired workflow has independent jobs:

1. **build** creates and validates the Pages artifact;
2. **deploy** publishes that artifact without waiting for Git writeback;
3. **writeback** commits only `analytics/` and `forecasts/` with fetch/rebase/push retries.

The production run verified this exact race scenario: audit writeback updated `main`, then analytics/forecast writeback successfully rebased and published its own commit while Pages deployment also succeeded.

## Live checks

| Path | HTTP | Bytes |
|---|---:|---:|
| [/](https://pme26elvis.github.io/media-experiment-ledger/) | 200 | 15,553 |
| [overview/](https://pme26elvis.github.io/media-experiment-ledger/overview/) | 200 | 29,771 |
| [analytics/](https://pme26elvis.github.io/media-experiment-ledger/analytics/) | 200 | 26,958 |
| [visual-lab/](https://pme26elvis.github.io/media-experiment-ledger/visual-lab/) | 200 | 40,695 |
| [yolo-lab/](https://pme26elvis.github.io/media-experiment-ledger/yolo-lab/) | 200 | 30,951 |
| [forecast/](https://pme26elvis.github.io/media-experiment-ledger/forecast/) | 200 | 31,062 |
| [architecture/](https://pme26elvis.github.io/media-experiment-ledger/architecture/) | 200 | 47,696 |
| [frontend-stack/](https://pme26elvis.github.io/media-experiment-ledger/frontend-stack/) | 200 | 51,101 |
| [data/analytics.json](https://pme26elvis.github.io/media-experiment-ledger/data/analytics.json) | 200 | 13,069 |
| [data/forecast.json](https://pme26elvis.github.io/media-experiment-ledger/data/forecast.json) | 200 | 29,907 |
| [data/visual-analysis.json](https://pme26elvis.github.io/media-experiment-ledger/data/visual-analysis.json) | 200 | 65,872 |
| [data/yolo/latest.json](https://pme26elvis.github.io/media-experiment-ledger/data/yolo/latest.json) | 200 | 1,631,221 |

Machine-readable evidence is stored in [`data/audits/pages-deploy-verification.json`](../../data/audits/pages-deploy-verification.json).
