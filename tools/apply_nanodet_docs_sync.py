#!/usr/bin/env python3
"""Synchronize long-form NanoDet implementation blocks without touching generated history."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value.rstrip() + "\n", encoding="utf-8")


def upsert(path: str, start: str, end: str, block: str) -> None:
    text = read(path)
    rendered = f"{start}\n{block.strip()}\n{end}"
    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        text = f"{before}\n\n{rendered}\n\n{after}"
    else:
        text = f"{text.rstrip()}\n\n{rendered}\n"
    write(path, text)


spec_path = "docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md"
spec = read(spec_path).replace(
    "Status: **`specified_not_implemented`**",
    "Status: **`implemented_pending_production`**",
    1,
)
write(spec_path, spec)
upsert(
    spec_path,
    "<!-- NANODET:IMPLEMENTATION:START -->",
    "<!-- NANODET:IMPLEMENTATION:END -->",
    r"""
## 18. Implementation status — 2026-07-21

The approved architecture is now implemented in the feature branch and is intentionally marked **`implemented_pending_production`** until the first full-corpus A/B run and combined Release are verified.

Implemented surfaces:

- `tools/nanodet_core.py`: official BGR/direct-resize preprocessing, 2,125 center priors, distribution-to-box decode, class-aware NMS, and original-image coordinate recovery;
- `object-detection/nanodet-model-lock.json`: official immutable pre-exported ONNX asset `nanodet-plus-m_320.onnx`, exact 4,793,615-byte size, SHA-256 `4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610`, input `[1,3,320,320]`, and output `[1,2125,112]`;
- `tools/build_detector_artifact.py`: shared complete-corpus-from-scratch artifact builder with normalized success/failure sidecars and deterministic ZIPs;
- separate read-only YOLOX and NanoDet inference workflows that publish workflow artifacts only;
- an exact-run publisher that validates `analysis_batch_id`, corpus fingerprint, quarantine digest, source Release order, canonical image SHA set, labels, thresholds, package hashes, ZIP CRC, and full sidecar coverage before publication;
- agreement/disagreement metrics, Original | YOLOX-Tiny | NanoDet-Plus tri-panels, comparison ZIPs, latest/history indexes, and Detector Lab;
- legacy `media-yolo-*` automation retired to explicit manual recovery; new production publications use `media-detection-*`.

### Model supply-chain decision

The alpha tag's legacy checkpoint exporter imports a removed `LightningLoggerBase` API. A reproducible bootstrap run proved that incompatibility before publication. The same official immutable Release provides a fixed-shape ONNX asset, so production uses that shorter supply chain instead of adding an obsolete PyTorch/Lightning environment. Every CI and production run downloads the official ONNX, checks exact size and SHA-256, creates an ONNX Runtime CPU session, and executes a real shape smoke.

### Promotion gate

The status changes from `implemented_pending_production` to `implemented` only after all of the following are recorded: successful YOLOX run ID, successful NanoDet run ID, publisher run ID, immutable `media-detection-all-*` Release, ZIP-only asset verification, detector index/writeback commit, live Detector Lab JSON/previews, and Atlas non-regression.
""",
)

upsert(
    "README.md",
    "<!-- NANODET:README:START -->",
    "<!-- NANODET:README:END -->",
    r"""
## YOLOX + NanoDet 多模型偵測

新管線狀態為 **`implemented_pending_production`**。YOLOX-Tiny 與 NanoDet-Plus-m-320 分別在完整 canonical corpus 從零推論，只上傳短期 workflow artifact；第三個 publisher 以 exact workflow run IDs 與完整 corpus/hash 契約配對，通過後才建立 ZIP-only `media-detection-*` Release。

- [Detector Lab](web/src/content/docs/detector-lab.mdx) 呈現 Original／YOLOX／NanoDet 三欄比較、class overlap、box IoU 與 agreement／disagreement。
- 這不是 accuracy benchmark；沒有人工 COCO ground truth 時，不宣稱 precision、recall、mAP、false positive 或哪個模型比較正確。
- NanoDet 使用官方 immutable ONNX，size、SHA、輸入與輸出 shape 皆由 CI 真實驗證。
- Prompt Repeatability Atlas 完全獨立，不共用 workflow、Release、index、preview 或 finalizer。
- 完整契約：[NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md)。
""",
)

upsert(
    "README.en.md",
    "<!-- NANODET:README_EN:START -->",
    "<!-- NANODET:README_EN:END -->",
    r"""
