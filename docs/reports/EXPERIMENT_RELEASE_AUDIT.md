# Experiment Release Audit

> 此報告由 GitHub Actions 全量重建，不使用持久化 state 或 cache。

- Generated at (UTC): `2026-07-20T13:59:53+00:00`
- Repository: `PME26Elvis/media-experiment-ledger`
- Releases audited: **9**
- Canonical runs: **11**
- Quarantined historical runs: **2**
- Canonical archived images: **387**
- Canonical archived videos: **33**

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

## Findings

- `media-exp-2026-06-29` / `run_20260629_232751` · **warning** · `empty_run` · Run contains no source files
- `media-exp-2026-06-29` / `run_test` · **warning** · `completed_events_vs_manifest_media` · completed events={'images': 550, 'videos': 7}, manifest media files={'images': 0, 'videos': 0}

## Quarantine policy

歷史 Release assets 維持不變；已確認無效的 run 由 `config/release-quarantine.json` 排除。Analytics、README、Atlas 與未來衍生分析共用同一份 policy。
