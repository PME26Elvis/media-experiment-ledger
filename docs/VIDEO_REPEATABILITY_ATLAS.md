# 影片 Prompt Repeatability Atlas 規劃

## 目的

影片版 Prompt Repeatability Atlas 用來回答與圖片版相同的問題：當相同 `prompt_id`、相同模型與相同會影響生成結果的設定，在不同時間／run 重複執行時，生成影片的內容、構圖、動態、時間一致性與 artifact 會如何變化？

這項功能應直接整合進既有的全資料 Atlas workflow，而不是建立另一套 release enumeration、state 或 cache。圖片與影片都來自相同的 immutable `media-exp-*` Releases，也應發布到同一個 `media-analysis-all-<fingerprint>-vN` companion Release。

## 設計原則

1. **同一個 corpus snapshot**：圖片與影片共用所有已發布 `media-exp-*` Releases、日期範圍與 dataset fingerprint。
2. **媒體類型隔離**：image cohort 與 video cohort 永遠不混合；media type 是 cohort identity 的一部分。
3. **原始影片保持 immutable**：Atlas 不修改 raw Release，也不需要把原始影片複製到 derived Release；sidecar 保留來源 asset、member、SHA-256 與 Release URL。
4. **GIF 只作為快速比較 preview**：完整證據仍是 raw video 與 machine-readable metadata。
5. **ZIP-only assets**：GIF、keyframe sheet、JSON、HTML 都包在 Atlas ZIP 內；只有 Release Notes 精選 GIF 會像圖片 previews 一樣放在版本化 repo 路徑。
6. **不使用 cache／state**：每次全量掃描與驗證；相同 immutable corpus 由 dataset fingerprint 判斷是否重用已發布 Atlas。
7. **FFmpeg 是標準 renderer**：GitHub Actions 的 CPU 足以處理目前少量影片；workflow 安裝 `ffmpeg`／`ffprobe` 後直接執行。

## Cohort Identity

影片 cohort 建議包含：

1. `prompt_id`；
2. `media_type = video`；
3. provider 與 model；
4. model revision／version（若 metadata 有提供）；
5. normalized generation settings：
   - width／height／aspect ratio；
   - requested duration；
   - requested FPS；
   - seed；
   - guidance／CFG；
   - sampler／scheduler；
   - negative prompt；
   - motion／camera／quality mode；
   - input image、reference video 或 conditioning media 的 SHA-256；
6. 其他會實質影響輸出的 request payload 欄位。

Prompt text 不重複進 settings fingerprint，因為 `prompt_id` 是 canonical identity；純 transport 欄位，例如 response format、download URL、request ID，不應改變 cohort。

## 影片樣本驗證

Metadata row 只有在下列條件全部成立時才能成為可比較樣本：

- event 是 `video_completed`；
- 存在 `prompt_id`；
- 對應 `run_*-videos*.zip` 中存在相同 prompt stem 的影片 member；
- `ffprobe` 能正常讀取 container；
- 至少存在一條可解碼 video stream；
- duration、width、height、frame rate 能取得合理值；
- FFmpeg 能實際 decode 開頭、中間與結尾附近的 frames；
- 檔案 SHA-256 驗證完成。

建議 sidecar 記錄：

```json
{
  "duration_seconds": 6.02,
  "width": 1280,
  "height": 720,
  "average_frame_rate": 24.0,
  "codec": "h264",
  "pixel_format": "yuv420p",
  "container": "mp4",
  "has_audio": false,
  "sha256": "...",
  "source_tag": "media-exp-...",
  "source_archive": "run_...-videos.zip",
  "source_member": "media/videos/v0001.mp4"
}
```

## 去除重複

第一階段使用與圖片相同的 exact SHA-256 去重：完全相同 bytes 只保留一份證據。

不建議第一版直接使用 perceptual video hash 去除「看起來很像」的影片，因為：

- codec／bitrate 不同可能造成 bytes 不同，但內容相同；
- 反過來，細微 motion artifact 可能正是 Atlas 想觀察的資訊；
- 自動 perceptual threshold 容易錯誤刪除有價值樣本。

