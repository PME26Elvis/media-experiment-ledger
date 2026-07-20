# Project Contract / 專案契約

本文件是 `project-contract.json` 的人類可讀版本。重要規則同時存在於 README、`AGENTS.md`、程式設定、測試與各分析規格中；CI 會執行 `python tools/validate_project_contract.py`，任何一個表面漂移都會阻止合併。

## Authority and synchronization

契約的機器可讀來源為 root `project-contract.json`。它不是唯一文件，而是同步錨點：

1. `project-contract.json`：可由程式檢查的值與路徑。
2. `visual-analysis/config.json`：Atlas 實際執行參數。
3. `config/release-quarantine.json`：歷史無效 run 的版本化例外。
4. `config/atlas-history-overrides.json`：舊 Atlas schema 缺失欄位，以及極少數經證據確認 report 本身錯誤時的審核記錄。
5. README、`AGENTS.md` 與本文件：人類／agent 操作說明。
6. Atlas、影片與 YOLO 規格：各分析模組的完整契約。
7. tests 與 validation workflow：防止上述內容靜默漂移。

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
- 任何其他全資料衍生分析。

目前 2026-06-29 的 `run_test` 是 synthetic fixture，另有一個 0 files／0 bytes 的空 run；兩者保留在歷史 Release 中，但不再被當作正式實驗。

## Completion events versus archived media

`image_completed`／`video_completed` 是 API 或 harvester 的成功事件；它們不等於已封存媒體。新發布流程必須分別記錄並驗證：

- API completion events；
- manifest 中的 image/video file records；
- media ZIP 的實際 members；
- asset size、SHA-256 與 ZIP CRC。

新 run 在發布前必須滿足完成事件數等於對應封存檔案數，且不得為空 run 或測試命名。歷史 Release Notes 由 auditor 改成清楚分列 API events 與 archived media。

## Prompt Repeatability Atlas

- 使用全部已發布、非 quarantine 的正式 corpus，每次全量重建，不使用隱藏 incremental state。
- 圖片與影片永遠是不同 cohort。
- Release Assets 維持 ZIP-only；inline JPEG/GIF 來自版本化 repo preview 路徑。
- 圖片與影片均以每 **15 prompt IDs** 一個 deterministic bundle。
- 影片 seed 保留為 sample evidence，但因 harvester 每次隨機化，seed 不進 repeatability identity。
- Image Release Notes 最多 15 個、至少 4 unique samples，先覆蓋 category 再按樣本數補滿。
- Video Release Notes 預設放入所有至少 2 unique samples 的可比較 cohorts。
- Atlas Release Notes 繼續直接嵌入 image comparison cards 與 eligible video GIF previews；YOLO 的規格、workflow、Notes 或 Release 不得縮減這個行為。
- Atlas workflow 維持 `.github/workflows/visual-analysis.yml`，Release 家族維持 `media-analysis-*`。
- Atlas 歷史表通常以 immutable Atlas report 的明確值為準；舊 schema 缺欄位時才讀一般 override。
- 只有當 report 本身已由 source Release、原始歷史表與 entry evidence 證實錯誤時，override 才可標記 `authoritative: true` 並優先於 report。兩者皆無則顯示未知，絕不以目前 corpus totals 回填舊快照。

## YOLOX-Tiny object detection status

YOLO 功能目前為 `implementation_pending_production`。完整規格位於 [`YOLO_OBJECT_DETECTION_SPEC.md`](YOLO_OBJECT_DETECTION_SPEC.md)，目前已實作：

- SHA-pinned YOLOX-Tiny ONNX model 與 COCO 80 labels；
- 真實 ONNX Runtime CPU smoke test；
- quarantine-aware full-corpus Release inventory；
- asset SHA、ZIP CRC、safe path、manifest member SHA 與 Pillow decode 驗證；
- 同一次 workflow 內 image SHA dedupe，並保留所有 source aliases；
- 單一 350-minute hosted-runner job；
- 每張圖片 success 或 explicit failure sidecar；
- annotated JPEG、class summaries、timing、source indexes 與 deterministic ZIP-only assets；
- 獨立 `.github/workflows/yolo-object-detection.yml`；
- 獨立 `media-yolo-all-<latest-experiment-date>-vN` Release；
- 獨立 latest/history indexes、README history 與 YOLO Lab；
- 每次 invocation 從零重跑，不使用 persistent state、跨 run cache skip 或 published-result reuse；
- YOLO 與 Atlas 不共用 workflow、draft Release、finalizer、assets、Notes、latest pointer 或 history table。

只有在 main 上完成一次真正的 full-corpus workflow，並驗證 published Release、ZIP assets、latest/history writeback、YOLO Lab、Pages 與 Atlas 非回歸後，狀態才能改為 `implemented`。

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
npm run build --prefix web
python tools/validate_site_build.py
```

`validate_project_contract.py` 會檢查 JSON contract、Atlas config、quarantine policy、README、`AGENTS.md`、本文件、三份分析規格、YOLO model lock、labels、workflow、indexes、UI 與測試表面。修改任何契約時，必須在同一個 PR 中同步所有受影響表面。
