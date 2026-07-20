# Full-Corpus YOLO Object Detection Specification

> Status: **`implementation_pending_production`**  
> Decision status: **implementation complete; production verification pending**  
> 本文件定義未來 production implementation contract；在程式、獨立 workflow、測試、Release 產物與 Visual Lab 整合全部完成前，不得在 README 或 UI 宣稱此功能已上線。

## 0. Implementation checkpoint

The production implementation is now present on the feature branch: pinned model and labels, real ONNX Runtime smoke validation, quarantine-aware full-corpus inventory, verified ZIP extraction, within-run SHA dedupe with aliases, single-job inference, explicit failure sidecars, annotated previews, deterministic ZIP-only assets, independent `media-yolo-*` publication, latest/history indexes, README history, and YOLO Lab filters.

The status remains `implementation_pending_production` until the merged main workflow publishes and verifies the first real full-corpus Release, index/writeback, Pages route, and Atlas non-regression.

## 1. 決策摘要

YOLO 物件偵測與 Prompt Repeatability Atlas 從架構、執行與發布層完全分離：

- Atlas 維持現有 `.github/workflows/visual-analysis.yml`；
- Atlas 維持現有 `media-analysis-*` Release 家族；
- Atlas Release Notes 繼續大量嵌入圖片 comparison cards 與所有符合條件的影片 GIF previews；
- YOLO 使用新的獨立 workflow：`.github/workflows/yolo-object-detection.yml`；
- YOLO 使用新的獨立 Release 家族：`media-yolo-all-<latest-experiment-date>-vN`；
- YOLO workflow 不等待 Atlas、不修改 Atlas、不與 Atlas 共用 draft/finalizer；
- YOLO v1 使用單一 GitHub-hosted CPU job 全量串行推論；
- YOLO 每次執行都從零重建，不使用 persistent state、跨 run cache、增量跳過或 published-result reuse；
- Visual Lab 未來可用 `image_sha256` 在 build-time 或 browser 端關聯 Atlas 與 YOLO，但兩者的 Release 與資料契約保持獨立。

這個方向優先維持既有 Atlas 的成熟使用體驗，並讓 YOLO 成為可獨立啟動、失敗、重跑、發布與移除的附加分析產品。

## 2. 目標

對所有正式、非 quarantine 的 `media-exp-*` 圖片執行 pretrained COCO object detection，產生：

- 每張圖片的 bounding boxes、class、confidence；
- 可直接檢視的 annotated preview；
- machine-readable detection sidecar；
- 全 corpus 的 class frequency、detection density、empty-detection 與來源 Release 統計；
- 獨立、不可變、可下載的 YOLO Release；
- 未來可在 Visual Lab 中切換的 object overlay；
- 可重建、可驗證、ZIP-only 的 YOLO Release assets。

這不是訓練、微調或品質評分系統。第一版只做 frozen pretrained COCO inference，不把「偵測到物件」解讀成生成品質、prompt adherence、安全判定或真實世界正確性。

## 3. 非目標

第一版不做：

- 自訂資料集訓練或 fine-tuning；
- segmentation、pose、tracking 或 OCR；
- 影片逐幀偵測；
- persistent state、跨 run cache 或只處理新增圖片；
- content-addressed published-result reuse；
- 看到相同 corpus fingerprint 就跳過 inference；
- 使用 detection 結果改寫原始 experiment Releases；
- 使用 YOLO workflow 修改、重發或 gate Atlas Releases；
- 把 YOLO assets 放入 `media-analysis-*`；
- 把沒有 COCO label 的內容判定為錯誤生成；
- 將 confidence 當作真實世界機率；
- 第一版建立 matrix sharding 或多 runner coordinator。

## 4. Atlas 非回歸契約

YOLO implementation 不得改變下列已認可的 Atlas 行為：

1. Atlas workflow 仍為 `.github/workflows/visual-analysis.yml`；
2. Atlas Release tags 仍使用 `media-analysis-*`；
3. Atlas image/video cohorts 仍分離；
4. 每個 Atlas ZIP bundle 仍最多包含 15 個 prompt IDs；
5. Atlas Release Notes 的 image highlights 上限仍為 15；
6. Atlas Release Notes 的 video highlights 仍為所有至少 2 unique samples 的 eligible video cohorts；
7. Atlas Release Notes 仍直接嵌入 image comparison previews 與 video GIF previews；
8. Atlas inline previews 仍由版本化 repository preview paths 提供；
9. YOLO 成功或失敗都不能阻止 Atlas 發布；
10. YOLO Release Notes 的長度、preview policy 或 assets 不得限制 Atlas Notes。

