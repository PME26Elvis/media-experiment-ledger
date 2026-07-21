#!/usr/bin/env python3
"""Download, verify and export the pinned NanoDet checkpoint to fixed-shape ONNX."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from nanodet_core import load_lock, sha256_file, verify_checkpoint, verify_labels


def command(args: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}"
        )
    return result


def download(url: str, destination: Path) -> float:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": "media-experiment-ledger-nanodet/1"}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target, length=4 * 1024 * 1024)
    return time.perf_counter() - started


def prepare(
    lock_path: Path,
    upstream_root: Path,
    output_path: Path,
    labels_path: Path,
    *,
    allow_unpinned: bool = False,
) -> dict[str, Any]:
    lock = load_lock(lock_path)
    verify_labels(labels_path, lock)
    checkpoint = output_path.parent / str(lock["checkpoint_asset"])
    download_seconds = download(str(lock["checkpoint_url"]), checkpoint)
    checkpoint_sha = verify_checkpoint(checkpoint, lock, allow_unpinned=allow_unpinned)
    expected_tag = str(lock["upstream_tag"])
    actual_tag = command(["git", "describe", "--tags", "--exact-match"], cwd=upstream_root).stdout.strip()
    if actual_tag != expected_tag:
        raise RuntimeError(f"NanoDet upstream tag mismatch: expected {expected_tag}, got {actual_tag}")
    config = upstream_root / str(lock["config_path"])
    if not config.exists():
        raise FileNotFoundError(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_started = time.perf_counter()
    result = command(
        [
            "python",
            str(upstream_root / "tools" / "export_onnx.py"),
            "--cfg_path",
            str(config),
            "--model_path",
            str(checkpoint),
            "--out_path",
            str(output_path),
            "--input_shape",
            f"{lock['input_height']},{lock['input_width']}",
        ],
        cwd=upstream_root,
    )
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"NanoDet ONNX export did not produce {output_path}\n{result.stdout}")
    return {
        "schema_version": 1,
        "model_family": lock["model_family"],
        "upstream_tag": actual_tag,
        "checkpoint_asset": lock["checkpoint_asset"],
        "checkpoint_size_bytes": checkpoint.stat().st_size,
        "checkpoint_sha256": checkpoint_sha,
        "onnx_size_bytes": output_path.stat().st_size,
        "onnx_sha256": sha256_file(output_path),
        "download_seconds": download_seconds,
        "export_seconds": time.perf_counter() - export_started,
        "export_log_tail": result.stdout.splitlines()[-20:],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--lock", type=Path, default=Path("object-detection/nanodet-model-lock.json"))
    value.add_argument("--upstream", type=Path, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--labels", type=Path, default=Path("object-detection/coco-80.json"))
    value.add_argument("--report", type=Path)
    value.add_argument("--allow-unpinned", action="store_true")
    return value


if __name__ == "__main__":
    args = parser().parse_args()
    report = prepare(
        args.lock.resolve(),
        args.upstream.resolve(),
        args.output.resolve(),
        args.labels.resolve(),
        allow_unpinned=args.allow_unpinned,
    )
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    print(text, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
