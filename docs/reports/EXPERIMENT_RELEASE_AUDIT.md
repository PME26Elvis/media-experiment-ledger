# Experiment Release Audit

> 此報告由 GitHub Actions 全量重建，不使用持久化 state 或 cache。

- Generated at (UTC): `2026-08-04T07:12:27+00:00`
- Repository: `PME26Elvis/media-experiment-ledger`
- Releases audited: **20**
- Canonical runs: **22**
- Quarantined historical runs: **2**
- Canonical archived images: **893**
- Canonical archived videos: **86**

## Release summary

| Release | Status | Manifest runs | Canonical | Quarantined | API images | Archived images | API videos | Archived videos |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `media-exp-2026-06-29` | corrected | 3 | 1 | 2 | 0 | 0 | 4 | 4 |
| `media-exp-2026-06-30` | ok | 3 | 3 | 0 | 40 | 40 | 0 | 0 |
| `media-exp-2026-07-01` | ok | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `media-exp-2026-07-02` | ok | 1 | 1 | 0 | 32 | 32 | 7 | 7 |
| `media-exp-2026-07-03` | ok | 1 | 1 | 0 | 28 | 28 | 7 | 7 |
| `media-exp-2026-07-05` | ok | 1 | 1 | 0 | 80 | 80 | 7 | 7 |
| `media-exp-2026-07-11` | ok | 1 | 1 | 0 | 59 | 59 | 0 | 0 |
| `media-exp-2026-07-12` | ok | 1 | 1 | 0 | 145 | 145 | 7 | 7 |
| `media-exp-2026-07-13` | ok | 1 | 1 | 0 | 3 | 3 | 1 | 1 |
| `media-exp-2026-07-17` | ok | 1 | 1 | 0 | 7 | 7 | 4 | 4 |
| `media-exp-2026-07-20` | ok | 1 | 1 | 0 | 1 | 1 | 4 | 4 |
| `media-exp-2026-07-21` | ok | 1 | 1 | 0 | 3 | 3 | 4 | 4 |
| `media-exp-2026-07-22` | ok | 1 | 1 | 0 | 1 | 1 | 7 | 7 |
| `media-exp-2026-07-23` | ok | 1 | 1 | 0 | 0 | 0 | 2 | 2 |
| `media-exp-2026-07-27` | ok | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `media-exp-2026-07-28` | ok | 1 | 1 | 0 | 306 | 306 | 4 | 4 |
| `media-exp-2026-07-29` | ok | 1 | 1 | 0 | 113 | 113 | 7 | 7 |
| `media-exp-2026-07-30` | ok | 1 | 1 | 0 | 9 | 9 | 7 | 7 |
| `media-exp-2026-07-31` | ok | 1 | 1 | 0 | 4 | 4 | 7 | 7 |
| `media-exp-2026-08-03` | ok | 1 | 1 | 0 | 62 | 62 | 7 | 7 |

## Findings

- `media-exp-2026-06-29` / `run_20260629_232751` · **warning** · `empty_run` · Run contains no source files
- `media-exp-2026-06-29` / `run_test` · **warning** · `completed_events_vs_manifest_media` · completed events={'images': 550, 'videos': 7}, manifest media files={'images': 0, 'videos': 0}

## Quarantine policy

歷史 Release assets 維持不變；已確認無效的 run 由 `config/release-quarantine.json` 排除。Analytics、README、Atlas 與未來衍生分析共用同一份 policy。
