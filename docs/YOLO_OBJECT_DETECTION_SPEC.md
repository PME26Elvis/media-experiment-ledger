# Full-Corpus YOLO Object Detection Specification

> Status: **`specified_not_implemented`**  
> 本文件定義 production implementation contract；在程式、workflow、測試、Release 產物與 Visual Lab 全部完成前，不得在 README 或 UI 宣稱此功能已上線。

## 1. 目標

對所有正式、非 quarantine 的 `media-exp-*` 圖片執行 pretrained COCO object detection，產生：

- 每張圖片的 bounding boxes、class、confidence；
- 可直接檢視的 annotated preview；
- machine-readable detection sidecar；
- 全 corpus 的 class frequency、detection density、empty-detection 與來源 Release 統計；
- 可在 Visual Lab 與 Prompt Repeatability Atlas entry 中切換的 object overlay；
- 可重建、可驗證、ZIP-only 的 companion Release assets。

這不是訓練、微調或品質評分系統。第一版只做 frozen pretrained COCO inference，不把「偵測到物件」解讀成生成品質、prompt adherence 或安全判定。

## 2. 非目標

第一版不做：

- 自訂資料集訓練或 fine-tuning；
- segmentation、pose、tracking 或 OCR；
- 影片逐幀偵測；
- persistent state、跨 run cache 或只處理新增圖片；
- 使用 detection 結果改寫原始 experiment Releases；
- 把沒有 COCO label 的內容判定為錯誤生成；
- 將 confidence 當作真實世界機率。

## 3. 模型與授權決策

### 3.1 預設模型

- Family: **YOLOX-Tiny**
- Training dataset: **COCO** 80 classes
- Runtime: **ONNX Runtime** CPU execution provider
- Input size: `416 × 416`
- Upstream license: Apache-2.0
- Approximate upstream model scale: 5.06M parameters、6.45 GFLOPs、COCO AP 32.8（416 input）

採用 YOLOX-Tiny，而不是把 Ultralytics package 當 production dependency，原因是：

1. YOLOX upstream 為 Apache-2.0，公開 repo 與衍生產物的授權邊界較單純；
2. Tiny model 適合 GitHub-hosted CPU runner；
3. ONNX Runtime 可避免在 workflow 安裝完整 PyTorch stack；
4. model、pre/post-processing 與 thresholds 可被固定並納入 dataset fingerprint；
5. 輸出格式容易與現有 Python、Pillow、ZIP packaging 管線整合。

### 3.2 權重 pinning

Production implementation 必須把以下資訊寫入 `object-detection/model-lock.json`：

- model family；
- upstream repository 與 release/version；
- ONNX download URL；
- expected byte size；
- SHA-256；
- input tensor name、shape、dtype；
- output tensor names／shape interpretation；
- COCO labels file SHA-256；
- preprocessing 與 postprocessing schema version。

建議初始 ONNX artifact 為約 20.2 MB 的 YOLOX-Tiny 416 model，已知 SHA-256：

```text
427cc366d34e27ff7a03e2899b5e3671425c262ea2291f88bb942bc1cc70b0f7
```

實作 PR 必須在 CI 下載後先驗證 hash；hash 不符立即失敗，不允許靜默接受新的權重。

## 4. Canonical corpus

YOLO corpus 與 Atlas 使用同一個正式母體：

1. 列舉所有已發布、非 draft 的 `media-exp-*` Releases；
2. 套用 `config/release-quarantine.json`；
3. 只接受 canonical runs；
4. 從 manifest 取得 image assets 與 file records；
5. 下載 image ZIP 並驗證 ZIP CRC、asset SHA-256、member path；
6. 只處理能以 Pillow 完整 decode 的圖片；
7. 以原始 image SHA-256 去除完全相同的 bytes；
8. 每個 detection record 仍保留所有 source aliases，避免 dedupe 後失去來源證據。

`media-input-*`、Atlas previews、YOLO annotated previews、README 圖片與任何 derived Release 都不能回流成輸入。

