# Project Contract / 專案契約

本文件是 `project-contract.json` 的人類可讀版本。重要規則同時存在於 README、`AGENTS.md`、程式設定、測試與各分析規格中；CI 會執行 `python tools/validate_project_contract.py`，任何一個表面漂移都會阻止合併。

## Authority and synchronization

契約的機器可讀來源為 root `project-contract.json`。它不是唯一文件，而是同步錨點：

1. `project-contract.json`：可由程式檢查的值與路徑。
2. `visual-analysis/config.json`：Atlas 實際執行參數。
3. `config/release-quarantine.json`：歷史無效 run 的版本化例外。
4. `config/atlas-history-overrides.json`：只有舊 Atlas schema 缺少 corpus-count fields 時才使用的審核記錄。
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
- 未來 YOLO object-detection corpus；
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
- Atlas 歷史表只讀該 immutable Atlas report 的明確值；舊 schema 缺欄位時才讀 `config/atlas-history-overrides.json`，兩者皆無則顯示未知，絕不以目前 corpus totals 回填舊快照。

## YOLOX-Tiny object detection status

YOLO 功能目前狀態為 `specified_not_implemented`。完整規格位於 [`YOLO_OBJECT_DETECTION_SPEC.md`](YOLO_OBJECT_DETECTION_SPEC.md)。預設方案是 Apache-2.0 的 YOLOX-Tiny COCO 模型、ONNX Runtime CPU inference、全資料重跑、deterministic matrix sharding，以及與 Atlas 共用同一個 media-analysis companion Release 的 namespaced assets。

在 production implementation 完成前，README 與 UI 不得把它描述成已上線功能。

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
npm run build --prefix web
python tools/validate_site_build.py
```

`validate_project_contract.py` 會檢查 JSON contract、Atlas config、quarantine policy、README、`AGENTS.md`、本文件與三份分析規格。修改任何契約時，必須在同一個 PR 中同步所有受影響表面。