YOLO implementation PR 必須加入非回歸測試，確認 `visual-analysis/config.json` 的 Atlas preview、bundle 與 highlight policy 沒有被修改。

## 5. 模型與授權決策

### 5.1 預設模型

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
4. model、pre/post-processing 與 thresholds 可被固定並記錄；
5. 輸出格式容易與現有 Python、Pillow、ZIP packaging 管線整合。

### 5.2 權重 pinning

Production implementation 必須建立：

```text
object-detection/model-lock.json
```

至少記錄：

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

每次 workflow 都重新下載或由明確固定的 repository asset 取得模型，並在 inference 前驗證 hash。第一版不使用 Actions cache 跳過模型驗證。

## 6. Canonical corpus

YOLO 與 Atlas讀取相同的正式原始資料母體，但各自獨立執行：

1. 列舉所有已發布、非 draft 的 `media-exp-*` Releases；
2. 套用 `config/release-quarantine.json`；
3. 只接受 canonical runs；
4. 從 manifest 取得 image assets 與 file records；
5. 下載 image ZIP 並驗證 ZIP CRC、asset SHA-256、member path；
6. 只處理能以 Pillow 完整 decode 的圖片；
7. 以原始 image SHA-256 去除同一次 workflow 中完全相同的 bytes；
8. 每個 detection record 保留所有 source aliases，避免 dedupe 後失去來源證據。

`media-input-*`、Atlas previews、YOLO annotated previews、README 圖片與任何 derived Release 都不能回流成輸入。

### 6.1 Identity

每張 canonical image 的 stable ID：

```text
image_sha256
```

來源 identity 另行保存：

```text
release_tag / run_id / archive_asset / archive_member / prompt_id / cohort_id(optional)
```

同一 bytes 出現在多個 Releases 時，在單次 workflow 內只 inference 一次，但 sidecar 必須列出全部 aliases。這是同一輪執行內的 byte deduplication，不是跨 workflow 的 cache 或 published-result reuse。

## 7. Rebuild policy：每次完整重跑

每次 production invocation 都必須：

- 重新列舉全部 Releases；
- 重新下載與讀取 manifests；
- 重新套用 quarantine；
- 重新建立完整 canonical image inventory；
- 重新下載並驗證模型；
- 重新 inference 全部 canonical unique images；
- 重新產生 sidecars、annotated previews、summaries 與 ZIP packages；
- 成功後建立一個新的 immutable YOLO Release。

明確禁止：

- 維護「已處理 image SHA」state；
- 依 Actions cache 決定哪些圖片不用 inference；
- 查到相同 corpus fingerprint 就直接沿用舊 Release；
- 將上一個 YOLO Release 當下一次分析的資料來源；
- 只分析最新 experiment package；
- 以 Atlas output 作為 YOLO input。

Corpus fingerprint 仍可放在 report 中作為稽核、比較與重現資訊，但**不得用來跳過執行或復用已發布結果**。

## 8. 執行規模與單一 job 決策

### 8.1 預期規模

目前資料累積速度低，Agnes AI 免費服務不穩定，實際每日通常不到 10 張，且不會每天都有新資料。第一版以未來可能但仍偏高的 **3000 張圖片**作為設計基準。

以極端保守的 4 秒／張串行推論：

```text
3000 × 4 s = 12,000 s = 3 h 20 m
```

即使再加入 Release inventory、ZIP download、decode、annotated rendering、packaging 與 upload，仍預期可落在 GitHub-hosted standard job 的 6 hours 上限內。

### 8.2 v1 不做 matrix

第一版預設單一 job：

```yaml
jobs:
  analyze-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 350
```

理由：

- 目前 corpus 遠小於 3000；
- workflow 結構明顯更簡單；
- 不需要 shard manifests、merge coordinator 或跨 job artifact fan-in；
- 避免為短期不會出現的規模增加維護成本；
- 使用者不頻繁上傳多日 package，完整重跑頻率低。

### 8.3 未來才重新評估的條件

只有在 production timing 顯示下列任一條件時，才另開 spec revision 討論 sharding：

