"""Publication primitives for the full-corpus Prompt Repeatability Atlas."""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from prompt_atlas_data import command

ANALYSIS_VERSION_RE = re.compile(r"-v(\d+)$")


def media_type(entry: Any) -> str:
    return str(getattr(entry, "media_type", "image") or "image")


def choose_highlights(
    entries: Sequence[Any],
    limit: int,
    *,
    media: str | None = None,
) -> list[Any]:
    candidates = [
        entry
        for entry in entries
        if media is None or media_type(entry) == media
    ]
    ranked = sorted(
        candidates,
        key=lambda entry: (
            -min(entry.sample_count, 32),
            entry.category,
            entry.prompt_id,
            entry.cohort_id,
        ),
    )
    selected: list[Any] = []
    categories: set[str] = set()
    for entry in ranked:
        if len(selected) >= limit:
            break
        if entry.category not in categories:
            selected.append(entry)
            categories.add(entry.category)
    for entry in ranked:
        if len(selected) >= limit:
            break
        if entry not in selected:
            selected.append(entry)
    return selected


def choose_release_highlights(
    entries: Sequence[Any],
    config: dict[str, Any],
) -> list[Any]:
    image_limit = max(
        0,
        int(
            config.get(
                "release_notes_image_highlights",
                config.get("release_notes_highlights", 4),
            )
        ),
    )
    video_limit = max(
        0,
        int(config.get("release_notes_video_highlights", 2)),
    )
    return [
        *choose_highlights(entries, image_limit, media="image"),
        *choose_highlights(entries, video_limit, media="video"),
    ]


def release_asset_url(repo: str, tag: str, asset_name: str) -> str:
    return (
        f"https://github.com/{repo}/releases/download/"
        f"{quote(tag, safe='')}/{quote(asset_name, safe='')}"
    )


def release_page_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def asset_map(repo: str, tag: str) -> tuple[dict[str, str], str]:
    release = json.loads(
        command(["gh", "api", f"repos/{repo}/releases/tags/{tag}"]).stdout
    )
    return (
        {
            str(asset["name"]): str(asset["browser_download_url"])
            for asset in release.get("assets", [])
        },
        str(release.get("html_url") or ""),
    )


def analysis_tag_for_dataset(
    fingerprint: str,
    releases: Sequence[dict[str, Any]],
    *,
    force: bool = False,
) -> tuple[str, bool, bool]:
    base = f"media-analysis-all-{fingerprint[:12]}"
    drafts: list[tuple[int, str]] = []
    published: list[tuple[int, str]] = []
    for release in releases:
        tag = str(release.get("tagName") or "")
        if not tag.startswith(base + "-v"):
            continue
        match = ANALYSIS_VERSION_RE.search(tag)
        if not match:
            continue
        row = (int(match.group(1)), tag)
        (drafts if release.get("isDraft") else published).append(row)
    if drafts:
        return max(drafts)[1], True, False
    if published and not force:
        return max(published)[1], False, True
    next_version = max(
        [number for number, _ in drafts + published],
        default=0,
    ) + 1
    return f"{base}-v{next_version}", False, False


def complete_asset_names(assets: dict[str, str]) -> list[str]:
    return sorted(
        name
        for name in assets
        if name.startswith("prompt-repeatability-atlas-complete")
    )


def publication_result(
    tag: str,
    release_url: str,
    assets: dict[str, str],
    entries: Sequence[Any],
    config: dict[str, Any],
    *,
    resumed: bool,
    reused: bool,
) -> dict[str, Any]:
    complete_names = complete_asset_names(assets)
    highlights = choose_release_highlights(entries, config)
    return {
        "analysis_tag": tag,
        "analysis_url": release_url,
        "archive_url": next(
            (assets.get(name) for name in complete_names if assets.get(name)),
            None,
        ),
        "archive_urls": [
            assets[name]
            for name in complete_names
            if name in assets
        ],
        "report_url": assets.get("atlas-metadata.zip"),
        "gallery_url": assets.get("offline-gallery.zip"),
        "highlights": [
            {
                "media_type": media_type(entry),
                "prompt_id": entry.prompt_id,
                "cohort_id": entry.cohort_id,
            }
            for entry in highlights
        ],
        "assets": assets,
        "resumed_draft": resumed,
        "reused_published": reused,
    }


