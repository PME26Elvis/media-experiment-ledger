#!/usr/bin/env python3
"""Validate exact detector artifacts, compare them and publish media-detection-* outputs."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont, ImageOps

from yolo_packages import deterministic_zip, sha256_file, split_paths, write_json

TAG_RE = re.compile(r"^media-detection-all-(\d{4}-\d{2}-\d{2})-v(\d+)$")
DISCLAIMER = (
    "These are observations from two COCO-pretrained detectors, not ground-truth "
    "labels or an accuracy benchmark. Agreement does not prove correctness, and "
    "disagreement does not identify which detector is correct."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_tree(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Artifact contains a symlink: {path}")
        path.resolve().relative_to(root.resolve())


def validate_artifact(root: Path, expected_detector: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    safe_tree(root)
    manifest_path = root / "completion-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("status") != "success":
        raise ValueError(f"Artifact completion manifest is not successful: {root}")
    if manifest.get("detector_id") != expected_detector:
        raise ValueError(
            f"Detector mismatch for {root}: expected {expected_detector}, got {manifest.get('detector_id')}"
        )
    required = {
        "analysis_batch_id", "corpus_fingerprint", "quarantine_policy_digest",
        "source_release_tags", "canonical_image_sha256", "labels_sha256",
        "model_sha256", "thresholds", "package_files",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"Completion manifest missing: {', '.join(missing)}")
    assets = root / "release-assets"
    for item in manifest["package_files"]:
        name = str(item.get("name") or "")
        if not name.endswith(".zip") or Path(name).name != name:
            raise ValueError(f"Unsafe or non-ZIP package name: {name}")
        path = assets / name
        if not path.exists():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item["size_bytes"]):
            raise ValueError(f"Package size mismatch: {path}")
        if sha256_file(path) != str(item["sha256"]):
            raise ValueError(f"Package SHA-256 mismatch: {path}")
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Package CRC failure {path}: {bad}")
            for member in archive.infolist():
                candidate = Path(member.filename)
                if candidate.is_absolute() or ".." in candidate.parts:
                    raise ValueError(f"Unsafe ZIP member in {path}: {member.filename}")
    entries_path = root / "package-root" / "object-detection" / expected_detector / "entries.json"
    entries = read_json(entries_path)
    if not isinstance(entries, list):
        raise ValueError(f"Detector entries are not a list: {entries_path}")
    seen = {str(entry.get("image_sha256") or "") for entry in entries}
    expected = set(map(str, manifest["canonical_image_sha256"]))
    if seen != expected:
        raise ValueError(
            f"Detector sidecar coverage mismatch for {expected_detector}: "
            f"missing={len(expected-seen)}, extra={len(seen-expected)}"
        )
    failures = [entry for entry in entries if entry.get("status") != "success"]
    if failures:
        raise ValueError(
            f"Initial combined publication requires zero detector failures; "
            f"{expected_detector} has {len(failures)}"
        )
    return manifest, entries


def require_pair(yolox: dict[str, Any], nanodet: dict[str, Any]) -> None:
    for key in (
        "analysis_batch_id", "corpus_fingerprint", "quarantine_policy_digest",
        "source_release_tags", "canonical_image_sha256", "labels_sha256", "thresholds",
    ):
        if yolox.get(key) != nanodet.get(key):
            raise ValueError(f"Detector artifacts do not match for {key}")
    if yolox.get("detector_id") == nanodet.get("detector_id"):
        raise ValueError("Detector IDs must be distinct")


def iou(left: Sequence[float], right: Sequence[float]) -> float:
    x1, y1 = max(left[0], right[0]), max(left[1], right[1])
    x2, y2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


def greedy_matches(
    yolox: Sequence[dict[str, Any]], nanodet: Sequence[dict[str, Any]], threshold: float = 0.5
) -> tuple[list[dict[str, Any]], list[int], list[int]]:
    candidates: list[tuple[float, float, int, int]] = []
    for yi, left in enumerate(yolox):
        for ni, right in enumerate(nanodet):
            if int(left["class_id"]) != int(right["class_id"]):
                continue
            overlap = iou(left["bbox_xyxy"], right["bbox_xyxy"])
            if overlap >= threshold:
                confidence = float(left["confidence"]) + float(right["confidence"])
                candidates.append((-overlap, -confidence, yi, ni))
    used_y, used_n, matches = set(), set(), []
    for negative_iou, _, yi, ni in sorted(candidates):
        if yi in used_y or ni in used_n:
            continue
        used_y.add(yi)
        used_n.add(ni)
        matches.append(
            {
                "class_id": int(yolox[yi]["class_id"]),
                "class_name": yolox[yi]["class_name"],
                "iou": round(-negative_iou, 6),
                "yolox_confidence": float(yolox[yi]["confidence"]),
                "nanodet_confidence": float(nanodet[ni]["confidence"]),
                "confidence_delta": round(
                    float(yolox[yi]["confidence"]) - float(nanodet[ni]["confidence"]), 6
                ),
                "yolox_index": yi,
                "nanodet_index": ni,
            }
        )
    return matches, sorted(set(range(len(yolox))) - used_y), sorted(set(range(len(nanodet))) - used_n)


def compare_entry(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    yolox = list(left.get("detections") or [])
    nanodet = list(right.get("detections") or [])
    left_classes = {str(item["class_name"]) for item in yolox}
    right_classes = {str(item["class_name"]) for item in nanodet}
    union = left_classes | right_classes
    intersection = left_classes & right_classes
    matches, unmatched_left, unmatched_right = greedy_matches(yolox, nanodet)
    matched_ious = [float(item["iou"]) for item in matches]
    count_denominator = max(len(yolox), len(nanodet), 1)
    unmatched_denominator = max(len(yolox) + len(nanodet), 1)
    class_disagreement = 1.0 - (len(intersection) / len(union) if union else 1.0)
    count_difference = abs(len(yolox) - len(nanodet)) / count_denominator
    unmatched_fraction = (len(unmatched_left) + len(unmatched_right)) / unmatched_denominator
    mean_iou = sum(matched_ious) / len(matched_ious) if matched_ious else 0.0
    box_disagreement = 1.0 - mean_iou if (yolox or nanodet) else 0.0
    score = (
        0.35 * class_disagreement
        + 0.25 * count_difference
        + 0.25 * unmatched_fraction
        + 0.15 * box_disagreement
    )
    if not yolox and not nanodet:
        state = "both-empty"
    elif yolox and not nanodet:
        state = "yolox-only-nonempty"
    elif nanodet and not yolox:
        state = "nanodet-only-nonempty"
    else:
        state = "both-nonempty"
    source = (left.get("sources") or [{}])[0]
    return {
        "schema_version": 1,
        "image_sha256": left["image_sha256"],
        "prompt_id": source.get("prompt_id") or "unknown",
        "category": source.get("category") or "uncategorized",
        "sources": left.get("sources") or [],
        "state": state,
        "yolox_detection_count": len(yolox),
        "nanodet_detection_count": len(nanodet),
        "detection_count_delta": len(yolox) - len(nanodet),
        "shared_classes": sorted(intersection),
        "yolox_only_classes": sorted(left_classes - right_classes),
        "nanodet_only_classes": sorted(right_classes - left_classes),
        "class_jaccard": round(len(intersection) / len(union), 6) if union else 1.0,
        "matched_boxes": matches,
        "matched_box_count": len(matches),
        "unmatched_yolox_indexes": unmatched_left,
        "unmatched_nanodet_indexes": unmatched_right,
        "mean_matched_iou": round(mean_iou, 6),
        "median_matched_iou": round(median(matched_ious), 6) if matched_ious else 0.0,
        "disagreement_score": round(min(1.0, max(0.0, score)), 6),
        "disagreement_formula_version": 1,
        "yolox_sidecar": left.get("sidecar_file"),
        "nanodet_sidecar": right.get("sidecar_file"),
    }


def aggregate(comparisons: Sequence[dict[str, Any]], yolox_entries: Sequence[dict[str, Any]], nanodet_entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(str(item["state"]) for item in comparisons)
    yolox_classes: Counter[str] = Counter()
    nanodet_classes: Counter[str] = Counter()
    for entry in yolox_entries:
        yolox_classes.update({str(k): int(v) for k, v in dict(entry.get("class_counts") or {}).items()})
    for entry in nanodet_entries:
        nanodet_classes.update({str(k): int(v) for k, v in dict(entry.get("class_counts") or {}).items()})
    class_names = sorted(set(yolox_classes) | set(nanodet_classes))
    return {
        "images_compared": len(comparisons),
        "states": dict(sorted(states.items())),
        "yolox_total_detections": sum(item["yolox_detection_count"] for item in comparisons),
        "nanodet_total_detections": sum(item["nanodet_detection_count"] for item in comparisons),
        "matched_boxes": sum(item["matched_box_count"] for item in comparisons),
        "mean_disagreement_score": (
            sum(float(item["disagreement_score"]) for item in comparisons) / len(comparisons)
            if comparisons else 0.0
        ),
        "class_counts": [
            {
                "class_name": name,
                "yolox": yolox_classes[name],
                "nanodet": nanodet_classes[name],
                "delta": yolox_classes[name] - nanodet_classes[name],
            }
            for name in class_names
        ],
        "top_disagreements": [item["image_sha256"] for item in sorted(comparisons, key=lambda row: (-float(row["disagreement_score"]), row["image_sha256"]))[:50]],
        "top_agreements": [item["image_sha256"] for item in sorted(comparisons, key=lambda row: (float(row["disagreement_score"]), row["image_sha256"]))[:50]],
    }


def find_original(root: Path, digest: str) -> Path:
    matches = sorted((root / "package-root" / "corpus" / "originals").glob(f"{digest}.*"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one original for {digest}, found {len(matches)}")
    return matches[0]


def panel_image(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (10, 18, 30))
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def render_tripanel(
    original: Path,
    yolox: Path,
    nanodet: Path,
    comparison: dict[str, Any],
    destination: Path,
) -> None:
    cell = (480, 480)
    header, footer = 46, 92
    canvas = Image.new("RGB", (cell[0] * 3, cell[1] + header + footer), (7, 14, 25))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (title, path) in enumerate(
        (("Original", original), ("YOLOX-Tiny", yolox), ("NanoDet-Plus", nanodet))
    ):
        x = index * cell[0]
        canvas.paste(panel_image(path, cell), (x, header))
        draw.text((x + 12, 16), title, fill=(235, 244, 255), font=font)
    shared = ", ".join(comparison["shared_classes"]) or "none"
    exclusive = (
        f"YOLOX-only: {', '.join(comparison['yolox_only_classes']) or 'none'} | "
        f"NanoDet-only: {', '.join(comparison['nanodet_only_classes']) or 'none'}"
    )
    lines = [
        f"{comparison['prompt_id']} · {comparison['category']} · {comparison['image_sha256'][:12]}",
        f"counts {comparison['yolox_detection_count']} / {comparison['nanodet_detection_count']} · shared: {shared}",
        f"agreement {1-float(comparison['disagreement_score']):.3f} · {exclusive}",
    ]
    y = cell[1] + header + 10
    for line in lines:
        draw.text((12, y), line[:220], fill=(220, 231, 244), font=font)
        y += 24
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, "JPEG", quality=88, optimize=True, progressive=True)


def choose_previews(comparisons: Sequence[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    strongest_by_category: dict[str, dict[str, Any]] = {}
    for row in sorted(comparisons, key=lambda item: (-float(item["disagreement_score"]), item["image_sha256"])):
        strongest_by_category.setdefault(str(row["category"]), row)
    for row in strongest_by_category.values():
        if len(selected) >= limit:
            break
        selected.append(row); used.add(row["image_sha256"])
    buckets = [
        [row for row in comparisons if "only-nonempty" in str(row["state"])],
        sorted(comparisons, key=lambda row: (-(row["yolox_detection_count"] + row["nanodet_detection_count"]), row["image_sha256"])),
        sorted(comparisons, key=lambda row: (float(row["disagreement_score"]), row["image_sha256"])),
        sorted(comparisons, key=lambda row: (-float(row["disagreement_score"]), row["image_sha256"])),
    ]
    for bucket in buckets:
        for row in bucket:
            if len(selected) >= limit:
                return selected
            if row["image_sha256"] in used:
                continue
            selected.append(row); used.add(row["image_sha256"])
    return selected


def build_gallery(root: Path, comparisons: Sequence[dict[str, Any]], preview_map: dict[str, str]) -> Path:
    gallery = root / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    write_json(gallery / "data.json", list(comparisons))
    cards = []
    for row in comparisons:
        preview = preview_map.get(row["image_sha256"], "")
        search = " ".join(
            [row["prompt_id"], row["category"], row["image_sha256"], row["state"], *row["shared_classes"], *row["yolox_only_classes"], *row["nanodet_only_classes"]]
        ).lower()
        image = f"<img loading='lazy' src='{html.escape(preview)}' alt='comparison'>" if preview else ""
        cards.append(
            f"<article data-search='{html.escape(search)}' data-state='{row['state']}' data-score='{row['disagreement_score']}'>{image}"
            f"<h2>{html.escape(row['prompt_id'])}</h2><p>{row['state']} · disagreement {row['disagreement_score']:.3f}</p></article>"
        )
    (gallery / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>YOLOX versus NanoDet comparison</title><style>body{font-family:system-ui;background:#07101d;color:#eef6ff;margin:0;padding:1rem}"
        "header,.grid{max-width:96rem;margin:auto}.controls{display:flex;gap:.7rem;flex-wrap:wrap}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem;margin-top:1rem}"
        "article{background:#101c2d;border:1px solid #28425e;border-radius:1rem;overflow:hidden;padding-bottom:1rem}img{width:100%;display:block}h2,p{margin:.7rem 1rem}input,select{padding:.7rem}</style></head><body>"
        f"<header><h1>YOLOX-Tiny versus NanoDet-Plus</h1><p>{html.escape(DISCLAIMER)}</p><div class='controls'>"
        "<input id='q' placeholder='prompt, category, SHA or class'><select id='state'><option value=''>all states</option>"
        "<option>both-empty</option><option>yolox-only-nonempty</option><option>nanodet-only-nonempty</option><option>both-nonempty</option></select>"
        "<select id='sort'><option value='desc'>highest disagreement</option><option value='asc'>strongest agreement</option></select></div></header>"
        "<main id='grid' class='grid'>" + "".join(cards) + "</main><script>"
        "const cards=[...document.querySelectorAll('article')];function render(){let query=q.value.toLowerCase(),s=state.value;"
        "cards.forEach(x=>x.hidden=!(x.dataset.search.includes(query)&&(!s||x.dataset.state===s)));"
        "cards.sort((a,b)=>(+a.dataset.score-+b.dataset.score)*(sort.value==='asc'?1:-1)).forEach(x=>grid.append(x))}"
        "q.oninput=state.onchange=sort.onchange=render;render()</script></body></html>",
        encoding="utf-8",
    )
    return gallery


def choose_tag(repo: str, latest_date: str) -> tuple[str, bool]:
    rows = json.loads(
        command(["gh", "release", "list", "--repo", repo, "--limit", "1000", "--json", "tagName,isDraft"]).stdout or "[]"
    )
    matching = []
    for row in rows:
        match = TAG_RE.fullmatch(str(row.get("tagName") or ""))
        if match and match.group(1) == latest_date:
            matching.append((int(match.group(2)), str(row["tagName"]), bool(row.get("isDraft"))))
    drafts = [row for row in matching if row[2]]
    if drafts:
        return max(drafts)[1], True
    return f"media-detection-all-{latest_date}-v{max((row[0] for row in matching), default=0)+1}", False


def release_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def asset_url(repo: str, tag: str, name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{quote(tag, safe='')}/{quote(name, safe='')}"


def notes(repo: str, tag: str, report: dict[str, Any], assets: Sequence[dict[str, Any]], previews: Sequence[dict[str, Any]], preview_prefix: str) -> str:
    summary = report["summary"]
    lines = [
        "# Multi-detector COCO observations — YOLOX-Tiny + NanoDet-Plus",
        "",
        DISCLAIMER,
        "",
        f"- Analysis batch: `{report['analysis_batch_id']}`",
        f"- Source range: **{report['date_from']} → {report['date_to']}**",
        f"- Source Releases: **{len(report['source_release_tags'])}**",
        f"- Canonical images compared: **{summary['images_compared']:,}**",
        f"- YOLOX detections: **{summary['yolox_total_detections']:,}**",
        f"- NanoDet detections: **{summary['nanodet_total_detections']:,}**",
        f"- Matched same-class boxes at IoU ≥ 0.50: **{summary['matched_boxes']:,}**",
        f"- Mean disagreement score: **{summary['mean_disagreement_score']:.3f}**",
        f"- Corpus fingerprint: `{report['corpus_fingerprint']}`",
        f"- YOLOX model SHA-256: `{report['detectors']['yolox-tiny']['model_sha256']}`",
        f"- NanoDet model SHA-256: `{report['detectors']['nanodet-plus-m-320']['model_sha256']}`",
        "",
        "## Agreement states",
        "",
    ]
    lines.extend(f"- **{name}**: {count:,}" for name, count in summary["states"].items())
    if previews:
        lines.extend(["", "## Representative Original / YOLOX / NanoDet panels", ""])
        for row in previews:
            raw = f"https://raw.githubusercontent.com/{repo}/main/{preview_prefix}/{row['image_sha256']}.jpg"
            lines.extend(
                [
                    f"### {row['prompt_id']} · {row['state']} · disagreement {row['disagreement_score']:.3f}",
                    "",
                    f"[![{row['image_sha256'][:12]} detector comparison]({raw})]({raw})",
                    "",
                ]
            )
    lines.extend(["## ZIP assets", ""])
    for item in assets:
        lines.append(
            f"- [{item['name']}]({asset_url(repo, tag, item['name'])}) — "
            f"{item['size_bytes']/1024**2:.1f} MiB · SHA-256 `{item['sha256']}`"
        )
    lines.extend(["", "## Interpretation limits", "", DISCLAIMER, ""])
    return "\n".join(lines)


def rebuild_history(repo: str, destination: Path) -> list[dict[str, Any]]:
    rows = json.loads(
        command(["gh", "release", "list", "--repo", repo, "--limit", "1000", "--json", "tagName,publishedAt,isDraft"]).stdout or "[]"
    )
    history = []
    for row in rows:
        tag = str(row.get("tagName") or "")
        if not TAG_RE.fullmatch(tag) or row.get("isDraft"):
            continue
        history.append(
            {
                "tag": tag,
                "published_at": row.get("publishedAt"),
                "release_url": release_url(repo, tag),
            }
        )
    history.sort(key=lambda row: (str(row["published_at"]), row["tag"]), reverse=True)
    write_json(destination, {"schema_version": 1, "releases": history})
    return history


def run(args: argparse.Namespace) -> dict[str, Any]:
    yolox_root, nanodet_root = args.yolox_root.resolve(), args.nanodet_root.resolve()
    yolox_manifest, yolox_entries = validate_artifact(yolox_root, "yolox-tiny")
    nanodet_manifest, nanodet_entries = validate_artifact(nanodet_root, "nanodet-plus-m-320")
    require_pair(yolox_manifest, nanodet_manifest)
    left = {entry["image_sha256"]: entry for entry in yolox_entries}
    right = {entry["image_sha256"]: entry for entry in nanodet_entries}
    comparisons = [compare_entry(left[digest], right[digest]) for digest in yolox_manifest["canonical_image_sha256"]]
    summary = aggregate(comparisons, yolox_entries, nanodet_entries)
    output = args.output_dir.resolve()
    if output.exists():
        shutil.rmtree(output)
    comparison_root = output / "comparison"
    preview_rows = choose_previews(comparisons, limit=args.preview_limit)
    preview_map: dict[str, str] = {}
    for row in preview_rows:
        digest = row["image_sha256"]
        original = find_original(yolox_root, digest)
        yolox_image = yolox_root / "package-root" / str(left[digest]["annotated_file"])
        nanodet_image = nanodet_root / "package-root" / str(right[digest]["annotated_file"])
        destination = comparison_root / "previews" / f"{digest}.jpg"
        render_tripanel(original, yolox_image, nanodet_image, row, destination)
        preview_map[digest] = f"../previews/{digest}.jpg"
    write_json(comparison_root / "entries.json", comparisons)
    report = {
        "schema_version": 1,
        "status": "published" if args.publish else "built",
        "generated_at_utc": utc_now(),
        "analysis_batch_id": yolox_manifest["analysis_batch_id"],
        "corpus_fingerprint": yolox_manifest["corpus_fingerprint"],
        "quarantine_policy_digest": yolox_manifest["quarantine_policy_digest"],
        "source_release_tags": yolox_manifest["source_release_tags"],
        "date_from": yolox_manifest["date_from"],
        "date_to": yolox_manifest["date_to"],
        "latest_date": yolox_manifest["latest_date"],
        "thresholds": yolox_manifest["thresholds"],
        "detectors": {
            "yolox-tiny": {
                "workflow_run_id": yolox_manifest["workflow_run_id"],
                "model_sha256": yolox_manifest["model_sha256"],
                "successful_images": yolox_manifest["successful_image_count"],
            },
            "nanodet-plus-m-320": {
                "workflow_run_id": nanodet_manifest["workflow_run_id"],
                "model_sha256": nanodet_manifest["model_sha256"],
                "successful_images": nanodet_manifest["successful_image_count"],
            },
        },
        "summary": summary,
        "disagreement_formula": "0.35*class + 0.25*count + 0.25*unmatched + 0.15*(1-mean_iou)",
        "interpretation": DISCLAIMER,
    }
    write_json(comparison_root / "comparison-report.json", report)
    gallery = build_gallery(comparison_root, comparisons, preview_map)
    release_assets = output / "release-assets"
    release_assets.mkdir(parents=True)
    asset_manifest: list[dict[str, Any]] = []
    for source_root in (yolox_root, nanodet_root):
        for source in sorted((source_root / "release-assets").glob("*.zip")):
            destination = release_assets / source.name
            shutil.copy2(source, destination)
            asset_manifest.append(
                {"name": destination.name, "size_bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
            )
    metadata_paths = [comparison_root / "comparison-report.json", comparison_root / "entries.json"]
    deterministic_zip(release_assets / "detector-comparison-metadata.zip", output, metadata_paths)
    gallery_paths = [path for path in comparison_root.rglob("*") if path.is_file() and ("/gallery/" in path.as_posix() or "/previews/" in path.as_posix())]
    deterministic_zip(release_assets / "detector-comparison-gallery.zip", comparison_root, gallery_paths)
    complete_paths = [path for path in comparison_root.rglob("*") if path.is_file()]
    for number, part in enumerate(split_paths(complete_paths, int(1.75 * 1024**3)), 1):
        deterministic_zip(release_assets / f"detector-comparison-complete-part{number:03d}.zip", comparison_root, part)
    existing_names = {item["name"] for item in asset_manifest}
    for path in sorted(release_assets.glob("detector-comparison-*.zip")):
        if path.name in existing_names:
            continue
        asset_manifest.append(
            {"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    write_json(output / "package-manifest.json", {"schema_version": 1, "assets": asset_manifest})

    tag, resumed = choose_tag(args.repo, str(report["latest_date"]))
    release_page = release_url(args.repo, tag)
    preview_prefix = f"{args.preview_repo_root.rstrip('/')}/{tag}"
    notes_text = notes(args.repo, tag, report, asset_manifest, preview_rows, preview_prefix)
    (output / "release-notes.md").write_text(notes_text, encoding="utf-8")
    if args.publish:
        preliminary = output / "preliminary.md"
        preliminary.write_text("# Multi-detector analysis\n\nVerified assets are being uploaded.\n", encoding="utf-8")
        if not resumed:
            command([
                "gh", "release", "create", tag, "--repo", args.repo,
                "--title", f"YOLOX + NanoDet comparison (through {report['latest_date']})",
                "--notes-file", str(preliminary), "--draft", "--latest=false",
            ])
        command(["gh", "release", "upload", tag, "--repo", args.repo, *map(str, sorted(release_assets.glob("*.zip"))), "--clobber"])
        command([
            "gh", "release", "edit", tag, "--repo", args.repo,
            "--title", f"YOLOX + NanoDet comparison (through {report['latest_date']})",
            "--notes-file", str(output / "release-notes.md"), "--draft=false", "--latest=false",
        ])
        published = json.loads(command(["gh", "api", f"repos/{args.repo}/releases/tags/{tag}"]).stdout)
        actual = {item["name"]: int(item["size"]) for item in published.get("assets", [])}
        expected = {item["name"]: int(item["size_bytes"]) for item in asset_manifest}
        if actual != expected:
            raise RuntimeError(f"Published detector asset mismatch: expected={expected}, actual={actual}")
        release_page = str(published.get("html_url") or release_page)

    preview_root = args.preview_root / tag
    preview_root.mkdir(parents=True, exist_ok=True)
    for row in preview_rows:
        shutil.copy2(comparison_root / "previews" / f"{row['image_sha256']}.jpg", preview_root / f"{row['image_sha256']}.jpg")
        row["preview_url"] = f"https://raw.githubusercontent.com/{args.repo}/main/{preview_prefix}/{row['image_sha256']}.jpg"
    latest = {
        "schema_version": 1,
        "status": "published" if args.publish else "built",
        "generated_at_utc": utc_now(),
        "release_tag": tag,
        "release_url": release_page,
        "analysis_batch_id": report["analysis_batch_id"],
        "date_from": report["date_from"],
        "date_to": report["date_to"],
        "corpus_fingerprint": report["corpus_fingerprint"],
        "detectors": report["detectors"],
        "thresholds": report["thresholds"],
        "summary": summary,
        "previews": preview_rows,
        "interpretation": DISCLAIMER,
    }
    write_json(args.index, latest)
    write_json(args.web_index, latest)
    if args.publish:
        rebuild_history(args.repo, args.history)
    return {"tag": tag, "release_url": release_page, "latest": latest, "report": report}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo", required=True)
    value.add_argument("--yolox-root", type=Path, required=True)
    value.add_argument("--nanodet-root", type=Path, required=True)
    value.add_argument("--output-dir", type=Path, default=Path("object-detection/comparison-output"))
    value.add_argument("--index", type=Path, default=Path("data/detection/latest.json"))
    value.add_argument("--history", type=Path, default=Path("data/detection/history.json"))
    value.add_argument("--web-index", type=Path, default=Path("web/public/data/detection/latest.json"))
    value.add_argument("--preview-root", type=Path, default=Path("web/public/data/detection/previews"))
    value.add_argument("--preview-repo-root", default="web/public/data/detection/previews")
    value.add_argument("--preview-limit", type=int, default=20)
    value.add_argument("--publish", action="store_true")
    return value


if __name__ == "__main__":
    args = parser().parse_args()
    result = run(args)
    print(json.dumps({"release_tag": result["tag"], "release_url": result["release_url"]}, indent=2))
