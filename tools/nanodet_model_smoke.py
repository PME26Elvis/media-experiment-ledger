#!/usr/bin/env python3
"""Download the pinned official NanoDet ONNX and execute a real ORT shape smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from prepare_nanodet_model import prepare

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="nanodet-smoke-") as temp:
        report = prepare(
            ROOT / "object-detection" / "nanodet-model-lock.json",
            Path(temp) / "nanodet-plus-m_320.onnx",
            ROOT / "object-detection" / "coco-80.json",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