- 單次 workflow 實際總時間連續兩次超過 4 小時 30 分；
- canonical unique images 明顯超過 3000；
- inference p95 大幅高於 4 秒；
- GitHub runner CPU 或 I/O 使總時間接近 timeout；
- 單一 job 曾因時間限制失敗。

不得預先在 v1 實作未被實測需要的 matrix 架構。

## 9. 獨立 GitHub Actions workflow

規劃路徑：

```text
.github/workflows/yolo-object-detection.yml
```

### 9.1 Triggers

第一版主要入口：

```yaml
on:
  workflow_dispatch:
```

可提供：

- `reason`：自由文字，寫入 run summary 與 Release Notes；
- `confidence_threshold`：預設 0.25；
- `nms_iou_threshold`：預設 0.45；
- `max_detections_per_image`：預設 100；
- `publish_release`：預設 true，允許測試時只產 Actions artifact。

未來若要在 experiment batch 發布後自動啟動，可由 publisher 發送獨立 `repository_dispatch` 或呼叫 reusable workflow，但必須符合：

- Atlas 與 YOLO 各自收到獨立 trigger；
- YOLO 失敗不回滾 experiment Releases；
- YOLO 失敗不影響 Atlas；
- Atlas 失敗不影響 YOLO；
- 兩者不共用 draft Release 或 finalizer。

### 9.2 單一 job phases

`analyze-and-publish` job 依序執行：

1. **checkout-and-validate-contract**
   - checkout main；
   - 驗證 project contract 與 quarantine policy；
   - 記錄 commit SHA。

2. **inventory-corpus**
   - 列舉 `media-exp-*`；
   - 下載 manifests；
   - 套用 quarantine；
   - 建立 canonical image inventory；
   - 計算 corpus fingerprint；
   - 記錄 latest experiment date。

3. **download-and-verify-model**
   - 下載 YOLOX-Tiny ONNX；
   - 驗證 size 與 SHA-256；
   - 載入 COCO labels lock。

4. **download-and-verify-images**
   - 下載必要 image ZIP assets；
   - 驗證 asset SHA-256、ZIP CRC、safe paths；
   - 完整 decode；
   - 建立 within-run deduplicated image set。

5. **run-inference**
   - ONNX Runtime CPU；
   - 順序固定為 image SHA-256 ascending；
   - 每張輸出 success 或 explicit failure record；
   - 不允許靜默遺漏。

6. **render-and-summarize**
   - 產生 annotated previews；
   - 彙整 classes、prompts、Releases、empty detections；
   - 記錄 timing 與環境資訊。

7. **package-and-verify**
   - deterministic ZIP packaging；
   - 產生 package manifests；
   - 再次驗證 output coverage、size、SHA-256 與 ZIP CRC。

8. **publish-independent-release**
   - 先完成全部本地驗證；
   - 建立獨立 YOLO draft Release；
   - 上傳 ZIP-only assets；
   - 寫入 Release Notes；
   - 驗證 assets 完整；
   - 最後將 draft 發布。

9. **write-index**
   - 寫回獨立 YOLO index；
   - 不修改 Atlas latest pointer 或 Atlas history rows；
   - 未來可更新 README 的獨立 YOLO history table。

## 10. 獨立 Release architecture

### 10.1 Release family

YOLO 使用獨立 tag：

```text
media-yolo-all-<latest-experiment-date>-vN
```

範例：

```text
media-yolo-all-2026-07-13-v1
media-yolo-all-2026-07-13-v2
media-yolo-all-2026-07-20-v1
```

規則：

- `<latest-experiment-date>` 是此次完整 corpus 中最新正式 experiment date；
- `vN` 在相同 latest date 下遞增；
- 每次成功 invocation 都建立新的版本，即使 corpus fingerprint 與先前相同；
- Release report 仍記錄完整 source tags、source digests、corpus fingerprint、code SHA 與 model SHA；
- 不刪除、不覆寫舊 YOLO Releases；
- YOLO Release 不使用 `media-analysis-*`；
- Atlas Release 不使用 `media-yolo-*`。

### 10.2 Release title

```text
YOLO Object Detection — YOLOX-Tiny / COCO (through YYYY-MM-DD)
```

### 10.3 Release family separation

Repository 中形成三個清楚層次：

```text
media-exp-*       immutable formal source data
media-analysis-*  Prompt Repeatability Atlas only
media-yolo-*      YOLO object-detection analysis only
```

`media-input-*` 仍只是 transport/snapshot，不屬於正式分析或正式統計。

## 11. YOLO Release assets

