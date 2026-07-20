#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


replace_required(
    ROOT / "AGENTS.md",
    "- YOLOX-Tiny object detection is currently `implementation_pending_production`: implementation exists, but do not call it fully production-complete until a real `media-yolo-*` Release, index writeback, YOLO Lab, README history, and Atlas non-regression are verified.",
    "- YOLOX-Tiny object detection is `implemented`: production Release `media-yolo-all-2026-07-13-v1`, writeback commit `bab357c4f92963d5d74e7229ad86272147436295`, YOLO Lab, README history, 387-image coverage, and Atlas non-regression were verified.",
)

replace_required(
    ROOT / "docs" / "PROJECT_CONTRACT.md",
    "YOLO 功能目前為 `implementation_pending_production`。完整規格位於 [`YOLO_OBJECT_DETECTION_SPEC.md`](YOLO_OBJECT_DETECTION_SPEC.md)，目前已實作：",
    "YOLO 功能狀態為 `implemented`。完整規格位於 [`YOLO_OBJECT_DETECTION_SPEC.md`](YOLO_OBJECT_DETECTION_SPEC.md)。首個 production Release 為 `media-yolo-all-2026-07-13-v1`，writeback commit 為 `bab357c4f92963d5d74e7229ad86272147436295`，實測處理 387 張 canonical images，其中 313 張有偵測，共 1,533 個 boxes。已實作並驗證：",
)
replace_required(
    ROOT / "docs" / "PROJECT_CONTRACT.md",
    "只有在 main 上完成一次真正的 full-corpus workflow，並驗證 published Release、ZIP assets、latest/history writeback、YOLO Lab、Pages 與 Atlas 非回歸後，狀態才能改為 `implemented`。",
    "首個 main full-corpus workflow 已完成；published Release、ZIP-only assets、latest/history writeback、20 張版本化 previews、YOLO Lab、Pages build 與 Atlas 非回歸均已驗證。",
)

spec = ROOT / "docs" / "YOLO_OBJECT_DETECTION_SPEC.md"
replace_required(spec, "> Status: **`implementation_pending_production`**  ", "> Status: **`implemented`**  ")
replace_required(
    spec,
    "> Decision status: **implementation complete; production verification pending**  ",
    "> Decision status: **production implemented and verified**  ",
)
replace_required(
    spec,
    "The status remains `implementation_pending_production` until the merged main workflow publishes and verifies the first real full-corpus Release, index/writeback, Pages route, and Atlas non-regression.",
    "Production verification completed on 2026-07-20: `media-yolo-all-2026-07-13-v1` processed 387 canonical images, observed detections in 313 images, produced 1,533 boxes, wrote independent latest/history indexes and 20 versioned previews, and preserved the Atlas 15-image/all-video preview contract.",
)

replace_required(
    ROOT / "README.md",
    "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測已完成獨立 workflow、`media-yolo-*` Release、ZIP、index 與 YOLO Lab 實作，正在等待第一次 production 全量驗證；詳見[完整契約](docs/YOLO_OBJECT_DETECTION_SPEC.md)與 [YOLO Lab](web/src/content/docs/yolo-lab.mdx)。",
    "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測已正式上線：獨立 workflow、`media-yolo-*` Release、ZIP-only assets、index、README history 與 [YOLO Lab](web/src/content/docs/yolo-lab.mdx) 均已完成。首個 Release `media-yolo-all-2026-07-13-v1` 全量處理 387 張 canonical images，313 張有偵測，共 1,533 個 boxes；詳見[完整契約](docs/YOLO_OBJECT_DETECTION_SPEC.md)。",
)
replace_required(
    ROOT / "README.en.md",
    "- YOLOX-Tiny / ONNX Runtime / COCO object detection now has an independent workflow, `media-yolo-*` Release family, ZIP packages, indexes, and YOLO Lab implementation; the first production full-corpus verification is pending. See the [full contract](docs/YOLO_OBJECT_DETECTION_SPEC.md) and [YOLO Lab](web/src/content/docs/yolo-lab.mdx).",
    "- YOLOX-Tiny / ONNX Runtime / COCO object detection is live with an independent workflow, `media-yolo-*` Releases, ZIP-only assets, indexes, README history, and [YOLO Lab](web/src/content/docs/yolo-lab.mdx). The first Release, `media-yolo-all-2026-07-13-v1`, processed all 387 canonical images, observed detections in 313, and produced 1,533 boxes. See the [full contract](docs/YOLO_OBJECT_DETECTION_SPEC.md).",
)

Path(__file__).unlink()
