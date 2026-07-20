#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise RuntimeError(f"Expected text not found in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


spec = ROOT / "docs" / "YOLO_OBJECT_DETECTION_SPEC.md"
replace_required(
    spec,
    "> Status: **`specified_not_implemented`**  ",
    "> Status: **`implementation_pending_production`**  ",
)
replace_required(
    spec,
    "> Decision status: **approved direction, implementation pending**  ",
    "> Decision status: **implementation complete; production verification pending**  ",
)
text = spec.read_text(encoding="utf-8")
checkpoint = """## 0. Implementation checkpoint

The production implementation is now present on the feature branch: pinned model and labels, real ONNX Runtime smoke validation, quarantine-aware full-corpus inventory, verified ZIP extraction, within-run SHA dedupe with aliases, single-job inference, explicit failure sidecars, annotated previews, deterministic ZIP-only assets, independent `media-yolo-*` publication, latest/history indexes, README history, and YOLO Lab filters.

The status remains `implementation_pending_production` until the merged main workflow publishes and verifies the first real full-corpus Release, index/writeback, Pages route, and Atlas non-regression.

"""
if "## 0. Implementation checkpoint" not in text:
    marker = "## 1. 決策摘要"
    if marker not in text:
        raise RuntimeError("YOLO spec decision marker missing")
    text = text.replace(marker, checkpoint + marker, 1)
spec.write_text(text, encoding="utf-8")

readme = ROOT / "README.md"
replace_required(
    readme,
    "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測目前為[詳盡規格](docs/YOLO_OBJECT_DETECTION_SPEC.md)，狀態是 **specified, not implemented**。",
    "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測已完成獨立 workflow、`media-yolo-*` Release、ZIP、index 與 YOLO Lab 實作，正在等待第一次 production 全量驗證；詳見[完整契約](docs/YOLO_OBJECT_DETECTION_SPEC.md)與 [YOLO Lab](web/src/content/docs/yolo-lab.mdx)。",
)
text = readme.read_text(encoding="utf-8")
if "<!-- AUTO:YOLO_HISTORY:START -->" not in text:
    text = text.rstrip() + """

## YOLO 物件偵測歷史

<!-- AUTO:YOLO_HISTORY:START -->
| 發布日期 | 資料範圍 | 圖片 | 有偵測 | 偵測框 | 模型 | Release |
|---|---|---:|---:|---:|---|---|
<!-- AUTO:YOLO_HISTORY:END -->
"""
readme.write_text(text, encoding="utf-8")

readme_en = ROOT / "README.en.md"
replace_required(
    readme_en,
    "- YOLOX-Tiny / ONNX Runtime / COCO object detection has a [detailed specification](docs/YOLO_OBJECT_DETECTION_SPEC.md) and is **specified, not implemented**.",
    "- YOLOX-Tiny / ONNX Runtime / COCO object detection now has an independent workflow, `media-yolo-*` Release family, ZIP packages, indexes, and YOLO Lab implementation; the first production full-corpus verification is pending. See the [full contract](docs/YOLO_OBJECT_DETECTION_SPEC.md) and [YOLO Lab](web/src/content/docs/yolo-lab.mdx).",
)
text = readme_en.read_text(encoding="utf-8")
if "<!-- AUTO:YOLO_HISTORY_EN:START -->" not in text:
    text = text.rstrip() + """

## YOLO object-detection history

<!-- AUTO:YOLO_HISTORY_EN:START -->
| Published | Source range | Images | With detections | Detections | Model | Release |
|---|---|---:|---:|---:|---|---|
<!-- AUTO:YOLO_HISTORY_EN:END -->
"""
readme_en.write_text(text, encoding="utf-8")

gitignore = ROOT / ".gitignore"
text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
for line in ("object-detection/output/", "object-detection/model-cache/"):
    if line not in text.splitlines():
        text = text.rstrip() + "\n" + line + "\n"
gitignore.write_text(text, encoding="utf-8")

Path(__file__).unlink()