### 4.1 Identity

每張 canonical image 的 stable ID：

```text
image_sha256
```

來源 identity 另行保存：

```text
release_tag / run_id / archive_asset / archive_member / prompt_id / cohort_id(optional)
```

同一 bytes 出現在多個 Releases 時只 inference 一次，但 sidecar 必須列出全部 aliases。

## 5. Dataset fingerprint

YOLO analysis fingerprint 必須包含：

- 所有 canonical experiment Release tags 與 published timestamps；
- quarantine policy SHA-256；
- model-lock JSON canonical digest；
- model ONNX SHA-256；
- COCO labels SHA-256；
- preprocessing schema version；
- postprocessing schema version；
- confidence threshold；
- NMS IoU threshold；
- max detections per image；
- annotated-image rendering policy；
- packaging schema version；
- sharding algorithm version。

不得把 job order、runner hostname、temporary path 或 execution timestamp 放進 fingerprint。

## 6. Preprocessing

Production defaults：

```json
{
  "input_width": 416,
  "input_height": 416,
  "color_order": "RGB",
  "layout": "NCHW",
  "dtype": "float32",
  "normalization": "model-lock-defined",
  "resize": "letterbox",
  "letterbox_fill": 114,
  "preserve_aspect_ratio": true
}
```

必須記錄：

- 原始 width／height；
- resize scale；
- left/top padding；
- EXIF transpose 是否套用；
- alpha channel 如何 compositing；
- decode library/version。

Bounding boxes 必須從 model input coordinates 反算回原始圖片 pixel coordinates，並 clamp 到影像邊界。

## 7. Postprocessing

Production defaults：

```json
{
  "confidence_threshold": 0.25,
  "nms_iou_threshold": 0.45,
  "max_detections_per_image": 100,
  "nms_scope": "per-class",
  "box_format": "xyxy_original_pixels"
}
```

每個 detection 至少包含：

```json
{
  "class_id": 0,
  "class_name": "person",
  "confidence": 0.8731,
  "bbox_xyxy": [104.2, 55.0, 388.4, 501.7],
  "bbox_normalized_xyxy": [0.1357, 0.0716, 0.5057, 0.6533],
  "area_pixels": 126903.2,
  "area_fraction": 0.214
}
```

排序：confidence descending → class ID → box coordinates。JSON float 建議固定為 6 位小數，確保 deterministic diffs。

## 8. GitHub Actions runtime design

### 8.1 Hosted-runner limit

GitHub-hosted standard jobs 的單一 job execution time 上限為 **6 hours**。即使公開 repo 的 standard runner minutes 很寬鬆，也不能把 6 小時視為可用 inference budget；下載、解壓、model setup、JSON merge、ZIP upload 與 runner variability 都必須留 headroom。

若 5000 張圖片以極端保守的 4 秒／張串行推論：

```text
5000 × 4 s = 20,000 s = 5 h 33 m 20 s
```

這已過度接近 6 hours，不可採單 job 串行設計。

### 8.2 Fixed matrix sharding

第一版固定 **8-way matrix**：

```yaml
strategy:
  fail-fast: false
  matrix:
    shard: [0, 1, 2, 3, 4, 5, 6, 7]
```

Deterministic assignment：

```text
int(image_sha256[0:16], 16) % shard_count
```

5000 張、4 秒／張的悲觀估算：約 625 張／shard，純 inference 約 41 分 40 秒；即使加上 I/O 與 packaging，仍有充足 headroom。

`shard_count=8` 是 output contract 的一部分；未來調整 shard count 不應改變 detection JSON，只改變 execution plan。Shard merge 必須按 image SHA-256 排序，不依 job 完成順序。

### 8.3 Workflow jobs

建議 workflow：`.github/workflows/media-analysis.yml`

1. `plan-corpus`
   - checkout main；
   - 列舉 Releases、套用 quarantine；
   - 下載 manifests；
   - 建立 canonical image inventory；
   - 計算 analysis fingerprint；
   - 建立或復用 matching draft companion Release；
   - 輸出 shard manifests 作為 ephemeral Actions artifact。

