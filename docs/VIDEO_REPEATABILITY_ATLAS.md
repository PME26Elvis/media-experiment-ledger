# 影片 Prompt Repeatability Atlas

## 狀態

影片 Prompt Repeatability Atlas 已整合進正式的全資料 Atlas pipeline。圖片與影片共用：

- 所有已發布的 `media-exp-*` Releases；
- dataset fingerprint；
- batch completion trigger；
- 同一個 `media-analysis-all-<fingerprint>-vN` companion Release；
- ZIP-only asset contract；
- Visual Lab index；
- README statistics 與 Atlas history 更新。

主要實作位於：

- `tools/prompt_atlas_video.py`：video metadata、ZIP extraction、FFprobe validation、GIF 與 keyframe rendering；
- `tools/prompt_atlas_build.py`：image/video 全資料 build；
- `tools/prompt_atlas_packages.py`：image/video 15-prompt bundles 與 complete packages；
- `tools/prompt_atlas_publish.py`：同一份 Release Notes 的 JPEG/GIF highlights；
- `.github/workflows/visual-analysis.yml`：安裝 FFmpeg 並執行 production build；
- `tests/test_prompt_atlas_video.py`：以真實合成 MP4 驗證 FFmpeg pipeline。

## 目的

影片 Atlas 回答與圖片 Atlas 相同的問題：相同 prompt、模型及非隨機生成設定在不同日期與 run 重複執行時，輸出的構圖、內容、動態、時間一致性與 artifacts 會如何變化？

Derived Atlas 不修改或複製 raw experiment Release。原始 MP4 仍保存在 immutable `media-exp-*` video ZIP；Atlas 保存來源 tag、asset、member、SHA-256、codec、duration、FPS 與可視化證據。

## Cohort identity

影片 cohort 使用：

1. `media_type = video`；
2. `prompt_id`；
3. model；
4. normalized request settings，例如：
   - `num_frames`；
   - requested frame rate；
   - width／height；
   - negative prompt；
   - motion、camera、quality 或 conditioning settings；
   - model revision（若 metadata 提供）。

### Seed 的處理

Agnes harvester 每次執行都會產生新的 random seed。Seed 會完整保留在每個 sample sidecar 中，但**不放進 cohort identity**。

若把 seed 放入 cohort key，每一次真實 run 都會成為 singleton，無法形成 repeatability comparison。Atlas 的目的正是比較同一固定 prompt/config 在不同隨機抽樣下的變化；因此 seed 是觀察變數，不是控制分組鍵。

Prompt text 不重複進 settings fingerprint，因為 `prompt_id` 是 canonical prompt identity。Transport-only 欄位也不參與 cohort identity。

## 樣本驗證

Metadata row 只有在以下條件全部成立時才能成為影片證據：

- event 是 `video_completed`；
- 有 `prompt_id`；
- 對應 `run_*-videos*.zip` 存在 `media/videos/<prompt_id>_<task>.mp4` 或同 stem member；
- `ffprobe` 找到至少一條 video stream；
- duration、width、height 為合理正值；
- FFmpeg 能實際 decode 開頭、中間與結尾附近 frame；
- 完成 SHA-256。

支援的 container suffix：

```text
.mp4 .mov .m4v .webm .mkv .avi
```

無法 probe、decode 或對應 source member 的 metadata 不會出現在 Atlas。

## 去除重複

使用 exact SHA-256 去除完全相同 bytes。若同一影片透過重複 Release 或 supplement 再次出現，只保留一份證據，並在衝突時優先保留最新來源 Release 的 metadata。

目前不使用 perceptual video hash 做 hard deduplication。Codec 或 bitrate 差異、細微 motion artifacts 都可能是有價值的 repeatability 證據。

## Primary GIF

Primary selection 與圖片版採相同時間錨點策略：

| 唯一可用影片 | 版面 |
|---:|---|
| 0–1 | 不建立 repeatability entry |
| 2 | `1 × 2` |
| 3 | `2 × 2`，第四格顯示樣本不足 |
| 4+ | earliest、mid-history、latest prior、latest 的 `2 × 2` |

### 時間正規化

- 全部 tiles 從 `t=0` 同步播放；
- 預設最長 6 秒；
- 長影片取前 6 秒；
- 短影片使用 FFmpeg `tpad=stop_mode=clone` 停在最後一幀；
- 不循環短片來製造額外 motion；
- contain／letterbox，不裁切；
- 預設 6 FPS、128 色 palette、無限循環。

預設 tile 為 `480 × 270`。標題、cohort、sample role、Release、run、尺寸及 duration 由 Pillow 疊加，因此不依賴 FFmpeg drawtext 的字型環境。

## Extended GIF

當一個 video cohort 至少有 5 個唯一樣本時，Atlas 會建立 extended GIF：

- 最多 8 個 temporal quantiles；
- 最多 4 欄；
- 每格預設 `320 × 180`；
- 使用相同同步、padding 與 contain policy。

