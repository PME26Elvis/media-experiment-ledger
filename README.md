# Media Experiment Ledger

**繁體中文** | [English](README.en.md)

這是一個以 GitHub Releases 為資料層的媒體生成實驗平台，用來管理圖片／影片 prompt、不可變更的實驗資料、可重建分析、圖片與影片 Prompt Repeatability Atlas、預測模型與 GitHub Pages 儀表板，同時避免把大型原始結果直接提交進 Git history。

## 即時統計

<!-- AUTO:LEDGER_STATS:START -->
> 此區塊由 GitHub Actions 全量重建；只統計正式 `media-exp-*` Releases，`media-input-*` snapshot 不會重複計入。

| 統計項目 | 數值 |
|---|---:|
| 正式 Experiment Releases | 9 |
| 實驗日期範圍 | 2026-06-29 → 2026-07-13 |
| 圖片總數 | 937 |
| 影片總數 | 40 |
| 最新 Prompt Repeatability Atlas | [media-analysis-all-f5fdcae2c78b-v1](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-f5fdcae2c78b-v1) |
<!-- AUTO:LEDGER_STATS:END -->

## Prompt Repeatability Atlas 歷史

<!-- AUTO:ATLAS_HISTORY:START -->
> 每次 Atlas workflow 都重新掃描全部 Atlas Releases 並重建此表，不依賴增量狀態。