def publish_release(
    repo: str,
    dataset_fingerprint_value: str,
    output_root: Path,
    entries: list[Any],
    config: dict[str, Any],
    report: dict[str, Any],
    preview_urls: dict[str, str],
    *,
    force: bool = False,
) -> dict[str, Any]:
    listed = json.loads(
        command(
            [
                "gh",
                "release",
                "list",
                "--repo",
                repo,
                "--limit",
                "1000",
                "--json",
                "tagName,isDraft,publishedAt",
            ]
        ).stdout
        or "[]"
    )
    tag, resumed, reused = analysis_tag_for_dataset(
        dataset_fingerprint_value,
        listed,
        force=force,
    )
    title = (
        "Prompt Repeatability Atlas — Images + Videos "
        f"({report.get('date_from') or 'unknown'} → "
        f"{report.get('date_to') or 'unknown'})"
    )
    release_assets = sorted((output_root / "release-assets").glob("*.zip"))
    if not release_assets:
        raise RuntimeError("No ZIP release assets were created")
    non_zip = [
        path.name
        for path in release_assets
        if path.suffix.lower() != ".zip"
    ]
    if non_zip:
        raise RuntimeError(
            "Atlas Release assets must all be ZIP containers: "
            + ", ".join(non_zip)
        )

    if reused:
        assets, release_url = asset_map(repo, tag)
        return publication_result(
            tag,
            release_url,
            assets,
            entries,
            config,
            resumed=False,
            reused=True,
        )

    preliminary = output_root / "release-notes-preliminary.md"
    preliminary.write_text(
        "# Prompt Repeatability Atlas\n\n"
        "Rendering is complete. ZIP assets and inline previews are being finalized.\n",
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

    chunk_size = int(config.get("upload_chunk_size", 80))
    for start in range(0, len(release_assets), chunk_size):
        upload = [
            "gh",
            "release",
            "upload",
            tag,
            "--repo",
            repo,
            *map(str, release_assets[start : start + chunk_size]),
        ]
        if resumed:
            upload.append("--clobber")
        command(upload)

    planned_assets = {
        path.name: release_asset_url(repo, tag, path.name)
        for path in release_assets
    }
    release_url = release_page_url(repo, tag)
    highlights = choose_release_highlights(entries, config)
    complete_names = complete_asset_names(planned_assets)
    complete_links = " · ".join(
        f"[Complete part {index + 1}]({planned_assets[name]})"
        for index, name in enumerate(complete_names)
    )
    image_count = int(report.get("comparable_image_prompts") or 0)
    video_count = int(report.get("comparable_video_prompts") or 0)
    prompts_per_bundle = max(
        1,
        int(config.get("prompts_per_bundle", 15)),
    )
    video_prompts_per_bundle = max(
        1,
        int(
            config.get(
                "video_prompts_per_bundle",
                prompts_per_bundle,
            )
        ),
    )

    notes = [
        "# Prompt Repeatability Atlas",
        "",
        "A full-corpus image + video snapshot built from every currently "
        "published `media-exp-*` Release.",
        "",
        f"- Dataset fingerprint: `{dataset_fingerprint_value}`",
        f"- Experiment Releases scanned: **{report.get('release_count_scanned', 0)}**",
        f"- Date range: **{report.get('date_from') or '—'} → "
        f"{report.get('date_to') or '—'}**",
        f"- Comparable image cohorts: **{image_count}**",
        f"- Comparable video cohorts: **{video_count}**",
        f"- Image bundles: **{report.get('prompt_bundle_count', 0)}**, "
        f"up to **{prompts_per_bundle} prompt IDs per ZIP**",
        f"- Video bundles: **{report.get('video_prompt_bundle_count', 0)}**, "
        f"up to **{video_prompts_per_bundle} prompt IDs per ZIP**",
        f"- Embedded previews: **{len(highlights)}** static cards / animated GIFs",
        "- Every Release asset is a ZIP container; there are no naked JPG, "
        "JSON, GIF, MP4, or HTML assets.",
        "- Video evidence includes synchronized GIF comparisons, "
        "10%/50%/90% keyframe sheets, FFprobe metadata, and exact source references.",
        "",
        complete_links or f"[All ZIP assets]({release_url})",
        f"[Metadata package]({planned_assets.get('atlas-metadata.zip', release_url)}) · "
        f"[Offline gallery package]({planned_assets.get('offline-gallery.zip', release_url)})",
        "",
        "## Highlights",
        "",
    ]
    for entry in highlights:
        kind = media_type(entry)
        preview = preview_urls.get(entry.cohort_id)
        bundle = planned_assets.get(entry.bundle_file or "", release_url)
        notes.extend(
            [
                f"### {entry.prompt_id} · {kind} · {entry.category} · "
                f"{entry.sample_count} unique samples",
                "",
                textwrap.shorten(
                    entry.prompt,
                    width=240,
                    placeholder="…",
                ),
                "",
            ]
        )
        if preview:
            notes.extend(
                [
                    f"[![{entry.prompt_id} {kind} repeatability comparison]"
                    f"({preview})]({preview})",
                    "",
                ]
            )
        bundle_size = (
            video_prompts_per_bundle
            if kind == "video"
            else prompts_per_bundle
        )
        notes.extend(
            [
                f"[Download the containing {bundle_size}-prompt "
                f"{kind} bundle]({bundle})",
                "",
            ]
        )
    notes.extend(
        [
            "## Interpretation",
            "",
            "Image primary cards summarize temporal anchors; full image pages "
            "contain every verified byte-unique sample. Video primary GIFs "
            "synchronize all tiles from t=0, pad short clips on their final frame, "
            "and use contain/letterbox without cropping. Video keyframe pages "
            "include 10%, 50%, and 90% frames for every verified byte-unique clip.",
        ]
    )
    final_notes = output_root / "release-notes.md"
    final_notes.write_text("\n".join(notes) + "\n", encoding="utf-8")
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
            str(final_notes),
            "--draft=false",
            "--latest=false",
        ]
    )

    assets, verified_release_url = asset_map(repo, tag)
    expected = {path.name for path in release_assets}
    missing = sorted(expected.difference(assets))
    if missing:
        raise RuntimeError(
            f"Published release {tag} is missing ZIP assets: "
            f"{', '.join(missing)}"
        )
    if any(not name.endswith(".zip") for name in assets):
        raise RuntimeError(
            f"Published release {tag} contains a non-ZIP asset"
        )
    return publication_result(
        tag,
        verified_release_url or release_url,
        assets,
        entries,
        config,
        resumed=resumed,
        reused=False,
    )