未來可把 perceptual similarity 當作額外 metric，而不是 hard deduplication。

## Primary GIF：Release Notes 快速預覽

### 樣本數與版面

| 可用唯一影片 | Primary preview |
|---:|---|
| 0–1 | 不建立 repeatability preview |
| 2 | `1 × 2` 同步播放 |
| 3 | `2 × 2`，第四格顯示樣本不足 |
| 4+ | 使用 earliest、history anchors、latest 的 `2 × 2` |

### 時間正規化

為確保視覺比較公平：

- 每格從影片時間 `t=0` 開始；
- preview 預設最多 6 秒；
- 較短影片使用 `tpad=stop_mode=clone` 停留在最後一幀，不循環原片來假裝有更多 motion；
- 較長影片截取前 6 秒；
- 每格採相同 relative timestamp 同步播放。

第一版不使用「自動找最精彩片段」，因為不同影片若選到不同時間窗，會降低 repeatability 比較的可解釋性。

### 尺寸與 GIF 設定

建議預設：

- 每格 logical canvas：`480 × 270`，使用 contain／letterbox，不裁切；
- 2 × 2 總畫布：`960 × 540`；
- 6 FPS；
- 最長 6 秒；
- 128 或 256 色 palette；
- 無限循環；
- 目標檔案約 5–20 MB；
- 超過設定上限時依序降低 FPS、色數、寬度，不縮短低於 3 秒。

建議 FFmpeg filter graph：

```text
每個 input
  → trim / setpts
  → fps=6
  → scale=480:270:force_original_aspect_ratio=decrease
  → pad=480:270:(ow-iw)/2:(oh-ih)/2
  → drawtext label
全部 inputs
  → xstack
  → split
  → palettegen
  → paletteuse
  → preview.gif
```

為避免系統字型差異，label 可沿用 workflow 安裝的 Noto Sans CJK；若 FFmpeg drawtext 的字型支援不穩定，也可先用 Pillow 產生 label overlay PNG，再由 FFmpeg 疊加。

## Extended 與完整輸出

由於目前影片 prompt 數量少，第一版可以比圖片更完整：

### Extended GIF

- 五個以上影片時，最多選 8 個時間分位樣本；
- 4 × 2 grid；
- 為控制檔案大小，每格可降到 `320 × 180`、4 FPS、4 秒；
- 主要用於 bundle 內離線比較，不必全部放進 Release Notes。

### Keyframe Contact Sheet

每個影片至少抽取：

- 0%；
- 25%；
- 50%；
- 75%；
- 接近結尾。

把同一影片的 keyframes 排成一列，不同 runs 排成多列，可在靜態圖中檢查：

- 主體是否漂移；
- 場景／物件 continuity；
- 幾何或肢體 artifact；
- 鏡頭運動差異；
- 結尾崩壞。

### Full Index

所有可用唯一影片都進 sidecar 與 HTML index。Derived bundle 不重複儲存原始影片本體，而是提供來源 Release／asset／member、hash 與可下載連結；必要時可加一個 `include_original_videos` 的手動選項，但不作預設。

## 與圖片流程的整合方式

建議擴充既有模組，而不是建立平行 workflow：

```text
release_rows()
  → download image/video metadata
  → build image cohorts + video cohorts
  → selective image ZIP download + selective video ZIP download
  → Pillow image renderer + FFmpeg video renderer
  → shared report/index/package publication
  → one companion Release
  → one README/statistics refresh
```

建議檔案結構：

- `tools/prompt_atlas_data.py`
  - 增加 video metadata collection、archive/member matching、ffprobe validation。
- `tools/prompt_atlas_core.py`
  - 增加 `VideoSample` 或共用 base sample schema，以及 video cohort fingerprint。
- `tools/prompt_atlas_video.py`
  - 新增 FFmpeg／ffprobe command、GIF、keyframe sheet、video sidecar renderer。
- `tools/prompt_atlas_build.py`
  - 同一份 report 同時包含 `image_entries`、`video_entries` 與總數。