所有 Release assets 維持 ZIP-only：

```text
yolo-coco-metadata.zip
yolo-coco-detections-part001.zip
yolo-coco-annotated-part001.zip
yolo-coco-offline-gallery.zip
yolo-coco-complete-part001.zip
```

資料量增加時使用 deterministic parts：

```text
yolo-coco-detections-part002.zip
yolo-coco-annotated-part002.zip
yolo-coco-complete-part002.zip
```

ZIP internal layout：

```text
object-detection/yolox-tiny/
  model-lock.json
  corpus-manifest.json
  analysis-report.json
  detections/
    ab/cd/<image-sha256>.json
  annotated/
    ab/cd/<image-sha256>.jpg
  failures/
    ab/cd/<image-sha256>.json
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
    timing.json
  manifests/
    package-001.json
```

YOLO metadata 不得放進 `atlas-metadata.zip`，Atlas metadata 也不得放進 YOLO assets。

## 12. Release Notes

YOLO 有自己的 Release Notes，不與 Atlas 共用模板。

### 12.1 Summary

至少顯示：

- source experiment date range；
- source Release count；
- canonical unique images；
- successfully inferred images；
- explicit failures；
- images with detections；
- empty-detection images；
- total detections；
- top COCO classes；
- model/version/SHA；
- thresholds；
- corpus fingerprint；
- code SHA；
- total wall time；
- ZIP asset links。

### 12.2 Annotated previews

YOLO Notes 可嵌入代表性 annotated previews，但其 policy 完全獨立於 Atlas。建議第一版最多 20 張：

1. 優先覆蓋不同 top classes；
2. 再覆蓋高 detection count 與低 detection count；
3. 保留少量 empty-detection examples；
4. 同一 prompt 不超過 2 張；
5. 每張都連到 containing annotated ZIP；
6. inline previews 由版本化 repository path 提供，不以上傳裸 JPG 當 Release asset。

這個上限只適用 YOLO Release Notes，不能拿來縮減 Atlas 的 15 image highlights 或 all-video GIF highlights。

## 13. Preprocessing

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

## 14. Postprocessing

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

## 15. Per-image sidecar schema

```json
{
  "schema_version": 1,
  "analysis_type": "object_detection",
  "model": "YOLOX-Tiny",
  "training_dataset": "COCO",
  "model_sha256": "...",
  "analysis_run_id": "...",
  "corpus_fingerprint": "...",
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
  "annotated_file": null,
  "status": "success"
}
```

Decode 或 inference failure 必須產生 explicit failure sidecar，至少包含：

- image SHA；
- sources；
- failure phase；
- normalized error class；
- safe error message；
- timestamp；
- model/code identifiers。

## 16. Annotated image rendering

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
- 沒有 detections 時仍產生 sidecar，但預設不重編碼一張無 box 的 annotated duplicate。

## 17. Visual Lab integration

YOLO 不修改 Atlas Release，但未來可在 Visual Lab 以 `image_sha256` 關聯：

- Atlas index 提供 image source／cohort information；
- YOLO index 提供 detection sidecar／annotated preview；
- build step 或 browser 端以 `image_sha256` join；
- 任一側缺資料時 UI 仍可正常顯示另一側；
- YOLO Release 被移除或尚未發布時，Atlas UI 不得壞掉。

每個 image entry 可新增：

- `object_detection.available`；
- `object_detection.release_tag`；
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

### 17.1 獨立 index

建議寫回：

```text
data/yolo/latest.json
data/yolo/history.json
web/public/data/yolo/latest.json
```

不得寫入或覆蓋：

```text
data/visual-analysis/latest.json
README Atlas history markers
Atlas Release metadata
```

## 18. README 與歷史列表

YOLO implementation 完成後，README 可新增獨立區塊：

```text
<!-- AUTO:YOLO_HISTORY:START -->
<!-- AUTO:YOLO_HISTORY:END -->
```

欄位建議：

- published date；
- source date range；
- analyzed images；
- images with detections；
- total detections；
- model；
- Release link。

這個表不得插入 Atlas history table，也不得讓 README 的「最新 Atlas」指向 YOLO Release。

## 19. Analytics integration

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

YOLO analytics 可以有獨立 route 或 panel，但不得改變 Atlas 的 comparable cohort metrics。

## 20. Performance instrumentation

單一 job 必須記錄：

