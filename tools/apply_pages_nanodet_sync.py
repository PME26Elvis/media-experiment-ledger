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
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


zh_yolo = "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測已正式上線：獨立 workflow、`media-yolo-*` Release、ZIP-only assets、index、README history 與 [YOLO Lab](web/src/content/docs/yolo-lab.mdx) 均已完成。首個 Release `media-yolo-all-2026-07-13-v1` 全量處理 387 張 canonical images，313 張有偵測，共 1,533 個 boxes；詳見[完整契約](docs/YOLO_OBJECT_DETECTION_SPEC.md)。"
zh_added = zh_yolo + "\n- GitHub Pages 已採 build／deploy／writeback 分離：`site/` 只作為短期 Pages artifact，不提交進 Git；deploy 不再被其他 bot workflow 的 `main` writeback race 阻斷。\n- YOLOX + NanoDet-Plus 的三 workflow 聚合方向已完成 [`specified_not_implemented` 規格](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md)：兩個 inference artifacts 由 exact run IDs 配對，再由獨立 publisher 建立 `media-detection-*` Release 與 Original／YOLOX／NanoDet comparison gallery。"
replace_required(ROOT / "README.md", zh_yolo, zh_added)

en_yolo = "- YOLOX-Tiny / ONNX Runtime / COCO object detection is live with an independent workflow, `media-yolo-*` Releases, ZIP-only assets, indexes, README history, and [YOLO Lab](web/src/content/docs/yolo-lab.mdx). The first Release, `media-yolo-all-2026-07-13-v1`, processed all 387 canonical images, observed detections in 313, and produced 1,533 boxes. See the [full contract](docs/YOLO_OBJECT_DETECTION_SPEC.md)."
en_added = en_yolo + "\n- GitHub Pages now separates build, deploy, and writeback: `site/` is a short-lived Pages artifact rather than tracked Git output, so deployment is no longer blocked by concurrent bot writeback races on `main`.\n- The three-workflow YOLOX + NanoDet-Plus direction now has a [`specified_not_implemented` specification](docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md): two inference artifacts are paired by exact run IDs, then an independent publisher creates a `media-detection-*` Release and Original/YOLOX/NanoDet comparison gallery."
replace_required(ROOT / "README.en.md", en_yolo, en_added)

Path(__file__).unlink()
