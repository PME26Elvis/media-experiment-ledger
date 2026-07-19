"""Full-corpus rendering and Pages-index assembly for Prompt Repeatability Atlas."""
from __future__ import annotations

import re
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from prompt_atlas_core import (
    AtlasEntry, deduplicate_samples, locate_font, primary_roles, render_card,
    sample_public_dict, select_primary, temporal_quantiles,
)
from prompt_atlas_github import (
    choose_highlights, collect_samples, download_archives, download_metadata,
    extract_images, group_candidates,
)
from prompt_atlas_packages import chunks, create_release_packages, save_json

DATE_FROM_TAG = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})")


def build(
    rows: list[dict[str, Any]],
    fingerprint: str,
    config: dict[str, Any],
    work: Path,
    output: Path,
    batch_id: str,
) -> tuple[list[AtlasEntry], dict[str, Any]]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    roots = download_metadata(rows, work / "metadata")
    all_samples = collect_samples(rows, roots)
    groups = group_candidates(all_samples, "all")
    extract_images(groups, download_archives(groups, work / "archives"), work / "extracted")

    entries: list[AtlasEntry] = []
    missing: list[dict[str, Any]] = []
    latest_tag = str(rows[-1].get("tagName") or "") if rows else ""
    full_page_size = max(2, int(config.get("full_page_samples", 16)))
    extended_max = max(5, int(config.get("extended_max_samples", 16)))

    for cohort_id, raw in sorted(
        groups.items(),
        key=lambda item: (item[1][0].prompt_id, item[1][0].model, item[0]),
    ):
        samples = deduplicate_samples(raw, preferred_tag=latest_tag)
        if len(samples) < 2:
            missing.append(
                {
                    "cohort_id": cohort_id,
                    "prompt_id": raw[0].prompt_id,
                    "metadata_samples": len(raw),
                    "usable_unique_media": len(samples),
                }
            )
            continue

        first = samples[0]
        primary = select_primary(samples)
        primary_name = f"atlas-{first.prompt_id}-{cohort_id}-n{len(primary)}.jpg"
        render_card(
            output / "primary" / primary_name,
            prompt_id=first.prompt_id,
            category=first.category,
            prompt=first.prompt,
            model=first.model,
            cohort_id=cohort_id,
            samples=primary,
            roles=primary_roles(primary),
            config=config,
        )

        extended_name = None
        extended: list[Any] = []
        if len(samples) >= int(config.get("extended_min_samples", 5)):
            extended = temporal_quantiles(samples, min(extended_max, len(samples)))
            extended_name = f"atlas-{first.prompt_id}-{cohort_id}-extended-n{len(extended)}.jpg"
            render_card(
                output / "extended" / extended_name,
                prompt_id=first.prompt_id,
                category=first.category,
                prompt=first.prompt,
                model=first.model,
                cohort_id=cohort_id,
                samples=extended,
                roles=[f"Temporal {index + 1}/{len(extended)}" for index in range(len(extended))],
                config=config,
                extended=True,
            )

        full_names: list[str] = []
        sample_pages = list(chunks(samples, full_page_size))
        for page_index, page_samples in enumerate(sample_pages, 1):
            name = (
                f"{first.prompt_id}-{cohort_id}/"
                f"page-{page_index:03d}-of-{len(sample_pages):03d}-n{len(page_samples)}.jpg"
            )
            full_names.append(name)
            start = (page_index - 1) * full_page_size
            render_card(
                output / "full" / name,
                prompt_id=first.prompt_id,
                category=first.category,
                prompt=first.prompt,
                model=first.model,
                cohort_id=cohort_id,
                samples=page_samples,
                roles=[f"Sample {start + index + 1}/{len(samples)}" for index in range(len(page_samples))],
                config=config,
                extended=True,
            )

        sidecar_name = f"atlas-{first.prompt_id}-{cohort_id}.json"
        save_json(
            output / "sidecars" / sidecar_name,
            {
                "schema_version": 2,
                "dataset_scope": "all_published_media_exp_releases",
                "dataset_fingerprint": fingerprint,
                "latest_source_tag": latest_tag,
                "prompt_id": first.prompt_id,
                "category": first.category,
                "prompt": first.prompt,
                "model": first.model,
                "settings": first.settings,
                "cohort_id": cohort_id,
                "sample_count": len(samples),
                "selection_policy": {
                    "primary": "earliest, temporal history anchors, latest cohort sample",
                    "extended": f"up to {extended_max} temporal quantiles",
                    "full": f"all unique samples paginated at {full_page_size} per sheet",
                    "deduplication": "exact SHA-256",
                },
                "all_samples": [sample_public_dict(item) for item in samples],
                "primary_samples": [sample_public_dict(item) for item in primary],
                "extended_samples": [sample_public_dict(item) for item in extended],
                "full_files": full_names,
                "rendering": {
                    "fit": "contain",
                    "primary_cell_size": config.get("cell_size", 960),
                    "extended_cell_size": config.get("extended_cell_size", 640),
                    "font": str(locate_font(config) or "Pillow default"),
                },
            },
        )
        entries.append(
            AtlasEntry(
                first.prompt_id,
                first.category,
                first.prompt,
                first.model,
                cohort_id,
                len(samples),
                latest_tag,
                primary_name,
                sidecar_name,
                extended_name,
                [sample_public_dict(item) for item in primary],
                [sample_public_dict(item) for item in extended],
                full_names,
            )
        )

    dates = [
        match.group(1)
        for row in rows
        if (match := DATE_FROM_TAG.match(str(row.get("tagName") or "")))
    ]
    report = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "batch_id": batch_id,
        "dataset_scope": "all_published_media_exp_releases",
        "dataset_fingerprint": fingerprint,
        "latest_source_tag": latest_tag,
        "release_tags": [str(row.get("tagName") or "") for row in rows],
        "release_count_scanned": len(rows),
        "date_from": min(dates) if dates else None,
        "date_to": max(dates) if dates else None,
        "metadata_image_samples": len(all_samples),
        "candidate_cohorts": len(groups),
        "comparable_prompts": len(entries),
        "missing_or_duplicate_media": missing,
        "entries": [asdict(entry) for entry in entries],
    }
    create_release_packages(output, entries, report, config)
    return entries, report


