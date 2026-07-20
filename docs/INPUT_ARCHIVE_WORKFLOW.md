# ZIP 輸入與 Snapshot 工作流程

[English version](INPUT_ARCHIVE_WORKFLOW.en.md)

Codespaces 的瀏覽器檔案總管在大量媒體檔案下可能不穩定，因此建議上傳單一 `results.zip`。直接使用 `results/` 仍完整支援；若希望先把大檔安全存進 GitHub Releases、之後再處理，也可使用 input snapshot 流程。

## 所有正式路徑共用同一個 Publisher

```text
多日期 results.zip ─┐
直接 results/ ───────┼─→ publish_results.py
media-input promote ─┘     ├─ 每個新日期一個 immutable Release
                             ├─ 已有日期的新 run 建立 supplement
                             └─ 整批成功後只 dispatch 一次全資料 Atlas
```

Atlas 不會對批次中間產生的每個日期 Release 各跑一次，而是等整批完成後，掃描目前所有已發布的 `media-exp-*` 資料。

## 主要方式：上傳一個 ZIP，發布所有日期

可使用以下結構：

```text
results.zip
  results/
    2026-06-29/
      run_20260629_120000/
        outputs.jsonl
        errors.jsonl
        media/images/...
        media/videos/...
    2026-06-30/
      run_20260630_120000/...
```

也可直接以日期資料夾為根：

```text
results.zip
  2026-06-29/
    run_20260629_120000/...
  2026-06-30/
    run_20260630_120000/...
```

允許額外一層 wrapper directory，並支援超過 2 GiB 的 ZIP64 archive。

1. 從 `main` 建立或開啟 Codespace。
2. 上傳 `results.zip`。
3. 若 Codespace 建立時間早於 repo 最近更新，先執行：

```bash
git pull --ff-only
```

4. 發布所有新日期與 run：

```bash
python tools/publish_from_archive.py results.zip
```

這個指令會：

- 拒絕不安全或未完整上傳的 ZIP members；
- 檢查檔案在 inspection／extraction 期間是否變動；
- 估算需要的可用磁碟空間；
- 暫時解壓至 `.archive-imports/`；
- 自動判斷 `results/`、直接日期資料夾或 wrapper 結構；
- 呼叫使用 SHA-256 的 duplicate-aware 日期 publisher；
- 建立所有需要的 primary／supplemental `media-exp-*` Releases；
- 只有全部日期成功後才 dispatch 一次全資料 Atlas；
- 清理暫存 extraction／package 檔案；
- 保留原始 `results.zip`。

只驗證、不發布：

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

只處理指定日期：

```bash
python tools/publish_from_archive.py results.zip \
  --date 2026-06-29 \
  --date 2026-06-30
```

保留解壓結果供檢查：

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

只有特殊維護情境才應使用內部的 `--skip-atlas-dispatch`；一般上傳應保留自動全資料重建。

## 瀏覽器傳輸的最後備援：分割普通檔案

若瀏覽器無法傳送單一 2+ GiB ZIP，可在 WSL 先分割：

```bash
sha256sum results.zip > results.zip.sha256
split -b 1500M -d -a 3 results.zip results.zip.upload-part-
```

把 parts 與 checksum 分別上傳後，在 Codespaces 重組：

```bash
cat results.zip.upload-part-* > results.zip
sha256sum -c results.zip.sha256
python tools/publish_from_archive.py results.zip
```

這只改變傳輸方式；重組後的 archive、日期 Releases 與 Atlas trigger 都與主要流程相同。

## 快速儲存：先發布 Input Snapshot

當優先目標是先把已上傳完成的大檔放進 Release storage：

```bash
python tools/input_snapshot.py publish results.zip
```

程式會驗證 ZIP central directory，把來源切成低於 1.8 GiB 的 byte-exact parts，計算整體與每一 part 的 SHA-256，並建立例如：

```text
Tag: media-input-2026-07-15-<sha12>
Assets:
  results.zip.part001
  results.zip.part002
  input-snapshot-manifest.json
```

來源不會被重新壓縮。`media-input-*` 是傳輸／暫存記錄，不會被 README 統計或 Atlas 當成正式資料；只有 promote 後建立的 `media-exp-*` Releases 才會計入。

只測試打包：

```bash
python tools/input_snapshot.py publish results.zip --dry-run
```

## 之後 Promote Snapshot

### GitHub Actions

1. 開啟 **Actions**。
2. 選擇 **Promote input snapshot**。
3. 執行 workflow。
4. `snapshot_tag` 可保留 `latest`，或指定精確 `media-input-*` tag。
5. 關閉 `dry_run` 才會建立正式 experiment Releases。

Workflow 會下載並驗證所有 parts、byte-for-byte 重建原 ZIP、安全解壓，最後呼叫同一個共同 publisher。整個多日期批次成功後只 dispatch 一次全資料 Atlas；analytics 另外由 promotion workflow 更新。

### Codespaces

Promote 最新 snapshot：

```bash
python tools/input_snapshot.py promote
```

指定 tag：

```bash
python tools/input_snapshot.py promote \
  --tag media-input-2026-07-15-<real-sha-prefix>
```

只還原、不發布：

```bash
python tools/input_snapshot.py restore \
  --output restored-results.zip
```

## 直接使用 Results 資料夾

```bash
python tools/publish_results.py --source results
```

這是正式支援的第一級路徑。它會掃描所有 `YYYY-MM-DD` 目錄、發布新 runs，並在無失敗的整批完成後 dispatch 一次全資料 Atlas。

## 重複與衝突規則

| 本地狀態 | 遠端狀態 | 結果 |
|---|---|---|
| 新 `run_id` | 不存在 | 發布到本批次日期 Release。 |
| 相同 `run_id`、相同 digest | 已存在 | 安全跳過。 |
| 相同 `run_id`、不同 digest | 已存在 | 該日期失敗，且不 dispatch 最終 Atlas。 |
| 已發布日期新增 run | primary 已存在 | 建立 `-sNN` supplement。 |

單一日期失敗不會阻止其他日期先完成評估，但 Atlas 會等待整批無失敗，避免把部分完成的資料誤標成最終 corpus。

## 清理

以下路徑皆由 `.gitignore` 排除：

```text
results/
results*.zip
results.zip.*
.archive-imports/
.input-staging/
.input-download/
.release-staging/
visual-analysis/output/
```

確認 Releases 正常後即可刪除 Codespace，不會影響已發布 assets。
