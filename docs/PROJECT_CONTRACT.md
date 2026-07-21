# Project Contract / 專案契約

本文件是 `project-contract.json` 的人類可讀版本。重要規則同時存在於 README、`AGENTS.md`、程式設定、測試與各分析規格中；CI 會執行 `python tools/validate_project_contract.py`，任何一個表面漂移都會阻止合併。

## Authority and synchronization

契約的機器可讀來源為 root `project-contract.json`。它不是唯一文件，而是同步錨點：

1. `project-contract.json`：可由程式檢查的值與路徑。
2. `visual-analysis/config.json`：Atlas 實際執行參數。
3. `config/release-quarantine.json`：歷史無效 run 的版本化例外。
4. `config/atlas-history-overrides.json`：舊 Atlas schema 缺失欄位，以及極少數經證據確認 report 本身錯誤時的審核記錄。
5. `.github/workflows/analytics.yml` 與 `tools/validate_site_build.py`：Pages build、deploy、writeback 與路由／資料驗證契約。
6. README、`AGENTS.md` 與本文件：人類／agent 操作說明。
7. Atlas、影片、YOLO 與 multi-detector 規格：各分析模組的完整契約。
8. tests 與 validation workflow：防止上述內容靜默漂移。

## Source of truth

- 正式原始資料只來自已發布的 `media-exp-*` Releases。
- `media-input-*` 是傳輸或暫存 snapshot，不進正式統計或衍生分析。
- 正式母體定義為：所有已發布 `media-exp-*` 中，套用版本化 Release quarantine 後仍為 canonical 的 runs。
- 已發布資產保持不可變；同日期的新資料使用 supplemental Release。
- 歷史錯誤不以刪除資產掩蓋，而是保留證據、quarantine 無效 run、重建衍生資料並修復 managed Release Notes。

## Release quarantine

`config/release-quarantine.json` 是公開、可審核、帶雙語理由與證據的 policy。所有以下表面必須共用它：

- canonical analytics；
- README totals；
- image/video Prompt Repeatability Atlas；
- Experiment Release Audit；
- YOLO object-detection corpus；
- 未來 NanoDet 與 multi-detector comparison corpus；
- 任何其他全資料衍生分析。

目前 2026-06-29 的 `run_test` 是 synthetic fixture，另有一個 0 files／0 bytes 的空 run；兩者保留在歷史 Release 中，但不再被當作正式實驗。

## Completion events versus archived media

`image_completed`／`video_completed` 是 API 或 harvester 的成功事件；它們不等於已封存媒體。新發布流程必須分別記錄並驗證：

- API completion events；
- manifest 中的 image/video file records；
- media ZIP 的實際 members；
- asset size、SHA-256 與 ZIP CRC。

新 run 在發布前必須滿足完成事件數等於對應封存檔案數，且不得為空 run 或測試命名。歷史 Release Notes 由 auditor 改成清楚分列 API events 與 archived media。

## Pages build boundary

`web/` 是可追蹤的 Astro/Starlight source；`site/` 是編譯產物。

- `site/` 必須列在 `.gitignore`，不得提交至 `main`。
- Pages workflow 分成獨立的 **build**、**deploy**、**writeback** jobs。
- build 會產生 analytics／forecast、暫存 browser JSON、建置 Astro、驗證七個 primary routes 與四份 JSON，再以 `actions/upload-pages-artifact` 上傳 `site/`。
- deploy 只依賴 build artifact，不依賴任何 `git push`，因此 bot writeback race 不能阻止已驗證網站部署。
- writeback 只下載短期 workflow artifact 中的 `analytics/` 與 `forecasts/`，再以 fetch/rebase/push retry 寫回 `main`。
- writeback 不得包含 `site/`、`web/public/` 或任何 Atlas／detector preview 複本。
- `tools/validate_site_build.py` 必須驗證 `overview`、`analytics`、`visual-lab`、`yolo-lab`、`forecast`、`architecture`、`frontend-stack`，以及 `analytics.json`、`forecast.json`、`visual-analysis.json`、`yolo/latest.json`。
- Pages artifact 另有 1 GB 總量與 100 MB 單檔防呆；這是 repo contract 的預警門檻，不是宣稱 GitHub 平台的絕對限制。

## Prompt Repeatability Atlas

- 使用全部已發布、非 quarantine 的正式 corpus，每次全量重建，不使用隱藏 incremental state。
- 圖片與影片永遠是不同 cohort。
- Release Assets 維持 ZIP-only；inline JPEG/GIF 來自版本化 repo preview 路徑。
- 圖片與影片均以每 **15 prompt IDs** 一個 deterministic bundle。
- 影片 seed 保留為 sample evidence，但因 harvester 每次隨機化，seed 不進 repeatability identity。
- Image Release Notes 最多 15 個、至少 4 unique samples，先覆蓋 category 再按樣本數補滿。
- Video Release Notes 預設放入所有至少 2 unique samples 的可比較 cohorts。
- Atlas Release Notes 繼續直接嵌入 image comparison cards 與 eligible video GIF previews；任何 detector 規格、workflow、Notes 或 Release 都不得縮減這個行為。
- Atlas workflow 維持 `.github/workflows/visual-analysis.yml`，Release 家族維持 `media-analysis-*`。
- Atlas 歷史表通常以 immutable Atlas report 的明確值為準；舊 schema 缺欄位時才讀一般 override。
- 只有當 report 本身已由 source Release、原始歷史表與 entry evidence 證實錯誤時，override 才可標記 `authoritative: true` 並優先於 report。兩者皆無則顯示未知，絕不以目前 corpus totals 回填舊快照。