def safe_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "run"


def stage_highlight_previews(
    output: Path,
    preview_root: Path,
    repo: str,
    fingerprint: str,
    batch_id: str,
    entries: list[AtlasEntry],
    config: dict[str, Any],
) -> dict[str, str]:
    highlights = choose_highlights(entries, int(config.get("release_notes_highlights", 4)))
    relative_root = preview_root / fingerprint[:12] / safe_segment(batch_id)[:64]
    relative_root.mkdir(parents=True, exist_ok=True)
    urls: dict[str, str] = {}
    repo_root = Path.cwd().resolve()
    for entry in highlights:
        source = output / "primary" / entry.primary_file
        destination = relative_root / entry.primary_file
        shutil.copy2(source, destination)
        relative = destination.resolve().relative_to(repo_root).as_posix()
        urls[entry.cohort_id] = (
            f"https://raw.githubusercontent.com/{repo}/main/{quote(relative, safe='/')}"
        )
    return urls


def write_pages_index(
    path: Path,
    report: dict[str, Any],
    publication: dict[str, Any] | None,
    preview_urls: dict[str, str],
) -> None:
    assets = publication.get("assets", {}) if publication else {}
    entries = [
        {
            "prompt_id": item["prompt_id"],
            "category": item["category"],
            "prompt": item["prompt"],
            "model": item["model"],
            "cohort_id": item["cohort_id"],
            "sample_count": item["sample_count"],
            "primary_url": preview_urls.get(item["cohort_id"]),
            "bundle_url": assets.get(item.get("bundle_file") or ""),
            "has_extended": bool(item.get("extended_file")),
            "full_page_count": len(item.get("full_files") or []),
        }
        for item in report.get("entries", [])
    ]
    save_json(
        path,
        {
            "schema_version": 2,
            "status": "published" if publication else ("no_comparable_prompts" if not entries else "built_not_published"),
            "generated_at_utc": report.get("generated_at_utc"),
            "dataset_scope": report.get("dataset_scope"),
            "dataset_fingerprint": report.get("dataset_fingerprint"),
            "source_tag": "all published data",
            "latest_source_tag": report.get("latest_source_tag"),
            "release_count_scanned": report.get("release_count_scanned"),
            "date_from": report.get("date_from"),
            "date_to": report.get("date_to"),
            "comparable_prompts": len(entries),
            "analysis_tag": publication.get("analysis_tag") if publication else None,
            "analysis_url": publication.get("analysis_url") if publication else None,
            "archive_url": publication.get("archive_url") if publication else None,
            "archive_urls": publication.get("archive_urls", []) if publication else [],
            "report_url": publication.get("report_url") if publication else None,
            "highlights": publication.get("highlights", []) if publication else [],
            "entries": entries,
        },
    )