2. `detect` matrix × 8
   - 下載 model 並驗證 SHA-256；
   - 下載自己的 shard 所需 image ZIPs；
   - 驗證 archive/member；
   - ONNX Runtime CPU inference；
   - 產生 sidecars、annotated previews、shard summary；
   - 建立 deterministic ZIP parts；
   - 上傳 ephemeral workflow artifact。

3. `finalize-analysis`
   - 下載所有 shard artifacts；
   - 驗證 shard coverage 無遺漏／重複；
   - merge class summaries；
   - 產生 gallery/index；
   - 與 Atlas build outputs 組合；
   - 上傳 namespaced Release assets；
   - 編輯 Release Notes；
   - 發布 draft；
   - 寫回 Visual Lab index 與少量版本化 annotated previews。

4. `failure-recovery`
   - 任一 shard 失敗時保持 Release 為 draft；
   - 上傳 corpus plan、completed shard manifests、logs 與 partial package 為 7-day Actions artifact；
   - 不更新 README latest Atlas、不更新 Visual Lab published pointer。

### 8.4 No state/cache rule

每次 production run 都：

- 重新列舉全部 Releases；
- 重新讀 manifests；
- 重新套用 quarantine；
- 重新計算 fingerprint；
- 重新 inference 全部 canonical unique images。

不維護「已處理 image SHA」state，不依 Actions cache 判定 correctness。可使用 runner-local temporary files；不可使用跨 run cache 跳過 inference。若 fingerprint 已有完整 published Release，非 force 執行可直接復用整個 immutable published result，這是 content-addressed publication reuse，不是增量 cache。

## 9. Release architecture

### 9.1 Same companion Release

不建立 `media-yolo-*` 第三種 Release 家族。YOLO 與 Prompt Repeatability Atlas 都是相同 canonical corpus 的衍生分析，應放入同一個：

```text
media-analysis-all-<combined-analysis-fingerprint>-vN
```

理由：

- 使用者只需找到一個「此 corpus 的分析快照」；
- README 歷史不會被多種 analysis Releases 分散；
- Visual Lab entry 可從同一 Release 取得 comparison 與 detection bundles；
- 原始資料 Releases、衍生分析 Releases 的兩層結構仍清楚；
- Atlas 與 YOLO 檔案透過 namespaced asset names／ZIP internal paths 分離，不會混淆。

### 9.2 Independent build, shared finalization

同一 Release 不代表同一巨大 job。Atlas 與 YOLO 應為獨立 jobs／matrix，最後由單一 finalizer 驗證兩側 completion manifests 後發布。

第一個實作 PR 可先將現有 Atlas workflow 改名／重構為共用 `media-analysis.yml`；若 migration 風險過高，可保留 `visual-analysis.yml` 作為 reusable workflow，再由 coordinator 呼叫 Atlas 與 YOLO jobs。

### 9.3 Namespaced assets

Release assets 仍全部 ZIP-only：

```text
atlas-image-bundle-001-i0001-to-i0015.zip
yolo-detection-bundle-001-shard00-part001.zip
yolo-detection-bundle-002-shard01-part001.zip
analysis-metadata.zip
offline-analysis-gallery.zip
media-analysis-complete-part001.zip
```

ZIP internal layout：

```text
object-detection/yolox-tiny/
  model-lock.json
  corpus-manifest.json
  detections/
    ab/cd/<image-sha256>.json
  annotated/
    ab/cd/<image-sha256>.jpg
  source-index/
    by-release.json
    by-run.json
    by-prompt.json
  summaries/
    global.json
    classes.json
    releases.json
    prompts.json
    empty-detections.json
  manifests/
    shard-00.json
    package-001.json
```

`analysis-metadata.zip` 同時包含 Atlas report 與 YOLO summary，但保持子目錄：

```text
atlas/...
object-detection/yolox-tiny/...
```

## 10. Annotated images

### 10.1 Rendering

