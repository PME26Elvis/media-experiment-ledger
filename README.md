# Media Experiment Ledger

**繁體中文** | [English](README.en.md)

以 **GitHub Releases 作為不可變更資料層**的媒體生成實驗平台：保存圖片／影片 runs、重建 Analytics 與 Forecast、產生全資料 Prompt Repeatability Atlas，並以 YOLOX + NanoDet 進行同 corpus 的物件偵測比較，而不把大型原始結果直接提交進 Git history。

<!-- STUDIO_ENTRY:START -->
> [!TIP]
> **桌面版：Media Experiment Ledger Studio**  
> 跨平台、本機優先的 Atlas、物件偵測與媒體自動化桌面產品維護於 [`app-main`](https://github.com/PME26Elvis/media-experiment-ledger/tree/app-main)。  
> [下載 Studio Releases](https://github.com/PME26Elvis/media-experiment-ledger/releases?q=studio-v) · [桌面 App 說明](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/app/README.md) · [完整規格](https://github.com/PME26Elvis/media-experiment-ledger/blob/app-main/docs/app/README.md)
<!-- STUDIO_ENTRY:END -->

## 從這裡開始

| 目的 | 入口 |
|---|---|
| 查看目前 corpus、Atlas 與偵測歷史 | [專案狀態與歷史](docs/PROJECT_STATUS.md) |
| 上傳、保存或 Promote `results.zip` | [ZIP／snapshot 工作流程](docs/INPUT_ARCHIVE_WORKFLOW.md) |
| 在 Codespaces 發布 | [Codespaces 發布指南](docs/CODESPACES_PUBLISHING.md) |
| 瀏覽分析、Visual Lab、Detector Lab 與 Forecast | [GitHub Pages 觀測站](https://pme26elvis.github.io/media-experiment-ledger/) |
| 理解資料與安全邊界 | [專案契約](docs/PROJECT_CONTRACT.md) |
| 尋找所有技術文件 | [文件索引](docs/README.md) |

## 核心能力

### Release-backed ledger

- 每個日期建立 immutable `media-exp-*` Release；同日期新增真正不同的 run 時建立 supplemental Release。
- 圖片、影片、JSONL metadata 與 SHA-256 manifest 分離封裝，接近 GitHub 單一 asset 上限前自動分片。
- 相同內容自動跳過；相同 `run_id` 卻內容不同時 fail closed。
- 大型 archive 可先保存成 byte-exact `media-input-*` snapshot，再於之後 Promote。

### 可重建分析

- Analytics 與 ensemble forecasts 從正式 Releases 全量重建。
- 圖片與影片 Prompt Repeatability Atlas 使用相同 corpus，但 media types 永不混入同一 cohort。
- 每 15 個 prompt IDs 形成 deterministic ZIP bundle；圖片提供 comparison cards，影片提供 FFmpeg 驗證、同步 GIF 與 keyframe sheets。
- GitHub Pages 提供 Overview、Analytics、Visual Lab、Detector Lab、YOLO Lab、Forecast Lab、System Atlas 與 Frontend Stack。

### 物件偵測

- YOLOX-Tiny 與 NanoDet-Plus-m-320 以 read-only、`workflow_dispatch`-only inference workflows 從零分析完整 canonical image corpus；repo push 不會意外啟動昂貴的全量推論。
- Publisher 只接受 exact workflow run IDs、相同 `analysis_batch_id`、corpus fingerprint、quarantine digest、SHA set、labels 與 thresholds。
- Action Promotion 在 corpus 真的改變時會記錄兩個精確 inference run IDs、等待兩者成功，再把該 pair 明確交給 comparison publisher；不依賴 chained `workflow_run` 猜測配對。
- `media-detection-*` 只報告 agreement、disagreement、box IoU、class delta 與 runtime；沒有人工 ground truth 時不宣稱 accuracy、precision、recall 或 mAP。
- [多模型管線規格](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md) · [Detector Lab](web/src/content/docs/detector-lab.mdx)

## 最快發布方式

### 直接發布一個多日期 archive

```bash
python tools/publish_from_archive.py results.zip
```

只驗證、不發布：

```bash
python tools/publish_from_archive.py results.zip --dry-run
```

### 先保存，再透過 Action Promote

```bash
python tools/input_snapshot.py publish results.zip
```

接著到 **Actions → Promote input snapshot**。非 dry-run 且確實建立新正式 Releases 時，Action 會接續更新 Analytics、Release Audit，以共同 batch ID 啟動 YOLOX 與 NanoDet，記錄兩個精確 run IDs、等待兩者成功，再 dispatch comparison publisher 並等待發布完成。重複 Promote 的 no-op 不會浪費 detector inference。

> 直接 CLI Promote 仍會建立正式 Releases、觸發 Analytics 與 Atlas，但不額外 dispatch Audit／detector maintenance；完整差異見[輸入流程文件](docs/INPUT_ARCHIVE_WORKFLOW.md)。若 detector 已成功但 publisher 中斷，可直接用兩個既有 run IDs 手動執行 **Publish YOLOX + NanoDet comparison**，不必重跑 inference。

## 資料流程

```text
results.zip / results/
  → optional media-input-* snapshot
  → immutable media-exp-* Releases
  ├─ Analytics + Forecast + GitHub Pages
  ├─ image/video Prompt Repeatability Atlas → media-analysis-*
  ├─ full Release integrity audit
  └─ exact YOLOX + NanoDet runs → comparison publisher → media-detection-*
```

## 資料完整性

- [`project-contract.json`](project-contract.json) 是機器可驗證的同步錨點。
- [`config/release-quarantine.json`](config/release-quarantine.json) 保留歷史資產，但排除已確認的空 run／metadata fixture。
- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) 只允許對已證實錯誤的舊報告使用經審核的 `authoritative: true` 修正；目前 totals 不會改寫歷史快照。
- [`Experiment Release Audit`](docs/reports/EXPERIMENT_RELEASE_AUDIT.md) 檢查 manifests、JSONL、ZIP members、size、SHA-256 與 CRC。
- `site/` 是短期 Pages build artifact，不提交進 Git；build、deploy 與 writeback 彼此分離。

## 專案地圖

| 區域 | 說明 |
|---|---|
| `tools/` | 發布、分析、Atlas、偵測、Forecast 與驗證工具 |
| `.github/workflows/` | 發布、Promote、Analytics、Atlas、Audit、detector 與 Pages orchestration |
| `docs/` | 操作指南、規格、契約、狀態與 production evidence |
| `data/` | 版本化 latest/history/audit indexes |
| `web/` | Astro／Starlight Pages 前端與部署資料 |
| `app-main` | Media Experiment Ledger Studio 桌面產品分支 |

## 開發與驗證

```bash
python -m pip install \
  -r requirements-analytics.txt \
  -r requirements-forecast.txt \
  -r requirements-visual-analysis.txt \
  -r requirements-yolo.txt \
  -r requirements-nanodet.txt
sudo apt-get install -y --no-install-recommends ffmpeg
python tools/validate_project_contract.py
python -m compileall tools tests
python -m unittest discover -s tests -v
python tools/yolo_model_smoke.py
python tools/nanodet_model_smoke.py
npm install --prefix web --package-lock=false --no-audit --no-fund
npm run build --prefix web
```

Repository 操作與 merge policy 見 [`AGENTS.md`](AGENTS.md)。完整統計與持續增長的歷史表格集中在 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)，不再堆疊於首頁。