## YOLOX + NanoDet multi-detector analysis

The new pipeline is **`implemented_pending_production`**. YOLOX-Tiny and NanoDet-Plus-m-320 each rebuild the complete canonical corpus from scratch and upload short-lived workflow artifacts only. A third publisher pairs exact workflow run IDs and validates the full corpus/hash contract before creating a ZIP-only `media-detection-*` Release.

- [Detector Lab](web/src/content/docs/detector-lab.mdx) presents Original / YOLOX / NanoDet tri-panels, class overlap, box IoU, and agreement/disagreement.
- This is not an accuracy benchmark. Without human COCO ground truth, the project does not claim precision, recall, mAP, false positives, or which detector is correct.
- NanoDet uses the official immutable ONNX; CI executes real size, SHA, input-shape, output-shape, and ONNX Runtime checks.
- Prompt Repeatability Atlas remains completely independent and shares no workflow, Release, index, preview, or finalizer.
- Full contract: [NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md).
""",
)

upsert(
    "AGENTS.md",
    "<!-- NANODET:AGENTS:START -->",
    "<!-- NANODET:AGENTS:END -->",
    r"""
## Multi-detector behavior

- Multi-detector status is `implemented_pending_production` until the production evidence fields in `project-contract.json` are populated.
- Inference workflows are read-only and artifact-only. Pair only exact workflow run IDs; never combine independently selected "latest" runs.
- NanoDet-Plus uses the SHA-pinned official immutable pre-exported ONNX and `requirements-nanodet.txt`; do not reintroduce the obsolete Lightning checkpoint exporter without a new audited decision.
- The publisher must verify batch, corpus fingerprint, quarantine digest, source Releases, canonical image SHA set, COCO labels, thresholds, sidecar coverage, package hashes, and ZIP CRC before creating `media-detection-*`.
- Detector Lab is the primary combined UI. YOLO Lab remains a legacy historical view.
- Use agreement/disagreement language only. No accuracy claim is allowed without ground truth.
- Multi-detector work must not change Atlas workflow, Releases, previews, indexes, history, or finalizer.
""",
)

upsert(
    "docs/PROJECT_CONTRACT.md",
    "<!-- NANODET:PROJECT_CONTRACT:START -->",
    "<!-- NANODET:PROJECT_CONTRACT:END -->",
    r"""
## Multi-detector implementation boundary

The YOLOX + NanoDet pipeline is `implemented_pending_production`. Two read-only inference workflows produce short-lived artifacts; one publisher downloads exact workflow run IDs, verifies an identical canonical corpus contract, and creates the immutable `media-detection-*` product. Detector Lab reads `data/detection/latest.json`; YOLO Lab remains a legacy `media-yolo-*` view.

NanoDet-Plus-m-320 uses the SHA-pinned official immutable ONNX asset and ONNX Runtime CPU. The repository records model size/SHA and real `[1,3,320,320] → [1,2125,112]` execution. Generated media lacks human COCO ground truth, so only agreement/disagreement metrics are valid.

Production promotion requires verified A/B/publisher workflow IDs, Release assets, writeback, live Pages, and Atlas non-regression. Until then, all production fields remain null.
""",
)

web_path = "docs/WEB_EXPERIENCE_AND_FORECASTS.md"
web = read(web_path)
web = web.replace("all seven primary route files", "all eight primary route files")
web = web.replace("all four deployed JSON artifacts", "all five deployed JSON artifacts")
write(web_path, web)
upsert(
    web_path,
    "<!-- NANODET:WEB:START -->",
    "<!-- NANODET:WEB:END -->",
    r"""
## Detector Lab integration

The site now has **eight primary routes** and **five deployed JSON artifacts**. Detector Lab is the combined YOLOX/NanoDet route and reads `data/detection/latest.json`; YOLO Lab remains available for immutable legacy YOLO-only history. The new route uses the same base-safe `sitePath()` helper, Astro build boundary, ephemeral `site/` artifact, and `actions/upload-pages-artifact` deployment contract.
""",
)