- 原始圖片不可修改；
- annotated image 是 derived JPEG；
- preserve aspect ratio；
- EXIF transpose 後繪製；
- box line width 依圖片短邊動態計算；
- label 顯示 `class confidence`；
- class color 由 class ID deterministic 生成；
- label 背景需有足夠對比；
- 不裁切；
- 最大 preview edge 建議 1600 px；
- JPEG quality 88；
- 沒有 detections 時仍可產生 sidecar，但預設不重編碼一張無 box 的 annotated duplicate。

### 10.2 Release Notes previews

Release Notes 不應嵌入全部 annotated images。建議最多 12 張 representative previews：

1. 先覆蓋不同 top class；
2. 再覆蓋高 detection count、低 detection count；
3. 保留 2 張 empty-detection examples；
4. 同一 prompt 最多 2 張；
5. 全部有 entry 與 bundle link。

完整 results 由 Visual Lab filter 與 ZIP bundles 提供。

## 11. JSON schemas

### 11.1 Per-image sidecar

```json
{
  "schema_version": 1,
  "analysis_type": "object_detection",
  "model": "YOLOX-Tiny",
  "training_dataset": "COCO",
  "model_sha256": "...",
  "analysis_fingerprint": "...",
  "image_sha256": "...",
  "width": 1024,
  "height": 1024,
  "sources": [
    {
      "release_tag": "media-exp-2026-07-13",
      "run_id": "run_...",
      "asset": "run_...-images.zip",
      "member": "media/images/i0001_....png",
      "prompt_id": "i0001"
    }
  ],
  "preprocess": {
    "scale": 0.40625,
    "pad_left": 0,
    "pad_top": 0
  },
  "thresholds": {
    "confidence": 0.25,
    "nms_iou": 0.45
  },
  "detections": [],
  "detection_count": 0,
  "class_counts": {},
  "annotated_file": null
}
```

### 11.2 Shard completion manifest

必須包含：

- shard index/count；
- expected image IDs；
- processed image IDs；
- failures with reason；
- output files＋size＋SHA-256；
- class counts；
- inference timing summary；
- ONNX Runtime version；
- model/labels hashes；
- peak resident memory（可得時）；
- start/end UTC。

Finalizer 對所有 shard manifests 做 set equality：

```text
union(processed + failures) == expected corpus
intersection between shards == empty
```

任一 decode/inference failure 必須留 sidecar failure record，不得靜默遺漏。

## 12. Visual Lab integration

每個 image entry 可新增：

- `object_detection.available`；
- `object_detection.model`；
- `object_detection.detection_count`；
- `object_detection.top_classes`；
- `object_detection.sidecar_url`；
- `object_detection.annotated_preview_url`；
- `object_detection.bundle_url`。

UI：

- media filter 仍保留 Image／Video；
- image card 新增 `Boxes` toggle；
- `Original`／`Atlas comparison`／`YOLO boxes` 三種視圖不能互相覆寫；
- class filter 支援 COCO class；
- confidence slider 只在 browser 過濾已輸出的 detections，不重新 inference；
- 顯示「COCO-pretrained detector，未偵測不代表圖片沒有物體」；
- video cards 第一版不顯示 object detection。

## 13. Analytics integration

可新增但不得與生成成功率混合的指標：

- images with ≥1 detection；
- empty-detection rate；
- detections per image；
- class frequency；
- class co-occurrence；
- object area fraction distribution；
- class frequency by prompt category／model／release date；
- person、vehicle 等 selected classes 的 trend。

不得把 detector false negative 當生成失敗；所有 dashboard 文案使用「detector observed」而非「image contains」。

## 14. Performance instrumentation

每個 shard 紀錄：

- model load seconds；
- archive download seconds；
- unzip/member-read seconds；
- decode seconds；
- preprocess seconds；
- inference seconds；
- NMS seconds；
- render seconds；
- package seconds；
- images per second；
- p50/p95 per-image latency；
- runner CPU count；
- peak RSS（可取得時）。