- model download seconds；
- model load seconds；
- Release inventory seconds；
- archive download seconds；
- unzip/member-read seconds；
- decode seconds；
- preprocess seconds；
- inference seconds；
- NMS seconds；
- render seconds；
- package seconds；
- upload seconds；
- total wall time；
- images per second；
- p50/p95 per-image latency；
- runner CPU count；
- peak RSS（可取得時）。

Timing report 必須進 `yolo-coco-metadata.zip`，作為未來是否需要重新討論 sharding 的依據。

## 21. Reliability and security

- 只從 pinned HTTPS URL 下載 model；
- 驗證 SHA-256；
- ONNX 不允許外部 data file，除非全部 pin/hash；
- ZIP member 必須防 path traversal；
- 不執行 Release 內任何 script；
- Pillow 開啟後完整 decode，並設定合理 decompression-bomb policy；
- JSON sidecar 不包含 secret、signed URL 或 runner temp path；
- workflow permissions 最小化；分析階段只需 `contents: read`，發布階段才需 `contents: write`；
- 所有本地 coverage／package checks 通過後才能建立或發布 Release；
- YOLO workflow 不應具備修改既有 Atlas Releases 的程式路徑；
- 新增測試確認 YOLO tag selector 只接受 `media-yolo-*`，Atlas selector 只接受 `media-analysis-*`。

## 22. Failure and recovery

### 22.1 在建立 Release 前失敗

- workflow 直接失敗；
- 上傳 7-day diagnostic Actions artifact；
- 不建立 YOLO Release；
- 不更新 YOLO latest index；
- 不影響 Atlas 或 experiment Releases。

### 22.2 Release upload 中途失敗

- 保留 draft YOLO Release；
- 不設為 published；
- 不更新 latest index；
- 下一次 workflow 仍從零分析，不復用該 draft 的 detection results；
- 可由維護者刪除失敗 draft，或在完整重跑後由新 workflow 覆蓋同一 draft 的 assets；
- 不得因存在 draft 就跳過 inference。

### 22.3 部分圖片失敗

第一版允許少量 explicit per-image failures，但必須：

- 每個失敗都有 sidecar；
- report 清楚列出 failure count 與類別；
- `success + failures == expected unique images`；
- 不得靜默少檔；
- 若 failure rate 超過預設 1%，整體 workflow 失敗且不發布。

## 23. Bias and interpretation

COCO 只有 80 classes，對抽象圖、UI mockup、diagram、fantasy、Taiwan-specific object、產品細分類與文字內容覆蓋有限。主要限制：

- unknown object 會被忽略或誤分類為近似 COCO class；
- stylized／small／occluded objects recall 較低；
- confidence 不可跨 class 或跨 domain 當作 calibration；
- synthetic images 與 COCO natural-image distribution 不同；
- class frequency 受 prompt bank 設計與生成順序中斷影響；
- detector observations 不代表公平、安全或真實性。

README、YOLO Release Notes 與 Visual Lab 必須顯示這些限制的精簡版。

## 24. Testing contract

### 24.1 Unit tests

- letterbox transform 與 inverse box mapping；
- confidence filtering；
- class-aware NMS；
- deterministic ordering／rounding；
- exact SHA dedupe＋source aliases；
- quarantine exclusion；
- ZIP path traversal rejection；
- COCO labels lock；
- package manifests；
- empty detection sidecar；
- explicit failure sidecar；
- YOLO Release tag versioning；
- YOLO index 不修改 Atlas index；
- no published-result reuse；
- no incremental state input。

### 24.2 Model integration tests

使用少量 repo fixture images，執行真正 ONNX Runtime inference：

- model hash 驗證；
- tensor input/output shape；
- 至少一張有 detection；
- 至少一張 empty/low-confidence；
- annotated render 可由 Pillow decode；
- repeated run JSON byte-identical（排除 timestamp/run-ID fields）。

### 24.3 Workflow tests

- workflow path 為獨立 `yolo-object-detection.yml`；
- 單一 job coverage；
- 全 corpus inventory；
- duplicate image across Releases inference once／aliases retained；
- failure before publish 不建立 Release；
- upload failure 保留 draft；
- all assets ZIP-only；
- YOLO Release Notes links；
- YOLO tag 為 `media-yolo-*`；
- Atlas Release tag、Notes、assets 與 latest index 不變；
- Visual Lab route/build validation；
- production YOLO Release/index/writeback verification。

### 24.4 Atlas non-regression tests

必須明確驗證：

