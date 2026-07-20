"""Independent media-yolo-* Release publication and history rendering."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

try:
    from yolo_packages import choose_previews, write_json
except ImportError:
    from tools.yolo_packages import choose_previews, write_json

YOLO_TAG_RE = re.compile(r"^media-yolo-all-(\d{4}-\d{2}-\d{2})-v(\d+)$")


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result


def release_asset_url(repo: str, tag: str, name: str) -> str:
    return (
        f"https://github.com/{repo}/releases/download/"
        f"{quote(tag, safe='')}/{quote(name, safe='')}"
    )


def release_page_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def list_releases(repo: str) -> list[dict[str, Any]]:
    result = command(
        [
            "gh",
            "release",
            "list",
            "--repo",
            repo,
            "--limit",
            "1000",
            "--json",
            "tagName,isDraft,publishedAt,name",
        ]
    )
    return json.loads(result.stdout or "[]")


def choose_tag(latest_date: str, releases: Sequence[dict[str, Any]]) -> tuple[str, bool]:
    matching: list[tuple[int, str, bool]] = []
    for row in releases:
        tag = str(row.get("tagName") or "")
        match = YOLO_TAG_RE.fullmatch(tag)
        if not match or match.group(1) != latest_date:
            continue
        matching.append((int(match.group(2)), tag, bool(row.get("isDraft"))))
    drafts = [item for item in matching if item[2]]
    if drafts:
        _, tag, _ = max(drafts)
        return tag, True
    version = max((item[0] for item in matching), default=0) + 1
    return f"media-yolo-all-{latest_date}-v{version}", False


def copy_web_previews(
    entries: Sequence[dict[str, Any]],
    analysis_root: Path,
    preview_root: Path,
    run_id: str,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    selected = choose_previews(entries, limit=limit)
    target_root = preview_root / run_id
    target_root.mkdir(parents=True, exist_ok=True)
    output: list[dict[str, Any]] = []
    for entry in selected:
        annotated = analysis_root / str(entry["annotated_file"])
        target = target_root / f"{entry['image_sha256']}.jpg"
        shutil.copy2(annotated, target)
        output.append({**entry, "preview_relative_path": target.as_posix()})
    return output


def _notes(
    repo: str,
    tag: str,
    report: dict[str, Any],
    package_manifest: Sequence[dict[str, Any]],
    previews: Sequence[dict[str, Any]],
    *,
    preview_repo_prefix: str,
) -> str:
    summary = report["summary"]
    assets = {
        item["name"]: release_asset_url(repo, tag, item["name"])
        for item in package_manifest
    }
    lines = [
        "# YOLO Object Detection — YOLOX-Tiny / COCO",
        "",
        "Independent full-corpus object-detection analysis. This Release does not modify or gate the Prompt Repeatability Atlas.",
        "",
        f"- Source experiment range: **{report.get('date_from') or '—'} → {report.get('date_to') or '—'}**",
        f"- Source Releases: **{report.get('release_count', 0)}**",
        f"- Canonical unique images: **{summary.get('expected_images', 0):,}**",
        f"- Successfully inferred: **{summary.get('successful_images', 0):,}**",
        f"- Explicit failures: **{summary.get('failed_images', 0):,}**",
        f"- Images with detections: **{summary.get('images_with_detections', 0):,}**",
        f"- Empty detections: **{summary.get('empty_detection_images', 0):,}**",
        f"- Total detections: **{summary.get('total_detections', 0):,}**",
        f"- Model SHA-256: `{report.get('model_sha256', '')}`",
        f"- Corpus fingerprint: `{report.get('corpus_fingerprint', '')}`",
        f"- Confidence / NMS IoU: **{report['thresholds']['confidence']} / {report['thresholds']['nms_iou']}**",
        f"- Total workflow analysis time: **{report.get('timing', {}).get('total_seconds', 0):.2f}s**",
        "",
        "## ZIP assets",
        "",
    ]
    for item in package_manifest:
        lines.append(
            f"- [{item['name']}]({assets[item['name']]}) — "
            f"{item['file_count']:,} files, {item['size_bytes'] / 1024**2:.1f} MiB"
        )
    top = summary.get("top_classes", [])[:15]
    lines.extend(["", "## Top COCO detections", ""])
    lines.extend(f"- **{item['class_name']}**: {item['count']:,}" for item in top)
    if previews:
        annotated_bundle = next(
            (
                url
                for name, url in assets.items()
                if name.startswith("yolo-coco-annotated-part")
            ),
            release_page_url(repo, tag),
        )
        lines.extend(["", "## Representative annotated previews", ""])
        for entry in previews:
            source = (entry.get("sources") or [{}])[0]
            prompt_id = source.get("prompt_id") or "unknown prompt"
            classes = ", ".join(entry.get("top_classes", [])) or "no COCO detections"
            raw_url = (
                f"https://raw.githubusercontent.com/{repo}/main/"
                f"{preview_repo_prefix}/{entry['image_sha256']}.jpg"
            )
            lines.extend(
                [
                    f"### {prompt_id} · {entry.get('detection_count', 0)} detections · {classes}",
                    "",
                    f"[![{entry['image_sha256'][:12]} YOLOX-Tiny detection preview]({raw_url})]({raw_url})",
                    "",
                    f"[Download the containing annotated ZIP]({annotated_bundle})",
                    "",
                ]
            )
    lines.extend(
        [
            "## Interpretation limits",
            "",
            "This is a frozen COCO-pretrained detector. COCO covers 80 classes; a missing detection does not mean the image contains no object, and confidence is not a real-world probability or generation-quality score.",
        ]
    )
    return "\n".join(lines) + "\n"


def publish_release(
    repo: str,
    output_root: Path,
    report: dict[str, Any],
    entries: Sequence[dict[str, Any]],
    analysis_root: Path,
    preview_root: Path,
    *,
    preview_repo_root: str,
    publish: bool,
) -> dict[str, Any]:
    package_manifest = json.loads(
        (output_root / "package-manifest.json").read_text(encoding="utf-8")
    )["assets"]
    releases = list_releases(repo)
    tag, resumed = choose_tag(str(report["latest_date"]), releases)
    run_id = str(report["analysis_run_id"])
    selected = copy_web_previews(entries, analysis_root, preview_root, run_id, limit=20)
    relative_prefix = f"{preview_repo_root.rstrip('/')}/{run_id}"
    notes = _notes(
        repo,
        tag,
        report,
        package_manifest,
        selected,
        preview_repo_prefix=relative_prefix,
    )
    notes_path = output_root / "release-notes.md"
    notes_path.write_text(notes, encoding="utf-8")
    title = (
        f"YOLO Object Detection — YOLOX-Tiny / COCO "
        f"(through {report['latest_date']})"
    )
    release_url = release_page_url(repo, tag)
    if publish:
        preliminary = output_root / "release-notes-preliminary.md"
        preliminary.write_text(
            "# YOLO Object Detection\n\nAnalysis completed; verified ZIP assets are being uploaded.\n",
            encoding="utf-8",
        )
        if not resumed:
            command(
                [
                    "gh",
                    "release",
                    "create",
                    tag,
                    "--repo",
                    repo,
                    "--title",
                    title,
                    "--notes-file",
                    str(preliminary),
                    "--draft",
                    "--latest=false",
                ]
            )
        assets = sorted((output_root / "release-assets").glob("*.zip"))
        if not assets or any(path.suffix.lower() != ".zip" for path in assets):
            raise RuntimeError("YOLO publication requires ZIP-only Release assets")
        command(
            [
                "gh",
                "release",
                "upload",
                tag,
                "--repo",
                repo,
                *map(str, assets),
                "--clobber",
            ]
        )
        command(
            [
                "gh",
                "release",
                "edit",
                tag,
                "--repo",
                repo,
                "--title",
                title,
                "--notes-file",
                str(notes_path),
                "--draft=false",
                "--latest=false",
            ]
        )
        release = json.loads(
            command(["gh", "api", f"repos/{repo}/releases/tags/{tag}"]).stdout
        )
        actual = {str(item["name"]) for item in release.get("assets", [])}
        expected = {str(item["name"]) for item in package_manifest}
        if expected != actual:
            raise RuntimeError(
                f"Published YOLO asset mismatch: expected={sorted(expected)}, "
                f"actual={sorted(actual)}"
            )
        if any(not name.endswith(".zip") for name in actual):
            raise RuntimeError("Published YOLO Release contains non-ZIP assets")
        release_url = str(release.get("html_url") or release_url)
    for entry in entries:
        entry["release_tag"] = tag
        entry["release_url"] = release_url
        entry["bundle_url"] = next(
            (
                release_asset_url(repo, tag, item["name"])
                for item in package_manifest
                if item["name"].startswith("yolo-coco-annotated-part")
            ),
            release_url,
        )
    preview_ids = {entry["image_sha256"] for entry in selected}
    for entry in entries:
        if entry["image_sha256"] in preview_ids:
            entry["annotated_preview_url"] = (
                f"https://raw.githubusercontent.com/{repo}/main/"
                f"{relative_prefix}/{entry['image_sha256']}.jpg"
            )
    return {
        "tag": tag,
        "release_url": release_url,
        "resumed_draft": resumed,
        "published": publish,
        "preview_count": len(selected),
        "package_manifest": package_manifest,
    }


def rebuild_history(repo: str, destination: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for release in list_releases(repo):
        tag = str(release.get("tagName") or "")
        if not YOLO_TAG_RE.fullmatch(tag) or release.get("isDraft"):
            continue
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = command(
                [
                    "gh",
                    "release",
                    "download",
                    tag,
                    "--repo",
                    repo,
                    "--pattern",
                    "yolo-coco-metadata.zip",
                    "--dir",
                    str(root),
                ],
                check=False,
            )
            archive_path = root / "yolo-coco-metadata.zip"
            if result.returncode or not archive_path.exists():
                continue
            with zipfile.ZipFile(archive_path) as archive:
                candidates = [
                    name
                    for name in archive.namelist()
                    if name.endswith("analysis-report.json")
                ]
                if not candidates:
                    continue
                report = json.loads(archive.read(candidates[0]))
        summary = report.get("summary") or {}
        rows.append(
            {
                "tag": tag,
                "published_at": str(release.get("publishedAt") or ""),
                "release_url": release_page_url(repo, tag),
                "date_from": report.get("date_from"),
                "date_to": report.get("date_to"),
                "images": summary.get("expected_images", 0),
                "images_with_detections": summary.get(
                    "images_with_detections", 0
                ),
                "total_detections": summary.get("total_detections", 0),
                "model": report.get("model_family", "YOLOX-Tiny"),
            }
        )
    rows.sort(key=lambda item: (item["published_at"], item["tag"]), reverse=True)
    write_json(destination, {"schema_version": 1, "releases": rows})
    return rows


def update_readme_history(
    path: Path, rows: Sequence[dict[str, Any]], *, english: bool
) -> None:
    text = path.read_text(encoding="utf-8")
    start = (
        "<!-- AUTO:YOLO_HISTORY_EN:START -->"
        if english
        else "<!-- AUTO:YOLO_HISTORY:START -->"
    )
    end = (
        "<!-- AUTO:YOLO_HISTORY_EN:END -->"
        if english
        else "<!-- AUTO:YOLO_HISTORY:END -->"
    )
    if start not in text or end not in text:
        heading = (
            "## YOLO object-detection history"
            if english
            else "## YOLO 物件偵測歷史"
        )
        text = text.rstrip() + f"\n\n{heading}\n\n{start}\n{end}\n"
    header = (
        "| Published | Source range | Images | With detections | Detections | Model | Release |\n|---|---|---:|---:|---:|---|---|"
        if english
        else "| 發布日期 | 資料範圍 | 圖片 | 有偵測 | 偵測框 | 模型 | Release |\n|---|---|---:|---:|---:|---|---|"
    )
    lines = [header]
    for row in rows:
        published = str(row.get("published_at") or "")[:10]
        date_range = f"{row.get('date_from') or '—'} → {row.get('date_to') or '—'}"
        lines.append(
            f"| {published} | {date_range} | {int(row.get('images') or 0):,} | "
            f"{int(row.get('images_with_detections') or 0):,} | "
            f"{int(row.get('total_detections') or 0):,} | "
            f"{row.get('model') or 'YOLOX-Tiny'} | "
            f"[`{row['tag']}`]({row['release_url']}) |"
        )
    block = start + "\n" + "\n".join(lines) + "\n" + end
    prefix, remainder = text.split(start, 1)
    _, suffix = remainder.split(end, 1)
    path.write_text(prefix + block + suffix, encoding="utf-8")
