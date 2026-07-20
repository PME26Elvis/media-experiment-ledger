#!/usr/bin/env python3
"""Run full-corpus YOLOX-Tiny inference and publish an independent media-yolo-* Release."""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import time
import traceback
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, __version__ as pillow_version

from yolo_core import (
    YoloXSession,
    load_labels,
    load_model_lock,
    postprocess_predictions,
    prepare_image,
    render_annotated,
    verify_model_and_labels,
)
from yolo_corpus import build_inventory, download_release_inputs, release_rows
from yolo_packages import package_analysis, summarize, write_json
from yolo_publish import publish_release, rebuild_history, update_readme_history


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def download_model(lock: dict[str, Any], destination: Path) -> float:
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    request = urllib.request.Request(
        str(lock["download_url"]),
        headers={"User-Agent": "media-experiment-ledger-yolo/1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response, destination.open(
        "wb"
    ) as target:
        shutil.copyfileobj(response, target, length=4 * 1024 * 1024)
    return time.perf_counter() - started


def source_indexes(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_release: dict[str, list[str]] = defaultdict(list)
    by_run: dict[str, list[str]] = defaultdict(list)
    by_prompt: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        digest = str(entry["image_sha256"])
        for source in entry.get("sources", []):
            release = str(source.get("release_tag") or "")
            run_id = str(source.get("run_id") or "")
            prompt_id = str(source.get("prompt_id") or "")
            if release:
                by_release[release].append(digest)
            if run_id:
                by_run[f"{release}/{run_id}"].append(digest)
            if prompt_id:
                by_prompt[prompt_id].append(digest)
    return {
        "by-release.json": {
            key: sorted(set(value)) for key, value in sorted(by_release.items())
        },
        "by-run.json": {
            key: sorted(set(value)) for key, value in sorted(by_run.items())
        },
        "by-prompt.json": {
            key: sorted(set(value)) for key, value in sorted(by_prompt.items())
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    total_started = time.perf_counter()
    output_root = args.output_dir.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    package_root = output_root / "package-root"
    detector_root = package_root / "object-detection" / "yolox-tiny"
    detector_root.mkdir(parents=True)
    model_lock_path = args.model_lock.resolve()
    model_lock = load_model_lock(model_lock_path)
    labels_path = (args.repo_root / str(model_lock["labels_path"])).resolve()
    labels = load_labels(labels_path)

    timings: dict[str, Any] = {}
    inventory_started = time.perf_counter()
    releases = release_rows(args.repo)
    if not releases:
        raise RuntimeError("No published media-exp-* Releases found")

    import tempfile

    with tempfile.TemporaryDirectory(prefix="yolo-corpus-") as temp:
        temp_root = Path(temp)
        release_roots = download_release_inputs(
            args.repo, releases, temp_root / "releases"
        )
        inventory = build_inventory(releases, release_roots, temp_root / "images")
        timings["inventory_and_archive_seconds"] = (
            time.perf_counter() - inventory_started
        )

        model_path = temp_root / "model" / "yolox_tiny.onnx"
        timings["model_download_seconds"] = download_model(model_lock, model_path)
        verify_model_and_labels(model_path, model_lock, labels_path)
        model_load_started = time.perf_counter()
        session = YoloXSession(model_path, threads=max(1, os.cpu_count() or 1))
        timings["model_load_seconds"] = time.perf_counter() - model_load_started

        shutil.copy2(model_lock_path, detector_root / "model-lock.json")
        shutil.copy2(labels_path, detector_root / "coco-80.json")
        write_json(detector_root / "corpus-manifest.json", inventory.as_dict())

        analysis_run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
        entries: list[dict[str, Any]] = []
        per_image_seconds: list[float] = []
        inference_seconds: list[float] = []
        render_seconds: list[float] = []
        started_at = utc_now()
        input_size = (
            int(model_lock["input_height"]),
            int(model_lock["input_width"]),
        )

        for number, corpus_image in enumerate(inventory.images, 1):
            image_started = time.perf_counter()
            digest = corpus_image.image_sha256
            sources = [alias.as_dict() for alias in corpus_image.aliases]
            relative_sidecar = (
                Path("object-detection/yolox-tiny/detections")
                / digest[:2]
                / digest[2:4]
                / f"{digest}.json"
            )
            relative_failure = (
                Path("object-detection/yolox-tiny/failures")
                / digest[:2]
                / digest[2:4]
                / f"{digest}.json"
            )
            relative_annotated = (
                Path("object-detection/yolox-tiny/annotated")
                / digest[:2]
                / digest[2:4]
                / f"{digest}.jpg"
            )
            try:
                with Image.open(corpus_image.path) as opened:
                    opened.load()
                    letterbox = prepare_image(opened, input_size)
                    raw_output, inference_elapsed = session.infer(letterbox.tensor)
                    inference_seconds.append(inference_elapsed)
                    detections = postprocess_predictions(
                        raw_output,
                        letterbox,
                        labels,
                        confidence_threshold=args.confidence_threshold,
                        nms_iou_threshold=args.nms_iou_threshold,
                        max_detections=args.max_detections,
                        input_size=input_size,
                    )
                    render_started = time.perf_counter()
                    render_meta = render_annotated(
                        letterbox.image,
                        detections,
                        package_root / relative_annotated,
                    )
                    render_seconds.append(time.perf_counter() - render_started)
                class_counts = Counter(
                    detection.class_name for detection in detections
                )
                detection_rows = [detection.as_dict() for detection in detections]
                sidecar = {
                    "schema_version": 1,
                    "analysis_type": "object_detection",
                    "status": "success",
                    "model": model_lock["model_family"],
                    "training_dataset": model_lock["training_dataset"],
                    "model_sha256": model_lock["sha256"],
                    "analysis_run_id": analysis_run_id,
                    "corpus_fingerprint": inventory.fingerprint,
                    "image_sha256": digest,
                    "width": corpus_image.width,
                    "height": corpus_image.height,
                    "sources": sources,
                    "preprocess": {
                        "scale": round(letterbox.scale, 8),
                        "pad_left": letterbox.pad_left,
                        "pad_top": letterbox.pad_top,
                        "input_width": input_size[1],
                        "input_height": input_size[0],
                    },
                    "thresholds": {
                        "confidence": args.confidence_threshold,
                        "nms_iou": args.nms_iou_threshold,
                        "max_detections": args.max_detections,
                    },
                    "detections": detection_rows,
                    "detection_count": len(detections),
                    "class_counts": dict(sorted(class_counts.items())),
                    "annotated_file": relative_annotated.as_posix(),
                    "annotated_preview": render_meta,
                }
                write_json(package_root / relative_sidecar, sidecar)
                entries.append(
                    {
                        **sidecar,
                        "sidecar_file": relative_sidecar.as_posix(),
                        "top_classes": [
                            name for name, _ in class_counts.most_common(5)
                        ],
                        "max_confidence": max(
                            (
                                float(item["confidence"])
                                for item in detection_rows
                            ),
                            default=0.0,
                        ),
                    }
                )
            except Exception as exc:
                failure = {
                    "schema_version": 1,
                    "analysis_type": "object_detection",
                    "status": "failure",
                    "image_sha256": digest,
                    "sources": sources,
                    "failure_phase": "decode_preprocess_inference_or_render",
                    "error_class": type(exc).__name__,
                    "error_message": str(exc)[:1000],
                    "analysis_run_id": analysis_run_id,
                    "model_sha256": model_lock["sha256"],
                    "recorded_at_utc": utc_now(),
                }
                write_json(package_root / relative_failure, failure)
                entries.append(
                    {**failure, "failure_file": relative_failure.as_posix()}
                )
            elapsed = time.perf_counter() - image_started
            per_image_seconds.append(elapsed)
            print(
                f"[{number}/{len(inventory.images)}] {digest[:12]} "
                f"{entries[-1]['status']} {elapsed:.3f}s",
                flush=True,
            )

        summary = summarize(entries)
        if summary["successful_images"] + summary["failed_images"] != len(
            inventory.images
        ):
            raise RuntimeError("YOLO coverage mismatch")
        failure_rate = summary["failed_images"] / len(inventory.images)
        if failure_rate > args.max_failure_rate:
            raise RuntimeError(
                f"YOLO failure rate {failure_rate:.2%} exceeds "
                f"{args.max_failure_rate:.2%}"
            )

        total_image_seconds = sum(per_image_seconds)
        timings.update(
            {
                "inference_seconds": sum(inference_seconds),
                "render_seconds": sum(render_seconds),
                "per_image_p50_seconds": percentile(per_image_seconds, 0.50),
                "per_image_p95_seconds": percentile(per_image_seconds, 0.95),
                "mean_images_per_second": (
                    len(inventory.images) / total_image_seconds
                    if total_image_seconds
                    else 0.0
                ),
                "runner_cpu_count": os.cpu_count() or 0,
            }
        )
        try:
            import resource

            timings["peak_rss_kib"] = int(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            )
        except Exception:
            timings["peak_rss_kib"] = None

        for name, value in source_indexes(entries).items():
            write_json(detector_root / "source-index" / name, value)
        write_json(detector_root / "summaries" / "global.json", summary)
        write_json(
            detector_root / "summaries" / "classes.json",
            summary["top_classes"],
        )
        write_json(
            detector_root / "summaries" / "prompts.json",
            summary["images_by_prompt"],
        )
        write_json(
            detector_root / "summaries" / "releases.json",
            summary["images_by_release"],
        )
        write_json(
            detector_root / "summaries" / "empty-detections.json",
            [
                entry["image_sha256"]
                for entry in entries
                if entry.get("status") == "success"
                and not entry.get("detections")
            ],
        )
        write_json(detector_root / "summaries" / "timing.json", timings)

        report = {
            "schema_version": 1,
            "status": "published" if args.publish else "built",
            "analysis_run_id": analysis_run_id,
            "generated_at_utc": utc_now(),
            "started_at_utc": started_at,
            "repo": args.repo,
            "code_sha": os.environ.get("GITHUB_SHA", "local"),
            "model_family": model_lock["model_family"],
            "model_sha256": model_lock["sha256"],
            "labels_sha256": model_lock["labels_sha256"],
            "runtime": "ONNX Runtime CPUExecutionProvider",
            "python": platform.python_version(),
            "pillow": pillow_version,
            "date_from": inventory.date_from,
            "date_to": inventory.date_to,
            "latest_date": inventory.latest_date,
            "release_count": len(inventory.releases),
            "source_release_tags": [
                row["tagName"] for row in inventory.releases
            ],
            "source_image_files": inventory.source_file_count,
            "canonical_unique_images": len(inventory.images),
            "quarantined_runs": inventory.quarantined_runs,
            "corpus_fingerprint": inventory.fingerprint,
            "thresholds": {
                "confidence": args.confidence_threshold,
                "nms_iou": args.nms_iou_threshold,
                "max_detections": args.max_detections,
            },
            "summary": summary,
            "timing": timings,
            "rebuild_policy": (
                "complete corpus from scratch; no persistent "
                "state/cache/published-result reuse"
            ),
        }
        write_json(detector_root / "analysis-report.json", report)
        write_json(detector_root / "entries.json", entries)

        packaging_started = time.perf_counter()
        package_analysis(output_root, package_root, entries)
        timings["package_seconds"] = time.perf_counter() - packaging_started
        timings["total_seconds"] = time.perf_counter() - total_started
        write_json(detector_root / "summaries" / "timing.json", timings)
        report["timing"] = timings
        write_json(detector_root / "analysis-report.json", report)
        shutil.rmtree(output_root / "release-assets")
        package_analysis(output_root, package_root, entries)

        publication = publish_release(
            args.repo,
            output_root,
            report,
            entries,
            package_root,
            args.preview_root,
            preview_repo_root=args.preview_repo_root,
            publish=args.publish,
        )
        latest = {
            "schema_version": 1,
            "status": "published" if args.publish else "built",
            "generated_at_utc": utc_now(),
            "analysis_run_id": analysis_run_id,
            "release_tag": publication["tag"],
            "release_url": publication["release_url"],
            "date_from": inventory.date_from,
            "date_to": inventory.date_to,
            "release_count": len(inventory.releases),
            "corpus_fingerprint": inventory.fingerprint,
            "model": model_lock["model_family"],
            "model_sha256": model_lock["sha256"],
            "thresholds": report["thresholds"],
            "summary": summary,
            "entries": entries,
            "interpretation": (
                "COCO-pretrained detector observations are not ground truth; "
                "missing detections do not imply no objects."
            ),
        }
        write_json(args.index, latest)
        write_json(args.web_index, latest)
        if args.publish:
            history = rebuild_history(args.repo, args.history)
            update_readme_history(args.readme, history, english=False)
            update_readme_history(args.readme_en, history, english=True)
        return {"report": report, "publication": publication, "latest": latest}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", required=True)
    value.add_argument("--repo-root", type=Path, default=Path.cwd())
    value.add_argument(
        "--model-lock",
        type=Path,
        default=Path("object-detection/model-lock.json"),
    )
    value.add_argument(
        "--output-dir", type=Path, default=Path("object-detection/output")
    )
    value.add_argument(
        "--index", type=Path, default=Path("data/yolo/latest.json")
    )
    value.add_argument(
        "--history", type=Path, default=Path("data/yolo/history.json")
    )
    value.add_argument(
        "--web-index",
        type=Path,
        default=Path("web/public/data/yolo/latest.json"),
    )
    value.add_argument(
        "--preview-root",
        type=Path,
        default=Path("web/public/data/yolo/previews"),
    )
    value.add_argument(
        "--preview-repo-root", default="web/public/data/yolo/previews"
    )
    value.add_argument("--readme", type=Path, default=Path("README.md"))
    value.add_argument("--readme-en", type=Path, default=Path("README.en.md"))
    value.add_argument("--confidence-threshold", type=float, default=0.25)
    value.add_argument("--nms-iou-threshold", type=float, default=0.45)
    value.add_argument("--max-detections", type=int, default=100)
    value.add_argument("--max-failure-rate", type=float, default=0.01)
    value.add_argument("--publish", action="store_true")
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    arguments.repo_root = arguments.repo_root.resolve()
    try:
        result = run(arguments)
    except Exception:
        traceback.print_exc()
        raise
    print(
        json.dumps(
            {
                "release_tag": result["publication"]["tag"],
                "published": result["publication"]["published"],
                "images": result["report"]["summary"]["expected_images"],
                "detections": result["report"]["summary"]["total_detections"],
            },
            indent=2,
        )
    )