- `release_notes_image_highlights == 15`；
- `release_notes_video_highlights == "all"`；
- `release_notes_video_min_samples == 2`；
- `prompts_per_bundle == 15`；
- `video_prompts_per_bundle == 15`；
- Release Notes 仍包含 `Image highlights`；
- Release Notes 仍包含 `Video highlights`；
- image preview Markdown 與 video GIF preview Markdown 仍會產生；
- YOLO workflow 不在 Atlas finalizer dependencies 中。

## 25. Acceptance criteria

功能只有在以下全部完成後才能把 status 改成 implemented：

1. 全 canonical image corpus 被 inventory；
2. quarantine runs 沒有進入 inventory；
3. model/labels hash pinned；
4. 單一 hosted-runner job 實際跑過完整 corpus；
5. 每張 unique image 都有 success 或 explicit failure sidecar；
6. `success + failures == expected corpus`；
7. detection JSON schema 測試通過；
8. annotated previews 可檢視；
9. 成功建立獨立 `media-yolo-all-<date>-vN` Release；
10. YOLO Release Assets 全部 ZIP-only；
11. 每次 invocation 重新 inference，沒有 state/cache/published-result reuse；
12. YOLO 失敗不影響 Atlas；
13. Atlas 大量圖片與 GIF Release Notes preview contract 通過非回歸測試；
14. Visual Lab overlay／class filter 上線；
15. README 的 YOLO history 與 Atlas history 分離；
16. README、`AGENTS.md`、`project-contract.json`、本 spec、workflow 與測試同步；
17. PR CI 全綠；
18. production YOLO Release、YOLO index、Visual Lab 與 Pages 實際驗證成功。

## 26. Suggested implementation sequence

### Phase A — inference core

- model lock；
- ONNX Runtime wrapper；
- preprocessing／NMS／sidecar schemas；
- real inference tests。

### Phase B — canonical corpus runner

- reuse Experiment Release Auditor 的讀取與 quarantine 邏輯；
- canonical inventory；
- within-run SHA dedupe／aliases；
- single-job timing instrumentation；
- deterministic packages。

### Phase C — independent workflow and Release

- `.github/workflows/yolo-object-detection.yml`；
- manual trigger；
- `media-yolo-all-<date>-vN` versioning；
- independent Release Notes；
- draft/publish recovery；
- independent latest/history index。

### Phase D — Visual Lab and analytics

- build-time/browser join by image SHA；
- overlay toggle；
- class filters；
- summaries；
- representative YOLO Release Notes previews；
- independent README YOLO history。

### Phase E — production verification

- full rebuild without cache/state/reuse；
- timing review；
- inspect assets／Notes／Pages；
- confirm Atlas Release Notes remain unchanged；
- update status from `specified_not_implemented` only after all acceptance criteria pass。

## 27. Rejected alternatives

### 27.1 與 Atlas 共用 `media-analysis-*`

拒絕。Atlas 已有成熟、使用者認可且重視大量 inline image/GIF previews 的 Release 體驗。共用 Release 會增加 finalizer coupling、Notes 模板衝突、failure domain 與歷史理解成本。

### 27.2 Atlas/YOLO 共用 coordinator 或 draft

拒絕。任何一側失敗都不應延遲或阻止另一側。

### 27.3 第一版 8-way matrix

拒絕。依目前資料累積速度與 3000 張上限假設，單一 job 足夠；matrix 只在實測逼近 timeout 後重新討論。

### 27.4 Content-addressed publication reuse

拒絕。即使 corpus fingerprint 相同，每次 workflow invocation 仍重新執行全部 inference 並發布新的版本，方便把每次執行視為獨立、完整、可稽核的分析紀錄。

### 27.5 只分析新增圖片

拒絕。這會引入 state、cache invalidation 與跨版本拼接問題，不符合目前簡單且低頻的使用情境。

## 28. 最終架構

```text
media-exp-* Releases
        │
        ├── Prompt Repeatability Atlas
        │     workflow: visual-analysis.yml
        │     releases: media-analysis-*
        │     notes: many image cards + eligible video GIFs
        │
        └── YOLO Object Detection
              workflow: yolo-object-detection.yml
              releases: media-yolo-all-<date>-vN
              execution: one full CPU job, every time from scratch
```

兩條分析管線共用 canonical source-of-truth 與 quarantine policy，但不共用 workflow、Release、finalizer、Notes、assets、latest pointer 或 history table。