第一個 production run 後，以實測決定是否維持 8 shards；但不得降低到可能逼近 6 hours 的配置。

## 15. Reliability and security

- 只從 pinned HTTPS URL 下載 model；
- 驗證 SHA-256；
- ONNX 不允許外部 data file 除非全部 pin/hash；
- ZIP member 必須防 path traversal；
- 不執行 Release 內任何 script；
- Pillow 開啟後完整 decode，並設定合理 decompression-bomb policy；
- JSON sidecar 不包含 secret、signed URL 或 runner temp path；
- workflow permissions 最小化；matrix jobs只需 `contents: read`，finalizer 才需 `contents: write`；
- draft Release 在所有 completion manifests 通過前不可發布。

## 16. Bias and interpretation

COCO 只有 80 classes，對抽象圖、UI mockup、diagram、fantasy、Taiwan-specific object、產品細分類與文字內容覆蓋有限。主要限制：

- unknown object 會被忽略或誤分類為近似 COCO class；
- stylized／small／occluded objects recall 較低；
- confidence 不可跨 class 或跨 domain 當作 calibration；
- synthetic images 與 COCO natural-image distribution 不同；
- class frequency 受 prompt bank 設計與生成順序中斷影響；
- detector observations 不代表公平、安全或真實性。

README、Release Notes 與 Visual Lab 必須顯示這些限制的精簡版。

## 17. Testing contract

### Unit tests

- letterbox transform 與 inverse box mapping；
- confidence filtering；
- class-aware NMS；
- deterministic ordering／rounding；
- shard assignment；
- exact SHA dedupe＋source aliases；
- quarantine exclusion；
- ZIP path traversal rejection；
- COCO labels lock；
- package manifests；
- empty detection sidecar。

### Model integration tests

使用少量 repo fixture images，執行真正 ONNX Runtime inference：

- model hash 驗證；
- tensor input/output shape；
- 至少一張有 detection；
- 至少一張 empty/low-confidence；
- annotated render 可由 Pillow decode；
- repeated run JSON byte-identical（排除 timestamp fields）。

### Workflow tests

- 8 shards coverage；
- shard failure 保留 draft；
- missing shard finalization failure；
- duplicate image across Releases inference once／aliases retained；
- all assets ZIP-only；
- Release Notes links；
- Visual Lab route/build validation；
- production Release/index/writeback verification。

## 18. Acceptance criteria

功能只有在以下全部完成後才能把 status 改成 implemented：

1. 全 canonical image corpus 被 inventory；
2. quarantine runs 沒有進入 inventory；
3. model/labels hash pinned；
4. 8-way matrix 實際跑過；
5. 每張 unique image 都有 success 或 explicit failure sidecar；
6. shard coverage set equality 通過；
7. detection JSON schema 測試通過；
8. annotated previews 可檢視；
9. companion Release 同時含 Atlas 與 namespaced YOLO assets；
10. Release Assets 全部 ZIP-only；
11. Visual Lab overlay／class filter 上線；
12. README、`AGENTS.md`、`project-contract.json`、本 spec、workflow 與測試同步；
13. PR CI 全綠；
14. production Release、README history、Visual Lab index 與 Pages 實際驗證成功。

## 19. Suggested implementation sequence

### Phase A — inference core

- model lock；
- ONNX Runtime wrapper；
- preprocessing／NMS／sidecar schemas；
- real inference tests。

### Phase B — corpus and sharding

- reuse Experiment Release Auditor inventory logic；
- canonical dedupe／aliases；
- matrix shard manifests；
- shard packages。

### Phase C — companion Release coordinator

- Atlas／YOLO independent completion manifests；
- shared draft Release finalizer；
- namespaced assets；
- recovery behavior。

### Phase D — Visual Lab and analytics

- overlay toggle；
- class filters；
- summaries；
- representative Release Notes previews。

### Phase E — production verification

- full rebuild；
- timing review；
- inspect assets／Notes／Pages；
- update status from `specified_not_implemented` only after all acceptance criteria pass。