- `tools/prompt_atlas_packages.py`
  - 圖片維持每 15 prompts 一包；影片 prompt 數量少時可全部放在一個 `video-atlas-bundle-001.zip`，超過 15 prompts 後使用相同分包政策。
- `.github/workflows/visual-analysis.yml`
  - 安裝 `ffmpeg`，保持同一個 all-data job 與相同 publication sequence。

## Release Asset 與目錄規格

同一個 analysis Release 建議包含：

```text
prompt-atlas-bundle-001-i0001-to-i0015.zip
...
video-atlas-bundle-001-v0001-to-v0015.zip
atlas-metadata.zip
offline-gallery.zip
prompt-repeatability-atlas-complete-part001.zip
```

Video bundle 內：

```text
video-primary/
  atlas-v0001-<cohort>-n4.gif
video-extended/
  atlas-v0001-<cohort>-extended-n8.gif
video-keyframes/
  atlas-v0001-<cohort>-keyframes.jpg
video-sidecars/
  atlas-v0001-<cohort>.json
bundle-manifests/
  video-bundle-001.json
```

所有 Release assets 仍為 ZIP。Release Notes 精選 GIF 則提交到：

```text
web/public/data/visual-analysis/video-previews/<fingerprint>/<batch-id>/
```

再透過 raw repository URL 嵌入 Notes。

## README 與 Statistics

README 總表已經從正式 `media-exp-*` manifests 同時計算圖片與影片數量，因此影片 Atlas 上線後不需要另一套統計來源。

Atlas 歷史表應從每個 analysis report 的 `release_tags` 計算該版本當時的圖片／影片總量，避免把之後新增的資料倒灌進舊 Atlas row。

未來 report 建議明確新增：

```json
{
  "comparable_image_prompts": 80,
  "comparable_video_prompts": 4,
  "verified_unique_images": 420,
  "verified_unique_videos": 18
}
```

## GitHub Actions 資源與可靠性

- 使用 `sudo apt-get install --no-install-recommends ffmpeg`。
- 不設定 repository-specific 90 分鐘 timeout。
- 不使用 cache 或 persistent processing state。
- 每次都重新從 immutable Releases 建立 corpus。
- FFmpeg command 必須有明確錯誤輸出與單檔 timeout，避免損壞影片讓整個 process 永久卡住。
- 每個 GIF 完成後使用 `ffprobe` 或 ImageMagick（若已安裝）確認 frame count 與尺寸；不額外引入大型依賴時可由 Pillow 驗證 GIF frames。
- 只有全部 ZIP assets、Notes previews 與 metadata 驗證成功後才把 draft publish。

## 分階段實作

### Milestone V1：驗證與 Primary GIF

- 收集／驗證 video samples；
- 建立 controlled cohorts；
- 2／3／4-sample primary GIF；
- video sidecars；
- 少量 GIF Notes previews；
- 與圖片 Atlas 同 Release。

### Milestone V2：Extended 與 Keyframes

- 最多 8 樣本 extended GIF；
- 所有影片 keyframe contact sheets；
- Visual Lab 影片 filter 與 GIF lazy loading。

### Milestone V3：品質 Metrics

只作輔助指標，不取代人工觀看：

- duration／FPS／resolution consistency；
- scene-cut count；
- optical-flow motion magnitude；
- freeze-frame ratio；
- perceptual similarity timeline；
- black-frame／decode-error detection。

## 驗收條件

影片 Atlas 第一版完成時應滿足：

1. 同一個全資料 workflow 同時發布 image 與 video atlas。
2. 不讀取 `media-input-*` snapshot 作為實驗資料。
3. 每個 video sample 都經過 `ffprobe` 與實際 decode。
4. 相同 bytes 使用 SHA-256 去重。
5. Primary GIF 使用同步時間與 contain fit。
6. Release Notes 至少能直接顯示一個可點擊 GIF preview（有 eligible cohort 時）。
7. Release assets 仍全部是 ZIP。
8. Report、README statistics 與 Visual Lab 都能區分圖片與影片 prompt 數。
9. 損壞影片會留下清楚的 missing／validation record，不會被當成成功樣本。
10. 全部測試、Astro build 與 site validator 通過。
