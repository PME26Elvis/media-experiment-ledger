#!/usr/bin/env python3
"""Download and verify the pinned official NanoDet ONNX model."""
from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from nanodet_core import load_lock, sha256_file, verify_checkpoint, verify_labels


def download(url: str, destination: Path) -> float:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": "media-experiment-ledger-nanodet/2"}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target, length=4 * 1024 * 1024)
    return time.perf_counter() - started


def prepare(
    lock_path: Path,
    output_path: Path,
    labels_path: Path,
    *,
    allow_unpinned: bool = False,
) -> dict[str, Any]:
    lock = load_lock(lock_path)
    verify_labels(labels_path, lock)
    download_seconds = download(str(lock["download_url"]), output_path)
    model_sha = verify_checkpoint(output_path, lock, allow_unpinned=allow_unpinned)
    expected_size = int(lock.get("expected_size_bytes") or lock.get("expected_checkpoint_size_bytes") or 0)
    if expected_size and output_path.stat().st_size != expected_size:
        raise ValueError(
            f"NanoDet ONNX size mismatch: expected {expected_size}, got {output_path.stat().st_size}"
        )

    try:
        import onnxruntime as ort
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("onnxruntime is required for NanoDet model verification") from exc
    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    input_meta = session.get_inputs()[0]
    started = time.perf_counter()
    output = session.run(
        None,
        {
            input_meta.name: np.zeros(
                (1, 3, int(lock["input_height"]), int(lock["input_width"])),
                dtype=np.float32,
            )
        },
    )[0]
    inference_seconds = time.perf_counter() - started
    expected_shape = [1, 2125, 112]
    if list(output.shape) != expected_shape:
        raise ValueError(
            f"Unexpected NanoDet ONNX output shape: expected {expected_shape}, got {list(output.shape)}"
        )
    return {
        "schema_version": 1,
        "model_family": lock["model_family"],
        "upstream_tag": lock["upstream_tag"],
        "upstream_commit": lock["upstream_commit"],
        "asset": lock["model_asset"],
        "asset_url": lock["download_url"],
        "size_bytes": output_path.stat().st_size,
        "sha256": model_sha,
        "input_name": input_meta.name,
        "input_shape": [1, 3, int(lock["input_height"]), int(lock["input_width"])],
        "output_shape": list(output.shape),
        "download_seconds": download_seconds,
        "smoke_inference_seconds": inference_seconds,
        "supply_chain_policy": lock["supply_chain_policy"],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--lock", type=Path, default=Path("object-detection/nanodet-model-lock.json"))
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--labels", type=Path, default=Path("object-detection/coco-80.json"))
    value.add_argument("--report", type=Path)
    value.add_argument("--allow-unpinned", action="store_true")
    return value


if __name__ == "__main__":
    args = parser().parse_args()
    report = prepare(
        args.lock.resolve(),
        args.output.resolve(),
        args.labels.resolve(),
        allow_unpinned=args.allow_unpinned,
    )
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(text, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