## YOLOX-Tiny object detection status

YOLO 功能狀態為 `implemented`。完整規格位於 [`YOLO_OBJECT_DETECTION_SPEC.md`](YOLO_OBJECT_DETECTION_SPEC.md)。首個 production Release 為 `media-yolo-all-2026-07-13-v1`，writeback commit 為 `bab357c4f92963d5d74e7229ad86272147436295`，實測處理 387 張 canonical images，其中 313 張有偵測，共 1,533 個 boxes。已實作並驗證：

- SHA-pinned YOLOX-Tiny ONNX model 與 COCO 80 labels；
- 真實 ONNX Runtime CPU smoke test；
- quarantine-aware full-corpus Release inventory；
- asset SHA、ZIP CRC、safe path、manifest member SHA 與 Pillow decode 驗證；
- 同一次 workflow 內 image SHA dedupe，並保留所有 source aliases；
- 單一 350-minute hosted-runner job；
- 每張圖片 success 或 explicit failure sidecar；
- annotated JPEG、class summaries、timing、source indexes 與 deterministic ZIP-only assets；
- 獨立 `.github/workflows/yolo-object-detection.yml`；
- 獨立 `media-yolo-*` Release 家族，正式 tag 使用 `media-yolo-all-<latest-experiment-date>-vN`；
- 獨立 latest/history indexes、README history 與 YOLO Lab；
- 每次 invocation 從零重跑，不使用 persistent state、跨 run cache skip 或 published-result reuse；
- YOLO 與 Atlas 不共用 workflow、draft Release、finalizer、assets、Notes、latest pointer 或 history table。

首個 main full-corpus workflow 已完成；published Release、ZIP-only assets、latest/history writeback、20 張版本化 previews、YOLO Lab、Pages build 與 Atlas 非回歸均已驗證。

## YOLOX + NanoDet implementation

[`NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md`](NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md) 的狀態為 `implemented_pending_production`。NanoDet inference、exact-run publisher、comparison gallery、indexes 與 Detector Lab 已實作；首個 `media-detection-*` Release 尚待 main 上的完整 production A/B/C 驗證。

核准方向：

- Workflow A：YOLOX-Tiny 全量 inference，只上傳短期 transport artifact。
- Workflow B：NanoDet-Plus-m-320 全量 inference，只上傳短期 transport artifact。
- Workflow C：使用**明確的兩個 workflow run IDs**下載 artifacts，驗證共同 `analysis_batch_id`、corpus fingerprint、quarantine digest、source Release list、canonical image SHA set 與 COCO labels hash，再發布單一 `media-detection-all-<date>-vN` Release。
- workflow artifacts 不是 source of truth、state、cache 或 published-result reuse；最終 immutable Release 才是正式產品。
- comparison gallery 使用 `Original | YOLOX-Tiny | NanoDet-Plus` tri-panel，另有完整 offline HTML ZIP。
- 由於沒有 human-verified ground truth，只能報告 agreement、disagreement、coverage、box IoU、class distribution 與 runtime；不得稱為 accuracy、precision、recall 或此 corpus 的 mAP。
- 現有 `media-yolo-*` Releases 保持不可變歷史；Atlas 完全不受影響。

## Git and publication behavior

- 預設 feature branch → PR → validation → normal merge commit。
- 除非使用者要求，不刪除分支。
- 不以單元測試代替 production 驗證；涉及 Release、Pages 或 writeback 時必須查實際結果。
- connector／Actions 不可用時，先跑本地可行檢查，再交付 unified patch 或 Codespaces-ready commands。

## Contract validation

PR 與 main push 必須執行：

```bash
python tools/validate_project_contract.py
python -m compileall tools tests
python -m unittest discover -s tests -v
python tools/yolo_model_smoke.py
python tools/nanodet_model_smoke.py
npm run build --prefix web
python tools/validate_site_build.py
```

`validate_project_contract.py` 會檢查 JSON contract、Atlas config、quarantine policy、README、`AGENTS.md`、本文件、分析規格、Pages workflow、`.gitignore`、route/data validator、YOLO model lock、labels、indexes、UI 與測試表面。修改任何契約時，必須在同一個 PR 中同步所有受影響表面。

<!-- NANODET:PROJECT_CONTRACT:START -->
## Multi-detector implementation boundary

The YOLOX + NanoDet pipeline is `implemented_pending_production`. Two read-only inference workflows produce short-lived artifacts; one publisher downloads exact workflow run IDs, verifies an identical canonical corpus contract, and creates the immutable `media-detection-*` product. Detector Lab reads `data/detection/latest.json`; YOLO Lab remains a legacy `media-yolo-*` view.

NanoDet-Plus-m-320 uses the SHA-pinned official immutable ONNX asset and ONNX Runtime CPU. The repository records model size/SHA and real `[1,3,320,320] → [1,2125,112]` execution. Generated media lacks human COCO ground truth, so only agreement/disagreement metrics are valid. The offline gallery covers the full canonical corpus while the web index stages at most 20 representative previews.

Production promotion requires verified A/B/publisher workflow IDs, Release assets, writeback, live Pages, and Atlas non-regression. Until then, all production fields remain null.
<!-- NANODET:PROJECT_CONTRACT:END -->
