# Codespaces 發布指南

[English version](CODESPACES_PUBLISHING.en.md)

## 一次性準備

在 repository 頁面選擇 **Code → Codespaces → Create codespace on main**。Codespaces 會提供 Python、Git，以及已針對目前 repository 驗證的 GitHub CLI。

Repo 已忽略原始 results、上傳 archives、解壓與 release staging 目錄、logs、state、secrets 等本地檔案。

## 建議操作：一個多日期 Archive

### 1. 上傳

在本機建立 `results.zip` 並只上傳這一個檔案。它可包含多個 `YYYY-MM-DD` 目錄，每個日期也可有多個 runs。支援的結構請見 [ZIP 輸入與 snapshot 工作流程](INPUT_ARCHIVE_WORKFLOW.md)。

若 Codespace 較舊，先更新 tracked code：

```bash
git pull --ff-only
```

### 2. 發布完整批次

```bash
python tools/publish_from_archive.py results.zip
```

Wrapper 會驗證並安全解壓 archive，接著呼叫共同 publisher。共同 publisher 會：

1. 掃描所有日期目錄；
2. 載入每個日期的 primary／supplemental manifests；
3. 跳過相同 `run_id` 與 digest；
4. 阻止相同 `run_id` 對應到不同內容；
5. 使用 ZIP store mode 分別打包圖片與影片；
6. 在接近 1.8 GiB 時切分媒體；
7. 發布獨立 JSONL／manifest metadata；
8. 依 archive 內容建立所有必要的 immutable 日期 Releases；
9. 等待全部日期處理完畢；
10. 對**目前所有已發布的 experiment data** dispatch 一次 Prompt Repeatability Atlas；
11. 整批成功後清理暫存 extraction 與 packages。

因此 Atlas 對齊的是完整上傳批次，而不是處理途中任意一個日期 Release。

### 3. 檢查結果

開啟 **Releases**，確認：

- 預期的 `media-exp-*` primary／supplemental tags 都已建立；
- 有一個新的或可重用的 `media-analysis-all-<fingerprint>-vN` Atlas；
- Analysis Notes 內有少量 inline Atlas previews；
- Atlas assets 全部是 ZIP；圖片 Atlas 每個 bundle 最多包含 15 個 prompt IDs；
- 完整 multipart packages 都存在。

### 4. 清理

確認 Releases 後即可刪除 Codespace，已發布資料不會被刪除。

## 立即儲存的備援方式

若希望先確保大檔已進入 Release storage：

```bash
python tools/input_snapshot.py publish results.zip
```

之後可從 **Actions → Promote input snapshot** 執行，或在 Codespaces：

```bash
python tools/input_snapshot.py promote --tag latest
```

Promotion 會重建原始 archive 並呼叫相同共同 publisher，因此最終的全資料 Atlas 行為完全一致。

`media-input-*` snapshot 只作為傳輸／儲存紀錄；README 統計與 Atlas 都會排除它，直到 promote 產生正式 `media-exp-*` Releases。

## 直接資料夾模式

若已有完整資料夾：

```bash
python tools/publish_results.py --source results
```

可安全包含已發布日期。遠端 manifests 會判斷每個 run 是新資料、完全相同或衝突。成功執行後，會在全部日期 Releases 完成時 dispatch 一次全資料 Atlas。

## 常用 Archive 選項

只驗證：

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

指定日期：

```bash
python tools/publish_from_archive.py results.zip \
  --date 2026-06-29 \
  --date 2026-06-30
```

保留解壓結果：

```bash
python tools/publish_from_archive.py results.zip --keep-extracted
```

降低媒體 part 上限：

```bash
python tools/publish_from_archive.py results.zip --max-part-gib 1.5
```

只有特殊維護才跳過 Atlas：

```bash
python tools/publish_results.py \
  --source results \
  --skip-atlas-dispatch
```

## Atlas 執行政策

- **主要 trigger**：共同 publisher 的完整批次成功後，只 dispatch 一次。
- **手動 trigger**：在 **Publish Prompt Repeatability Atlas** 使用可選的 `force`。
- **程式／設定 trigger**：Atlas implementation 在 `main` 更新時強制建立新版本。
- **資料範圍**：每次都掃描全部已發布 `media-exp-*` Releases。
- **Cache／state**：不使用。
- **Repo timeout**：沒有額外 90 分鐘限制。
- **Assets**：全部為 ZIP；圖片 bundle 每包最多 15 個 prompt IDs；Notes previews 使用版本化 repo 路徑。
- **README**：每次 Atlas 成功後，全量掃描正式 experiment 與 Atlas Releases，重建中英統計與歷史表。
