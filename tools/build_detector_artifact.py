#!/usr/bin/env python3
"""Build one full-corpus detector workflow artifact without publishing a Release."""
from __future__ import annotations

import argparse
import hashlib
import html
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
from typing import Any, Sequence

from PIL import Image, __version__ as pillow_version

from nanodet_core import (
    NanoDetSession,
    load_lock as load_nanodet_lock,
    postprocess_predictions as nanodet_postprocess,
    prepare_image as nanodet_prepare,
    sha256_file,
    verify_labels as verify_nanodet_labels,
)
from yolo_core import (
    YoloXSession,
    load_labels,
    load_model_lock,
    postprocess_predictions as yolox_postprocess,
    prepare_image as yolox_prepare,
    render_annotated,
    verify_model_and_labels,
)
from yolo_corpus import build_inventory, download_release_inputs, release_rows
from yolo_packages import deterministic_zip, split_paths, summarize, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def download(url: str, destination: Path) -> float:
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    request = urllib.request.Request(
        url, headers={"User-Agent": "media-experiment-ledger-detector/1"}
    )
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target, length=4 * 1024 * 1024)
    return time.perf_counter() - started


def source_indexes(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    indexes: dict[str, dict[str, list[str]]] = {
        "by-release.json": defaultdict(list),
        "by-run.json": defaultdict(list),
        "by-prompt.json": defaultdict(list),
    }
    for entry in entries:
        digest = str(entry.get("image_sha256") or "")
        for source in entry.get("sources", []):
            release = str(source.get("release_tag") or "")
            run_id = str(source.get("run_id") or "")
            prompt_id = str(source.get("prompt_id") or "")
            if release:
                indexes["by-release.json"][release].append(digest)
            if run_id:
                indexes["by-run.json"][f"{release}/{run_id}"].append(digest)
            if prompt_id:
                indexes["by-prompt.json"][prompt_id].append(digest)
    return {
        name: {key: sorted(set(values)) for key, values in sorted(rows.items())}
        for name, rows in indexes.items()
    }


def build_gallery(detector_root: Path, detector_id: str, entries: Sequence[dict[str, Any]]) -> Path:
    gallery = detector_root / "offline-gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    write_json(gallery / "data.json", list(entries))
    cards: list[str] = []
    for entry in entries:
        if entry.get("status") != "success":
            continue
        annotated = Path(str(entry["annotated_file"])).relative_to(
            Path("object-detection") / detector_id
        )
        classes = ", ".join(entry.get("top_classes", [])) or "none"
        cards.append(
            "<article data-search='{}'><img loading='lazy' src='../{}' alt='annotated'>"
            "<h2>{}</h2><p>{} detections · {}</p></article>".format(
                html.escape((classes + " " + str(entry.get("image_sha256"))).lower()),
                html.escape(annotated.as_posix()),
                html.escape(str(entry.get("image_sha256", ""))[:12]),
                int(entry.get("detection_count") or 0),
                html.escape(classes),
            )
        )
    (gallery / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{html.escape(detector_id)} detection gallery</title><style>body{{font-family:system-ui;background:#07101d;color:#eef6ff;margin:0;padding:1rem}}"
        "header,.grid{max-width:90rem;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}"
        "article{background:#101c2d;border:1px solid #28425e;border-radius:1rem;overflow:hidden;padding-bottom:1rem}img{width:100%;display:block}"
        "h2,p{margin:.7rem 1rem}input{padding:.7rem;width:min(30rem,90%)}</style></head><body>"
        f"<header><h1>{html.escape(detector_id)} / COCO full-corpus gallery</h1>"
        "<p>Detector observations are not ground truth.</p><input id='q' placeholder='Filter class or SHA'></header>"
        "<main class='grid'>" + "".join(cards) + "</main>"
        "<script>q.oninput=()=>document.querySelectorAll('article').forEach(x=>x.hidden=!x.dataset.search.includes(q.value.toLowerCase()))</script>"
        "</body></html>",
        encoding="utf-8",
    )
    return gallery


def package_detector(
    output_root: Path,
    package_root: Path,
    detector_root: Path,
    detector_id: str,
    entries: Sequence[dict[str, Any]],
    *,
    max_part_bytes: int = int(1.75 * 1024**3),
) -> list[dict[str, Any]]:
    release_root = output_root / "release-assets"
    release_root.mkdir(parents=True, exist_ok=True)
    gallery = build_gallery(detector_root, detector_id, entries)
    all_files = [path for path in detector_root.rglob("*") if path.is_file()]
    detections = [
        path for path in all_files
        if "/detections/" in path.as_posix() or "/failures/" in path.as_posix()
    ]
    annotated = [path for path in all_files if "/annotated/" in path.as_posix()]
    gallery_files = [path for path in gallery.rglob("*") if path.is_file()]
    metadata = [
        path for path in all_files
        if path not in detections and path not in annotated and path not in gallery_files
    ]
    prefix = "yolox" if detector_id == "yolox-tiny" else "nanodet"
    plans: list[tuple[str, list[Path]]] = [(f"{prefix}-coco-metadata.zip", metadata)]
    for label, paths in (
        (f"{prefix}-coco-detections", detections),
        (f"{prefix}-coco-annotated", annotated),
        (f"{prefix}-coco-complete", all_files),
    ):
        for number, part in enumerate(split_paths(paths, max_part_bytes), 1):
            plans.append((f"{label}-part{number:03d}.zip", part))
    plans.append((f"{prefix}-coco-offline-gallery.zip", gallery_files))
    manifest: list[dict[str, Any]] = []
    for name, paths in plans:
        destination = release_root / name
        deterministic_zip(destination, package_root, paths)
        manifest.append(
            {
                "name": name,
                "size_bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "file_count": len(paths),
            }
        )
    return manifest


def run(args: argparse.Namespace) -> dict[str, Any]:
    started_total = time.perf_counter()
    detector_id = args.detector
    if detector_id not in {"yolox-tiny", "nanodet-plus-m-320"}:
        raise ValueError(f"Unsupported detector: {detector_id}")
    output_root = args.output_dir.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    package_root = output_root / "package-root"
    detector_root = package_root / "object-detection" / detector_id
    detector_root.mkdir(parents=True)
    labels_path = args.labels.resolve()
    labels = load_labels(labels_path)

    import tempfile
    timings: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix=f"{detector_id}-corpus-") as temp:
        temp_root = Path(temp)
        inventory_started = time.perf_counter()
        releases = release_rows(args.repo)
        roots = download_release_inputs(args.repo, releases, temp_root / "releases")
        inventory = build_inventory(releases, roots, temp_root / "images")
        timings["inventory_and_archive_seconds"] = time.perf_counter() - inventory_started
        write_json(detector_root / "corpus-manifest.json", inventory.as_dict())
        originals = package_root / "corpus" / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        for image in inventory.images:
            shutil.copy2(image.path, originals / f"{image.image_sha256}{image.path.suffix.lower()}")

        if detector_id == "yolox-tiny":
            lock_path = args.yolox_lock.resolve()
            lock = load_model_lock(lock_path)
            model_path = temp_root / "models" / "yolox-tiny.onnx"
            timings["model_download_seconds"] = download(str(lock["download_url"]), model_path)
            verify_model_and_labels(model_path, lock, labels_path)
            session: Any = YoloXSession(model_path, threads=max(1, os.cpu_count() or 1))
            model_sha = str(lock["sha256"])
            model_family = str(lock["model_family"])
            shutil.copy2(lock_path, detector_root / "model-lock.json")
        else:
            lock_path = args.nanodet_lock.resolve()
            lock = load_nanodet_lock(lock_path)
            verify_nanodet_labels(labels_path, lock)
            if not args.model_path:
                raise ValueError("--model-path is required for NanoDet")
            model_path = args.model_path.resolve()
            if not model_path.exists():
                raise FileNotFoundError(model_path)
            session = NanoDetSession(model_path, threads=max(1, os.cpu_count() or 1))
            model_sha = sha256_file(model_path)
            model_family = str(lock["model_family"])
            shutil.copy2(lock_path, detector_root / "model-lock.json")
            if args.model_report and args.model_report.exists():
                shutil.copy2(args.model_report, detector_root / "model-export-report.json")
        shutil.copy2(labels_path, detector_root / "coco-80.json")

        analysis_run_id = f"{detector_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        entries: list[dict[str, Any]] = []
        per_image: list[float] = []
        inference_times: list[float] = []
        started_at = utc_now()
        for number, corpus_image in enumerate(inventory.images, 1):
            image_started = time.perf_counter()
            digest = corpus_image.image_sha256
            sources = [alias.as_dict() for alias in corpus_image.aliases]
            relative = Path("object-detection") / detector_id
            sidecar_rel = relative / "detections" / digest[:2] / digest[2:4] / f"{digest}.json"
            failure_rel = relative / "failures" / digest[:2] / digest[2:4] / f"{digest}.json"
            annotated_rel = relative / "annotated" / digest[:2] / digest[2:4] / f"{digest}.jpg"
            try:
                with Image.open(corpus_image.path) as opened:
                    opened.load()
                    if detector_id == "yolox-tiny":
                        prepared = yolox_prepare(
                            opened,
                            (int(lock["input_height"]), int(lock["input_width"])),
                        )
                        raw, elapsed = session.infer(prepared.tensor)
                        detections = yolox_postprocess(
                            raw,
                            prepared,
                            labels,
                            confidence_threshold=args.confidence_threshold,
                            nms_iou_threshold=args.nms_iou_threshold,
                            max_detections=args.max_detections,
                            input_size=(int(lock["input_height"]), int(lock["input_width"])),
                        )
                        source_image = prepared.image
                        preprocess = {
                            "input_width": int(lock["input_width"]),
                            "input_height": int(lock["input_height"]),
                            "scale": prepared.scale,
                            "pad_left": prepared.pad_left,
                            "pad_top": prepared.pad_top,
                        }
                    else:
                        prepared = nanodet_prepare(opened, lock)
                        raw, elapsed = session.infer(prepared.tensor)
                        detections = nanodet_postprocess(
                            raw,
                            prepared,
                            labels,
                            lock,
                            confidence_threshold=args.confidence_threshold,
                            nms_iou_threshold=args.nms_iou_threshold,
                            max_detections=args.max_detections,
                        )
                        source_image = prepared.image
                        preprocess = {
                            "input_width": prepared.input_width,
                            "input_height": prepared.input_height,
                            "keep_ratio": False,
                            "color_order": "BGR",
                        }
                    inference_times.append(elapsed)
                    render_annotated(source_image, detections, package_root / annotated_rel)
                class_counts = Counter(item.class_name for item in detections)
                detection_rows = [item.as_dict() for item in detections]
                entry = {
                    "schema_version": 1,
                    "analysis_type": "object_detection",
                    "status": "success",
                    "detector_id": detector_id,
                    "model": model_family,
                    "model_sha256": model_sha,
                    "analysis_batch_id": args.analysis_batch_id,
                    "analysis_run_id": analysis_run_id,
                    "corpus_fingerprint": inventory.fingerprint,
                    "image_sha256": digest,
                    "width": corpus_image.width,
                    "height": corpus_image.height,
                    "sources": sources,
                    "preprocess": preprocess,
                    "thresholds": {
                        "confidence": args.confidence_threshold,
                        "nms_iou": args.nms_iou_threshold,
                        "max_detections": args.max_detections,
                    },
                    "detections": detection_rows,
                    "detection_count": len(detections),
                    "class_counts": dict(sorted(class_counts.items())),
                    "annotated_file": annotated_rel.as_posix(),
                    "sidecar_file": sidecar_rel.as_posix(),
                    "top_classes": [name for name, _ in class_counts.most_common(5)],
                    "max_confidence": max((float(row["confidence"]) for row in detection_rows), default=0.0),
                }
                write_json(package_root / sidecar_rel, entry)
            except Exception as exc:
                entry = {
                    "schema_version": 1,
                    "analysis_type": "object_detection",
                    "status": "failure",
                    "detector_id": detector_id,
                    "model_sha256": model_sha,
                    "analysis_batch_id": args.analysis_batch_id,
                    "analysis_run_id": analysis_run_id,
                    "corpus_fingerprint": inventory.fingerprint,
                    "image_sha256": digest,
                    "sources": sources,
                    "failure_phase": "decode_preprocess_inference_or_render",
                    "error_class": type(exc).__name__,
                    "error_message": str(exc)[:1000],
                    "failure_file": failure_rel.as_posix(),
                }
                write_json(package_root / failure_rel, entry)
            entries.append(entry)
            elapsed_total = time.perf_counter() - image_started
            per_image.append(elapsed_total)
            print(f"[{number}/{len(inventory.images)}] {detector_id} {digest[:12]} {entry['status']} {elapsed_total:.3f}s", flush=True)

        summary = summarize(entries)
        if summary["successful_images"] + summary["failed_images"] != len(inventory.images):
            raise RuntimeError("Detector coverage mismatch")
        failure_rate = summary["failed_images"] / len(inventory.images)
        if failure_rate > args.max_failure_rate:
            raise RuntimeError(
                f"{detector_id} failure rate {failure_rate:.2%} exceeds {args.max_failure_rate:.2%}"
            )
        timings.update(
            {
                "inference_seconds": sum(inference_times),
                "per_image_p50_seconds": percentile(per_image, 0.50),
                "per_image_p95_seconds": percentile(per_image, 0.95),
                "mean_images_per_second": len(per_image) / sum(per_image) if sum(per_image) else 0.0,
                "runner_cpu_count": os.cpu_count() or 0,
            }
        )
        for name, value in source_indexes(entries).items():
            write_json(detector_root / "source-index" / name, value)
        write_json(detector_root / "entries.json", entries)
        write_json(detector_root / "summaries" / "global.json", summary)
        write_json(detector_root / "summaries" / "timing.json", timings)
        report = {
            "schema_version": 1,
            "status": "built",
            "detector_id": detector_id,
            "model_family": model_family,
            "model_sha256": model_sha,
            "labels_sha256": str(lock["labels_sha256"]),
            "analysis_batch_id": args.analysis_batch_id,
            "analysis_run_id": analysis_run_id,
            "generated_at_utc": utc_now(),
            "started_at_utc": started_at,
            "repo": args.repo,
            "code_sha": os.environ.get("GITHUB_SHA", "local"),
            "runtime": "ONNX Runtime CPUExecutionProvider",
            "python": platform.python_version(),
            "pillow": pillow_version,
            "date_from": inventory.date_from,
            "date_to": inventory.date_to,
            "latest_date": inventory.latest_date,
            "release_count": len(inventory.releases),
            "source_release_tags": [row["tagName"] for row in inventory.releases],
            "canonical_image_count": len(inventory.images),
            "canonical_image_sha256": [image.image_sha256 for image in inventory.images],
            "source_image_files": inventory.source_file_count,
            "quarantined_runs": inventory.quarantined_runs,
            "quarantine_policy_digest": inventory.as_dict()["quarantine_policy_digest"],
            "corpus_fingerprint": inventory.fingerprint,
            "thresholds": {
                "confidence": args.confidence_threshold,
                "nms_iou": args.nms_iou_threshold,
                "max_detections": args.max_detections,
            },
            "summary": summary,
            "timing": timings,
            "rebuild_policy": "complete corpus from scratch; no persistent state/cache/published-result reuse",
        }
        write_json(detector_root / "analysis-report.json", report)
        assets = package_detector(output_root, package_root, detector_root, detector_id, entries)
        timings["total_seconds"] = time.perf_counter() - started_total
        report["timing"] = timings
        write_json(detector_root / "analysis-report.json", report)
        # Repackage metadata/complete so timing and report hashes are final.
        shutil.rmtree(output_root / "release-assets")
        assets = package_detector(output_root, package_root, detector_root, detector_id, entries)
        completion = {
            "schema_version": 1,
            "status": "success",
            "analysis_batch_id": args.analysis_batch_id,
            "detector_id": detector_id,
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "head_sha": os.environ.get("GITHUB_SHA", "local"),
            "corpus_fingerprint": inventory.fingerprint,
            "quarantine_policy_digest": report["quarantine_policy_digest"],
            "source_release_tags": report["source_release_tags"],
            "date_from": inventory.date_from,
            "date_to": inventory.date_to,
            "latest_date": inventory.latest_date,
            "canonical_image_count": len(inventory.images),
            "canonical_image_sha256": report["canonical_image_sha256"],
            "successful_image_count": summary["successful_images"],
            "failed_image_count": summary["failed_images"],
            "labels_sha256": report["labels_sha256"],
            "model_sha256": model_sha,
            "thresholds": report["thresholds"],
            "package_files": assets,
        }
        write_json(output_root / "completion-manifest.json", completion)
        return {"completion": completion, "report": report}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", required=True)
    value.add_argument("--analysis-batch-id", required=True)
    value.add_argument("--detector", choices=["yolox-tiny", "nanodet-plus-m-320"], required=True)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--model-path", type=Path)
    value.add_argument("--model-report", type=Path)
    value.add_argument("--labels", type=Path, default=Path("object-detection/coco-80.json"))
    value.add_argument("--yolox-lock", type=Path, default=Path("object-detection/model-lock.json"))
    value.add_argument("--nanodet-lock", type=Path, default=Path("object-detection/nanodet-model-lock.json"))
    value.add_argument("--confidence-threshold", type=float, default=0.25)
    value.add_argument("--nms-iou-threshold", type=float, default=0.45)
    value.add_argument("--max-detections", type=int, default=100)
    value.add_argument("--max-failure-rate", type=float, default=0.01)
    return value


if __name__ == "__main__":
    args = parser().parse_args()
    try:
        result = run(args)
    except Exception:
        traceback.print_exc()
        raise
    print(json.dumps(result["completion"], ensure_ascii=False, indent=2))
