"""ZIP packaging for the full-corpus Prompt Repeatability Atlas."""
from __future__ import annotations

import html
import json
import re
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _media_type(entry: Any) -> str:
    return str(getattr(entry, "media_type", "image") or "image")


def gallery_html(report: dict[str, Any]) -> str:
    cards = []
    for entry in report.get("entries", []):
        media_type = str(entry.get("media_type") or "image")
        prefix = "video/primary" if media_type == "video" else "primary"
        primary = html.escape(entry["primary_file"])
        cards.append(
            f'''<article><a href="{prefix}/{primary}"><img loading="lazy" src="{prefix}/{primary}" alt="{html.escape(entry['prompt_id'])} comparison"></a><div><strong>{html.escape(entry['prompt_id'])}</strong><span>{html.escape(media_type)} · {html.escape(entry['category'])} · {entry['sample_count']} samples</span><p>{html.escape(entry['prompt'])}</p><code>{html.escape(entry['cohort_id'])}</code></div></article>'''
        )
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prompt Repeatability Atlas</title><style>body{{margin:0;background:#07101d;color:#eef8ff;font:16px system-ui;padding:32px}}header{{max-width:1100px;margin:auto auto 28px}}main{{max-width:1400px;margin:auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}}article{{background:#0d1c2f;border:1px solid #315470;border-radius:16px;overflow:hidden}}img{{width:100%;display:block}}article div{{padding:16px}}strong,span{{display:block}}span,p{{color:#9cb5cc}}p{{font-size:14px;line-height:1.5}}code{{color:#52d3ff}}</style><header><h1>Prompt Repeatability Atlas</h1><p>All published image and video data · fingerprint {html.escape(report.get('dataset_fingerprint',''))}</p></header><main>{''.join(cards)}</main></html>'''


def write_zip(
    destination: Path,
    root: Path,
    files: Iterable[Path],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {"compression": compression, "allowZip64": True}
    if compression == zipfile.ZIP_DEFLATED:
        kwargs["compresslevel"] = 6
    with zipfile.ZipFile(destination, "w", **kwargs) as archive:
        for path in sorted(set(files), key=lambda item: item.as_posix()):
            if path.is_file() and path != destination:
                archive.write(path, path.relative_to(root).as_posix())
    with zipfile.ZipFile(destination) as archive:
        if bad := archive.testzip():
            raise IOError(f"Atlas ZIP verification failed for {destination}: {bad}")


def chunks(values: list[Any], size: int) -> Iterable[list[Any]]:
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    for start in range(0, len(values), size):
        yield values[start : start + size]


def partition_by_size(files: list[Path], max_bytes: int) -> list[list[Path]]:
    parts: list[list[Path]] = []
    current: list[Path] = []
    current_bytes = 0
    for path in sorted(files, key=lambda item: item.name):
        size = path.stat().st_size
        if size >= max_bytes:
            raise ValueError(
                "Single Atlas ZIP exceeds the configured Release asset limit: "
                f"{path.name} ({size} bytes)"
            )
        if current and current_bytes + size >= max_bytes:
            parts.append(current)
            current = []
            current_bytes = 0
        current.append(path)
        current_bytes += size
    if current:
        parts.append(current)
    return parts


def safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "prompt"


def prompt_bundle_name(
    index: int,
    prompt_ids: list[str],
    *,
    media_type: str = "image",
) -> str:
    if not prompt_ids:
        raise ValueError("Prompt bundle cannot be empty")
    first = safe_token(prompt_ids[0])
    last = safe_token(prompt_ids[-1])
    span = first if first == last else f"{first}-to-{last}"
    prefix = "video-atlas-bundle" if media_type == "video" else "prompt-atlas-bundle"
    return f"{prefix}-{index:03d}-{span}.zip"


def _bundle_entries(
    output: Path,
    entries: list[Any],
    prompts_per_bundle: int,
    *,
    media_type: str,
) -> list[Path]:
    selected = [entry for entry in entries if _media_type(entry) == media_type]
    by_prompt: dict[str, list[Any]] = {}
    for entry in selected:
        by_prompt.setdefault(entry.prompt_id, []).append(entry)
    prompt_ids = sorted(by_prompt)
    bundles: list[Path] = []
    for bundle_index, bundled_prompt_ids in enumerate(
        chunks(prompt_ids, max(1, int(prompts_per_bundle))),
        1,
    ):
        bundle_name = prompt_bundle_name(
            bundle_index,
            bundled_prompt_ids,
            media_type=media_type,
        )
        bundle_path = output / "release-assets" / bundle_name
        files: list[Path] = []
        bundled_entries: list[Any] = []
        for prompt_id in bundled_prompt_ids:
            for entry in sorted(
                by_prompt[prompt_id],
                key=lambda item: (item.model, item.cohort_id),
            ):
                if media_type == "video":
                    files.append(output / "video" / "primary" / entry.primary_file)
                    files.append(output / "video" / "sidecars" / entry.sidecar_file)
                    if entry.extended_file:
                        files.append(output / "video" / "extended" / entry.extended_file)
                    files.extend(
                        output / "video" / "keyframes" / name
                        for name in entry.full_files
                    )
                else:
                    files.append(output / "primary" / entry.primary_file)
                    files.append(output / "sidecars" / entry.sidecar_file)
                    if entry.extended_file:
                        files.append(output / "extended" / entry.extended_file)
                    files.extend(output / "full" / name for name in entry.full_files)
                entry.bundle_file = bundle_name
                bundled_entries.append(entry)
        manifest_dir = (
            "video-bundle-manifests"
            if media_type == "video"
            else "bundle-manifests"
        )
        manifest_name = (
            f"video-prompt-bundle-{bundle_index:03d}.json"
            if media_type == "video"
            else f"prompt-bundle-{bundle_index:03d}.json"
        )
        manifest_path = output / manifest_dir / manifest_name
        save_json(
            manifest_path,
            {
                "schema_version": 3,
                "media_type": media_type,
                "bundle_index": bundle_index,
                "prompt_count": len(bundled_prompt_ids),
                "prompt_ids": bundled_prompt_ids,
                "prompts_per_bundle_policy": int(prompts_per_bundle),
                "cohorts": [
                    {
                        "prompt_id": entry.prompt_id,
                        "cohort_id": entry.cohort_id,
                        "model": entry.model,
                        "sample_count": entry.sample_count,
                        "primary_file": entry.primary_file,
                        "extended_file": entry.extended_file,
                        "full_files": entry.full_files,
                        "sidecar_file": entry.sidecar_file,
                    }
                    for entry in bundled_entries
                ],
            },
        )
        files.append(manifest_path)
        write_zip(bundle_path, output, files)
        bundles.append(bundle_path)
    return bundles


def create_prompt_bundles(
    output: Path,
    entries: list[Any],
    prompts_per_bundle: int = 15,
) -> list[Path]:
    return _bundle_entries(
        output,
        entries,
        prompts_per_bundle,
        media_type="image",
    )


def create_video_bundles(
    output: Path,
    entries: list[Any],
    prompts_per_bundle: int = 15,
) -> list[Path]:
    return _bundle_entries(
        output,
        entries,
        prompts_per_bundle,
        media_type="video",
    )


def create_release_packages(
    output: Path,
    entries: list[Any],
    report: dict[str, Any],
    config: dict[str, Any],
) -> list[Path]:
    release_root = output / "release-assets"
    release_root.mkdir(parents=True, exist_ok=True)
    prompts_per_bundle = max(1, int(config.get("prompts_per_bundle", 15)))
    video_prompts_per_bundle = max(
        1,
        int(config.get("video_prompts_per_bundle", prompts_per_bundle)),
    )
    image_bundles = create_prompt_bundles(
        output,
        entries,
        prompts_per_bundle,
    )
    video_bundles = create_video_bundles(
        output,
        entries,
        video_prompts_per_bundle,
    )

    report["entries"] = [asdict(entry) for entry in entries]
    report["prompt_bundle_count"] = len(image_bundles)
    report["video_prompt_bundle_count"] = len(video_bundles)
    report["total_bundle_count"] = len(image_bundles) + len(video_bundles)
    report["prompts_per_bundle"] = prompts_per_bundle
    report["video_prompts_per_bundle"] = video_prompts_per_bundle
    report_path = output / "atlas-report.json"
    save_json(report_path, report)

    gallery_path = output / "index.html"
    gallery_path.write_text(gallery_html(report), encoding="utf-8")

    metadata_zip = release_root / "atlas-metadata.zip"
    metadata_files = [
        report_path,
        *sorted((output / "sidecars").glob("*.json")),
        *sorted((output / "video" / "sidecars").glob("*.json")),
        *sorted((output / "bundle-manifests").glob("*.json")),
        *sorted((output / "video-bundle-manifests").glob("*.json")),
    ]
    write_zip(metadata_zip, output, metadata_files)

    gallery_zip = release_root / "offline-gallery.zip"
    gallery_files = [
        gallery_path,
        *sorted((output / "primary").glob("*.jpg")),
        *sorted((output / "video" / "primary").glob("*.gif")),
    ]
    write_zip(gallery_zip, output, gallery_files)

    max_asset_bytes = int(
        float(config.get("max_release_asset_gib", 1.75)) * 1024**3
    )
    independent_assets = [
        *image_bundles,
        *video_bundles,
        metadata_zip,
        gallery_zip,
    ]
    for path in independent_assets:
        if path.stat().st_size >= max_asset_bytes:
            raise ValueError(
                f"Atlas Release asset is too large and must be split: {path.name}"
            )

    for index, part_files in enumerate(
        partition_by_size(independent_assets, max_asset_bytes),
        1,
    ):
        destination = (
            release_root
            / f"prompt-repeatability-atlas-complete-part{index:03d}.zip"
        )
        write_zip(
            destination,
            release_root,
            part_files,
            compression=zipfile.ZIP_STORED,
        )

    assets = sorted(release_root.glob("*"))
    if any(path.suffix.lower() != ".zip" for path in assets):
        raise RuntimeError("Every Atlas Release asset must be a ZIP file")
    return assets
