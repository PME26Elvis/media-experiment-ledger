"""Deterministic packaging, summaries, and preview selection for YOLO results."""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if pretty
        else canonical_json(value)
    )
    path.write_text(text, encoding="utf-8")


def deterministic_zip(destination: Path, root: Path, paths: Sequence[Path]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            )
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise IOError(f"ZIP verification failed for {destination}: {bad}")


def split_paths(paths: Sequence[Path], max_bytes: int) -> list[list[Path]]:
    groups: list[list[Path]] = []
    current: list[Path] = []
    size = 0
    for path in sorted(paths, key=lambda item: item.as_posix()):
        item_size = path.stat().st_size
        if item_size > max_bytes:
            raise ValueError(f"Single output exceeds package limit: {path}")
        if current and size + item_size > max_bytes:
            groups.append(current)
            current = []
            size = 0
        current.append(path)
        size += item_size
    if current:
        groups.append(current)
    return groups


def summarize(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    successful = [entry for entry in entries if entry.get("status") == "success"]
    failures = [entry for entry in entries if entry.get("status") != "success"]
    with_detections = [entry for entry in successful if int(entry.get("detection_count") or 0) > 0]
    class_counts: Counter[str] = Counter()
    prompt_counts: Counter[str] = Counter()
    release_counts: Counter[str] = Counter()
    total_detections = 0
    confidences: list[float] = []
    for entry in successful:
        total_detections += int(entry.get("detection_count") or 0)
        for name, count in dict(entry.get("class_counts") or {}).items():
            class_counts[str(name)] += int(count)
        for source in entry.get("sources", []):
            if not isinstance(source, dict):
                continue
            if source.get("prompt_id"):
                prompt_counts[str(source["prompt_id"])] += 1
            if source.get("release_tag"):
                release_counts[str(source["release_tag"])] += 1
        for detection in entry.get("detections", []):
            if isinstance(detection, dict) and detection.get("confidence") is not None:
                confidences.append(float(detection["confidence"]))
    return {
        "expected_images": len(entries),
        "successful_images": len(successful),
        "failed_images": len(failures),
        "images_with_detections": len(with_detections),
        "empty_detection_images": len(successful) - len(with_detections),
        "total_detections": total_detections,
        "mean_detections_per_successful_image": (
            total_detections / len(successful) if successful else 0.0
        ),
        "mean_detection_confidence": (
            sum(confidences) / len(confidences) if confidences else 0.0
        ),
        "top_classes": [
            {"class_name": name, "count": count}
            for name, count in class_counts.most_common()
        ],
        "images_by_prompt": dict(sorted(prompt_counts.items())),
        "images_by_release": dict(sorted(release_counts.items())),
        "failure_classes": dict(
            sorted(
                Counter(
                    str(entry.get("error_class") or "unknown") for entry in failures
                ).items()
            )
        ),
    }


def choose_previews(entries: Sequence[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    candidates = [
        entry
        for entry in entries
        if entry.get("status") == "success" and entry.get("annotated_file")
    ]
    ranked = sorted(
        candidates,
        key=lambda entry: (
            -int(entry.get("detection_count") or 0),
            -float(entry.get("max_confidence") or 0.0),
            str(entry.get("image_sha256") or ""),
        ),
    )
    selected: list[dict[str, Any]] = []
    covered_classes: set[str] = set()
    prompt_uses: Counter[str] = Counter()

    def prompt(entry: dict[str, Any]) -> str:
        sources = entry.get("sources") or []
        return str(sources[0].get("prompt_id") or "unknown") if sources else "unknown"

    for entry in ranked:
        if len(selected) >= limit:
            break
        top = [str(item) for item in entry.get("top_classes", [])]
        key = prompt(entry)
        if prompt_uses[key] >= 2:
            continue
        if top and top[0] not in covered_classes:
            selected.append(entry)
            covered_classes.add(top[0])
            prompt_uses[key] += 1
    empties = [entry for entry in ranked if int(entry.get("detection_count") or 0) == 0]
    for entry in [*ranked, *empties[:2]]:
        if len(selected) >= limit:
            break
        if entry in selected:
            continue
        key = prompt(entry)
        if prompt_uses[key] >= 2:
            continue
        selected.append(entry)
        prompt_uses[key] += 1
    return selected


def build_offline_gallery(root: Path, entries: Sequence[dict[str, Any]]) -> Path:
    gallery_root = root / "offline-gallery"
    if gallery_root.exists():
        shutil.rmtree(gallery_root)
    gallery_root.mkdir(parents=True, exist_ok=True)
    write_json(gallery_root / "data.json", list(entries))
    cards = []
    for entry in entries:
        if entry.get("status") != "success":
            continue
        annotated = entry.get("annotated_file")
        image = (
            f'<img loading="lazy" src="../{html.escape(str(annotated))}" alt="annotated">'
            if annotated
            else ""
        )
        classes = ", ".join(
            html.escape(str(item)) for item in entry.get("top_classes", [])
        ) or "none"
        cards.append(
            f'<article data-classes="{classes.lower()}">{image}'
            f'<h2>{html.escape(str(entry.get("image_sha256", ""))[:12])}</h2>'
            f'<p>{int(entry.get("detection_count") or 0)} detections · {classes}</p></article>'
        )
    (gallery_root / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>YOLOX-Tiny COCO detection gallery</title><style>body{font-family:system-ui;background:#07101d;color:#eef6ff;margin:0;padding:1rem}"
        "header{max-width:80rem;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem;max-width:90rem;margin:auto}"
        "article{background:#101c2d;border:1px solid #28425e;border-radius:1rem;overflow:hidden;padding-bottom:1rem}img{width:100%;display:block}"
        "h2,p{margin:.7rem 1rem}input{padding:.7rem;width:min(30rem,90%)}</style></head><body>"
        "<header><h1>YOLOX-Tiny / COCO full-corpus gallery</h1><p>Detector observations are not ground truth. COCO covers only 80 classes.</p>"
        "<input id='q' placeholder='Filter classes'></header><main class='grid'>"
        + "".join(cards)
        + "</main><script>q.oninput=()=>document.querySelectorAll('article').forEach(x=>x.hidden=!x.dataset.classes.includes(q.value.toLowerCase()))</script>"
        "</body></html>",
        encoding="utf-8",
    )
    return gallery_root


def package_analysis(
    output_root: Path,
    analysis_root: Path,
    entries: Sequence[dict[str, Any]],
    *,
    max_part_bytes: int = int(1.75 * 1024**3),
) -> list[dict[str, Any]]:
    release_root = output_root / "release-assets"
    release_root.mkdir(parents=True, exist_ok=True)
    gallery_root = build_offline_gallery(analysis_root, entries)
    all_files = [path for path in analysis_root.rglob("*") if path.is_file()]
    detection_files = [
        path
        for path in all_files
        if "/detections/" in path.as_posix() or "/failures/" in path.as_posix()
    ]
    annotated_files = [path for path in all_files if "/annotated/" in path.as_posix()]
    gallery_files = [path for path in gallery_root.rglob("*") if path.is_file()]
    metadata_files = [
        path
        for path in all_files
        if path not in detection_files
        and path not in annotated_files
        and path not in gallery_files
    ]

    plans: list[tuple[str, list[Path]]] = [("yolo-coco-metadata.zip", metadata_files)]
    for prefix, paths in (
        ("yolo-coco-detections", detection_files),
        ("yolo-coco-annotated", annotated_files),
        ("yolo-coco-complete", all_files),
    ):
        for index, part in enumerate(split_paths(paths, max_part_bytes), 1):
            plans.append((f"{prefix}-part{index:03d}.zip", part))
    plans.append(("yolo-coco-offline-gallery.zip", gallery_files))

    manifests: list[dict[str, Any]] = []
    for name, paths in plans:
        destination = release_root / name
        deterministic_zip(destination, analysis_root, paths)
        manifests.append(
            {
                "name": name,
                "size_bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "file_count": len(paths),
            }
        )
    write_json(
        output_root / "package-manifest.json",
        {"schema_version": 1, "assets": manifests},
    )
    return manifests