| 發布日期 | 圖譜類型 | 資料範圍 | 圖片 | 影片 | 可比較 Prompt | Release |
|---|---|---|---:|---:|---:|---|
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-f5fdcae2c78b-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-f5fdcae2c78b-v1) |
| 2026-07-19 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-8b850904b063-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-8b850904b063-v1) |
| 2026-07-19 | 歷史單次圖譜 | 2026-07-13 | 3 | 1 | 3 | [`media-analysis-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-2026-07-13-v1) |
<!-- AUTO:ATLAS_HISTORY:END -->

## 核心能力

- 建議在 Codespaces 上傳一個可包含多日結果的 `results.zip`，同時保留直接使用 `results/` 的方式。
- 每個實驗日期建立一個不可變更的 `media-exp-*` Release；已存在日期若新增真正不同的 run，則建立 supplemental Release。
- 圖片與影片分開包成 ZIP，並在接近 GitHub 單一 asset 2 GiB 上限前自動切分。
- 保留獨立 JSONL metadata 與 SHA-256 manifest，讓 analytics 不必下載全部媒體。
- 自動跳過已發布且內容相同的 run；相同 `run_id` 若內容不同則阻止發布。
- 可先把大檔存成可驗證的 `media-input-*` snapshot，之後再 promote 成正式實驗 Releases。
- 每次完整發布批次成功後，使用**目前所有正式實驗資料**重建一個全域圖片＋影片 Prompt Repeatability Atlas。
- 圖片與影片 Atlas 都以**每 15 個 prompt IDs 一個 ZIP bundle**發布。
- 圖片使用靜態 comparison cards；影片使用 FFmpeg 驗證、同步 GIF previews 與完整 keyframe sheets。
- 透過 GitHub Pages 提供 analytics、forecast、可搜尋的 image/video Visual Lab、架構圖與技術說明。

## 支援的上傳／發布方式

所有正式路徑最後都匯入 `tools/publish_results.py`，因此日期切分、重複檢查、manifest 與最終 Atlas trigger 都使用同一套邏輯。

| 使用情境 | 指令或 workflow | 結果 |
|---|---|---|
| 建議的瀏覽器上傳 | `python tools/publish_from_archive.py results.zip` | 安全解壓一個多日期 ZIP，發布所有新日期／run。 |
| 已有完整資料夾 | `python tools/publish_results.py --source results` | 直接處理 `results/YYYY-MM-DD/run_*`。 |
| 先儲存、之後再處理 | `python tools/input_snapshot.py publish results.zip` | 建立 byte-exact `media-input-*` snapshot。 |
| Promote snapshot | `python tools/input_snapshot.py promote` 或 **Promote input snapshot** Action | 重建原 ZIP，走同一個正式日期 publisher。 |
| 瀏覽器無法上傳 2+ GiB ZIP | 先分割、逐檔上傳、重組，再執行 `publish_from_archive.py` | 只改變傳輸方式，最終 Releases 完全相同。 |

一個 archive 可以包含很多日期。共同 publisher 會先建立所有需要的 primary／supplemental `media-exp-*` Releases，只有整批全部成功後才 dispatch **一次**全資料 Atlas。

詳細說明：

- [ZIP 輸入與 snapshot 工作流程](docs/INPUT_ARCHIVE_WORKFLOW.md)
- [Codespaces 發布指南](docs/CODESPACES_PUBLISHING.md)

## 最快發布方式

1. 在 repo 建立或開啟 `main` 的 Codespace。
2. 上傳 `results.zip`。
3. 執行：

```bash
python tools/publish_from_archive.py results.zip
```

支援 top-level `results/`、直接日期資料夾，以及額外一層 wrapper directory；ZIP64 大檔可正常使用。

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

## 先儲存、之後再處理

```bash
python tools/input_snapshot.py publish results.zip
python tools/input_snapshot.py promote --tag latest
```

`media-input-*` 只是一種傳輸／暫存紀錄，不是正式實驗資料。因此 README 統計與 Atlas 都不讀取 snapshot；只有 promote 後建立的 `media-exp-*` Releases 才會被統計與分析。

## 正式 Experiment Release 結構

```text
Tag: media-exp-2026-06-29

run_20260629_120000-images.zip
run_20260629_120000-videos.zip
run_20260629_120000-outputs.jsonl
run_20260629_120000-errors.jsonl
manifest-2026-06-29.json
```

已發布日期若新增新的 run，會建立例如 `media-exp-2026-06-29-s01` 的 immutable supplement，既有 Release 不會被覆寫。

## 全資料 Prompt Repeatability Atlas

同一個 companion Release 同時處理圖片與影片，但兩種 media 永遠不混入同一 cohort。

### 圖片 Atlas

對相同 `prompt_id`、model 與 appearance-relevant settings：

- primary comparison card；
- 最多 16 個時間分位樣本的 extended overview；
- 所有已驗證、SHA-256 去除完全重複後樣本的 full contact sheets；
- JSON sidecars 與來源索引；
- 每 15 個 image prompt IDs 一個 deterministic ZIP bundle。

### 影片 Atlas

對相同 `prompt_id`、model 與非隨機 generation settings：

- 以 `ffprobe` 驗證 container、stream、duration、尺寸、FPS 與 codec；
- 用 FFmpeg 實際 decode 開頭、中間與結尾，排除壞影片；
- 2／3／4-run synchronized GIF primary preview；
- 短片停在最後一幀，所有 tiles 從 `t=0` 同步，使用 contain／letterbox、不裁切；
- 所有唯一影片都產生 10%／50%／90% keyframe sheets；
- seed 保存在 sidecar 作為觀察證據，但不放進 cohort key；
- 每 15 個 video prompt IDs 一個 deterministic ZIP bundle。

Atlas Release tag 使用：

```text
media-analysis-all-<dataset-fingerprint>-vN
```

Release Notes 預設精選 4 張圖片 JPEG 與 2 個影片 GIF。所有 Release Assets 本身維持 ZIP-only；版本化 repo preview 路徑用於 Notes 與 Visual Lab 內嵌顯示。

相關文件：

- [圖片與共用 Atlas 規格](docs/PROMPT_REPEATABILITY_ATLAS.md)
- [影片 Prompt Repeatability Atlas](docs/VIDEO_REPEATABILITY_ATLAS.md)

## README 自動更新

每次 Atlas workflow 成功時會：

1. 重新掃描全部正式 `media-exp-*` Releases；
2. 從 manifests 聚合圖片與影片數量，並排除 `media-input-*` snapshots；
3. 重新掃描全部已發布 `media-analysis-*` Releases；
4. 全量重建中英文 README 的統計與 Atlas 歷史區塊；
5. 把 README、Visual Lab index 與 JPEG/GIF Notes previews 一起 commit 回 `main`。

這個流程不使用增量 state 或 cache。

## Analytics、Forecast 與 Pages

```text
多日期上傳批次
  → immutable 日期 experiment Releases
  → 一個全資料 image + video Prompt Repeatability Atlas
  → canonical analytics 與 reports
  → ensemble forecasts
  → Astro / Starlight build
  → GitHub Pages deployment
```

網站主要頁面：

- **Overview**：整體狀態與導航。
- **Analytics**：產量、成功率、類別、錯誤、月份與 run ledger。
- **Visual Lab**：圖片／影片 cohort 搜尋、media filter、GIF preview 與 bundle ZIP 下載。
- **Forecast Lab**：下一個 active day 與下一月份的機率預測。
- **System Atlas**：工具流程與 Mermaid 架構圖。
- **Frontend Stack**：前端框架、路由、圖表與部署架構。

## 文件索引

- [ZIP 輸入與 snapshot 工作流程](docs/INPUT_ARCHIVE_WORKFLOW.md)
- [Codespaces 發布指南](docs/CODESPACES_PUBLISHING.md)
- [圖片與共用 Prompt Repeatability Atlas](docs/PROMPT_REPEATABILITY_ATLAS.md)
- [影片 Prompt Repeatability Atlas](docs/VIDEO_REPEATABILITY_ATLAS.md)
- [English README](README.en.md)

## 開發與驗證

```bash
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt
sudo apt-get install -y --no-install-recommends ffmpeg
python -m compileall tools tests
python -m unittest discover -s tests -v
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```
