# 專案狀態與歷史

**繁體中文** | [English](PROJECT_STATUS.en.md)

> [!NOTE]
> 這一頁集中保存由 GitHub Actions 維護的 corpus 統計、Atlas 歷史與偵測基準。根目錄 README 只作為專案入口，不再承載持續增長的歷史表格。

## 即時 corpus 統計

<!-- AUTO:LEDGER_STATS:START -->
> 此區塊由 GitHub Actions 全量重建；只統計正式 `media-exp-*` 中非 quarantine runs 的封存媒體，`media-input-*` snapshot 與純 metadata fixture 不會重複計入。

| 統計項目 | 數值 |
|---|---:|
| 正式 Experiment Releases | 20 |
| 實驗日期範圍 | 2026-06-29 → 2026-08-03 |
| 圖片總數 | 893 |
| 影片總數 | 86 |
| 最新 Prompt Repeatability Atlas | [media-analysis-all-c1196dea3267-v2](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-c1196dea3267-v2) |
<!-- AUTO:LEDGER_STATS:END -->

完整 Release manifests、封存媒體數量與 quarantine 結果以 [`Experiment Release Audit`](reports/EXPERIMENT_RELEASE_AUDIT.md) 為準。

## Prompt Repeatability Atlas 歷史

<!-- AUTO:ATLAS_HISTORY:START -->
> 每次 Atlas workflow 都重新掃描全部 Atlas Releases 並重建此表，不依賴增量狀態。

| 發布日期 | 圖譜類型 | 資料範圍 | 圖片 | 影片 | 可比較 Prompt | Release |
|---|---|---|---:|---:|---:|---|
| 2026-08-04 | 全域重現性圖譜 | 2026-06-29 → 2026-08-03 | 893 | 86 | 152 | [`media-analysis-all-c1196dea3267-v2`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-c1196dea3267-v2) |
| 2026-08-04 | 全域重現性圖譜 | 2026-06-29 → 2026-08-03 | 893 | 86 | 152 | [`media-analysis-all-c1196dea3267-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-c1196dea3267-v1) |
| 2026-07-21 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v9`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v9) |
| 2026-07-21 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v8`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v8) |
| 2026-07-21 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v7`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v7) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v6`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v6) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v5`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v5) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v4`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v4) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v3`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v3) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v2`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v2) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 387 | 33 | 87 | [`media-analysis-all-633b2daf9eab-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-633b2daf9eab-v1) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 87 | [`media-analysis-all-c45c1b53c1f7-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-c45c1b53c1f7-v1) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 87 | [`media-analysis-all-34912876cb25-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-34912876cb25-v1) |
| 2026-07-20 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-f5fdcae2c78b-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-f5fdcae2c78b-v1) |
| 2026-07-19 | 全域重現性圖譜 | 2026-06-29 → 2026-07-13 | 937 | 40 | 80 | [`media-analysis-all-8b850904b063-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-all-8b850904b063-v1) |
| 2026-07-19 | 歷史單次圖譜 | 2026-07-13 | 3 | 1 | 3 | [`media-analysis-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-analysis-2026-07-13-v1) |
<!-- AUTO:ATLAS_HISTORY:END -->

歷史數值取自各 Atlas Release 的 immutable report。只有來源 Release、原始歷史與 entry evidence 證明舊報告錯誤時，才允許在 [`config/atlas-history-overrides.json`](../config/atlas-history-overrides.json) 使用經審核的 `authoritative: true` 修正；目前 corpus totals 不會回填舊快照。

## YOLOX-only 歷史

<!-- AUTO:YOLO_HISTORY:START -->
| 發布日期 | 資料範圍 | 圖片 | 有偵測 | 偵測框 | 模型 | Release |
|---|---|---:|---:|---:|---|---|
| 2026-07-20 | 2026-06-29 → 2026-07-13 | 387 | 313 | 1,533 | YOLOX-Tiny | [`media-yolo-all-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-yolo-all-2026-07-13-v1) |
<!-- AUTO:YOLO_HISTORY:END -->

這個 `media-yolo-*` 系列是保留的 immutable 歷史；目前正式多模型管線使用 `media-detection-*`。

<!-- NANODET:README:START -->
## YOLOX + NanoDet 多模型偵測基準

多模型管線狀態為 **`implemented`**。首個 production corpus 由 YOLOX-Tiny run `29812888677` 與 NanoDet-Plus-m-320 run `29812888709` 從零處理完整 387 張 canonical images；publisher run `29813188073` 以 exact workflow run IDs 與完整 corpus/hash 契約配對，發布 ZIP-only [`media-detection-all-2026-07-13-v1`](https://github.com/PME26Elvis/media-experiment-ledger/releases/tag/media-detection-all-2026-07-13-v1)。

- YOLOX：1,533 boxes；NanoDet：3,243 boxes；同類別 IoU ≥ 0.50 配對 902 組。
- Mean disagreement 為 0.5574；這是 agreement／disagreement 觀察，不是 accuracy benchmark。
- [Detector Lab](../web/src/content/docs/detector-lab.mdx) 提供 Original／YOLOX／NanoDet 三欄比較與版本化代表預覽。
- [完整 production evidence](reports/NANODET_PRODUCTION_EVIDENCE.md) · [完整契約](NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md)
<!-- NANODET:README:END -->

最新 detector publication 以 [`data/detection/latest.json`](../data/detection/latest.json) 與 [`data/detection/history.json`](../data/detection/history.json) 為準。Detector workflows 只分析 canonical images；影片仍由 Analytics 與 Prompt Repeatability Atlas 處理。

## 快速入口

- [完整文件索引](README.md)
- [GitHub Pages 觀測站](https://pme26elvis.github.io/media-experiment-ledger/)
- [所有 Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases)
- [專案契約](PROJECT_CONTRACT.md)
- [Release 完整性稽核](reports/EXPERIMENT_RELEASE_AUDIT.md)
