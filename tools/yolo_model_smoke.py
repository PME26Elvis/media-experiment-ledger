#!/usr/bin/env python3
"""Download the pinned YOLOX-Tiny model and verify real ONNX Runtime execution."""
from __future__ import annotations

import tempfile
import urllib.request
from pathlib import Path

from PIL import Image

from yolo_core import (
    YoloXSession,
    load_labels,
    load_model_lock,
    prepare_image,
    verify_model_and_labels,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    lock_path = ROOT / "object-detection" / "model-lock.json"
    lock = load_model_lock(lock_path)
    labels_path = ROOT / str(lock["labels_path"])
    labels = load_labels(labels_path)
    if len(labels) != 80:
        raise ValueError(f"Expected 80 COCO labels, got {len(labels)}")
    with tempfile.TemporaryDirectory() as temp:
        model_path = Path(temp) / "yolox_tiny.onnx"
        request = urllib.request.Request(
            str(lock["download_url"]),
            headers={"User-Agent": "media-experiment-ledger-yolo-smoke/1"},
        )
        with urllib.request.urlopen(request, timeout=180) as response, model_path.open(
            "wb"
        ) as target:
            while chunk := response.read(4 * 1024 * 1024):
                target.write(chunk)
        verify_model_and_labels(model_path, lock, labels_path)
        session = YoloXSession(model_path, threads=2)
        prepared = prepare_image(
            Image.new("RGB", (416, 416), "white"), (416, 416)
        )
        output, elapsed = session.infer(prepared.tensor)
        if output.ndim != 3 or output.shape[0] != 1 or output.shape[-1] != 85:
            raise ValueError(f"Unexpected real model output shape: {output.shape}")
        if output.shape[1] != 3549:
            raise ValueError(
                f"Expected 3549 YOLOX-Tiny rows, got {output.shape[1]}"
            )
        print(
            f"YOLOX-Tiny ONNX smoke passed: shape={output.shape}, "
            f"inference={elapsed:.3f}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