Extended GIF 主要放在 video bundle，不一定出現在 Release Notes。

## 完整 keyframe evidence

所有 verified byte-unique videos 都進入完整 keyframe pages，不是抽樣。

每個影片抽取：

- 10%；
- 50%；
- 90%。

三個時間點排列在同一 tile；每頁最多 16 個影片。這讓靜態檢查可以快速辨識：

- subject drift；
- scene／object continuity；
- geometry 或 limb artifacts；
- camera motion 差異；
- 結尾崩壞。

原始影片不重複放入 derived bundle；sidecar 指回 raw Release asset/member。

## Sidecar schema

每個 cohort sidecar 包含：

```json
{
  "media_type": "video",
  "prompt_id": "v0001",
  "model": "agnes-video-v2.0",
  "cohort_id": "...",
  "sample_count": 4,
  "rendering": {
    "preview_format": "GIF",
    "preview_seconds": 6,
    "preview_fps": 6,
    "fit": "contain/letterbox",
    "keyframes": [0.1, 0.5, 0.9]
  },
  "all_samples": [
    {
      "seed": 123,
      "duration_seconds": 10.04,
      "width": 1280,
      "height": 720,
      "average_frame_rate": 24.0,
      "codec": "h264",
      "pixel_format": "yuv420p",
      "container": "mov,mp4,m4a,3gp,3g2,mj2",
      "has_audio": false,
      "sha256": "...",
      "archive_name": "run_...-videos.zip",
      "archive_member": "media/videos/v0001_task.mp4"
    }
  ]
}
```

## Release assets

所有 companion Release assets 仍是 ZIP：

```text
prompt-atlas-bundle-001-i0001-to-i0015.zip
video-atlas-bundle-001-v0001-to-v0015.zip
atlas-metadata.zip
offline-gallery.zip
prompt-repeatability-atlas-complete-part001.zip
```

Video bundle 內部：

```text
video/primary/*.gif
video/extended/*.gif
video/keyframes/<prompt>-<cohort>/page-*.jpg
video/sidecars/*.json
video-bundle-manifests/video-prompt-bundle-001.json
```

每包最多 15 個 video prompt IDs；同一 prompt 的多個 model/settings cohorts 不會被拆到不同 bundle。

`atlas-metadata.zip` 同時包含 image/video sidecars 與兩種 bundle manifests。`offline-gallery.zip` 同時包含 image JPEG 與 video GIF primary previews。Complete multipart ZIP 也收錄全部 image/video bundles。

## Release Notes previews

預設 Notes 精選：

- 4 個 image cohorts；
- 2 個 video cohorts。

JPEG 與 GIF previews 先寫入版本化 repo 路徑，再用 raw repository URL 嵌入 Notes；因此 Release asset list 保持 ZIP-only。

若目前沒有可比較 video cohort，Notes 不會放空白 GIF，也不會讓 image Atlas 失敗。

## Visual Lab

Visual Lab index schema v3 為每個 entry 增加：

```json
{
  "media_type": "video",
  "preview_format": "gif",
  "primary_url": "...",
  "bundle_url": "...",
  "full_page_count": 1
}
```

前端提供 Images／Videos filter；GIF 會在卡片中直接播放，影片卡片顯示 keyframe page count，下載連結指向包含該 prompt 的 video bundle。

## Workflow

Production workflow 顯式安裝：

```bash
sudo apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk
```

Validate workflow 也安裝 FFmpeg，並以真實合成 MP4 執行：

- member matching；
- seed cohort policy；
- FFprobe；
- 三點 decode；
- synchronized animated GIF；
- Release-style video ZIP extraction；
- keyframe pages；
- image/video combined ZIP packaging。

Atlas 仍沒有 repository-specific 90-minute timeout、processing cache 或 persistent state。每次重新掃描全部正式 experiment Releases。

## Failure behavior

- 單一壞影片只會被排除並記入 `missing_or_duplicate_media`；
- FFmpeg／FFprobe 不存在會使 workflow 明確失敗；
- draft Release 可在下一次 run 恢復；
- 預期 ZIP 缺失或出現 non-ZIP asset 時不發布成功 index；
- failure recovery artifact 保留 output、index、previews 與 README。

## Production acceptance criteria

影片功能完成需同時符合：

1. 真實 `video_completed` metadata 可被收集；
2. harvester 的 `<prompt_id>_<task>.mp4` 可精準匹配；
3. 不同 random seeds 能形成同一 controlled cohort；
4. broken container／stream 被排除；
5. primary GIF 為多幀且同步；
6. 短片停在最後一幀，不重播；
7. 所有唯一影片都有 10%／50%／90% keyframe evidence；
8. video prompt 每 15 個一個 ZIP；
9. Release Notes 可嵌 GIF，但 Release Assets 維持 ZIP-only；
10. Visual Lab 可搜尋、篩選及下載影片 bundle；
11. 圖片 Atlas 既有測試與 Pages build 不退化。
