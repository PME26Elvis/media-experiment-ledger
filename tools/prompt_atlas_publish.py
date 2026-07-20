"""Publication primitives for the full-corpus Prompt Repeatability Atlas."""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from prompt_atlas_core import AtlasEntry
from prompt_atlas_data import command

ANALYSIS_VERSION_RE = re.compile(r"-v(\d+)$")


def choose_highlights(entries: Sequence[AtlasEntry], limit: int) -> list[AtlasEntry]:
    ranked = sorted(
        entries,
        key=lambda entry: (
            -min(entry.sample_count, 32),
            entry.category,
            entry.prompt_id,
            entry.cohort_id,
        ),
    )
    selected: list[AtlasEntry] = []
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


def release_asset_url(repo: str, tag: str, asset_name: str) -> str:
    return (
        f"https://github.com/{repo}/releases/download/"
        f"{quote(tag, safe='')}/{quote(asset_name, safe='')}"
    )


def release_page_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def asset_map(repo: str, tag: str) -> tuple[dict[str, str], str]:
    release = json.loads(command(["gh", "api", f"repos/{repo}/releases/tags/{tag}"]).stdout)
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
    """Return tag, resumed-draft flag, and reused-published flag."""
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
    next_version = max([number for number, _ in drafts + published], default=0) + 1
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
    entries: Sequence[AtlasEntry],
    config: dict[str, Any],
    *,
    resumed: bool,
    reused: bool,
) -> dict[str, Any]:
    complete_names = complete_asset_names(assets)
    highlights = choose_highlights(
        entries,
        int(config.get("release_notes_highlights", 4)),
    )
    return {
        "analysis_tag": tag,
        "analysis_url": release_url,
        "archive_url": next((assets.get(name) for name in complete_names if assets.get(name)), None),
        "archive_urls": [assets[name] for name in complete_names if name in assets],
        "report_url": assets.get("atlas-metadata.zip"),
        "gallery_url": assets.get("offline-gallery.zip"),
        "highlights": [entry.prompt_id for entry in highlights],
        "assets": assets,
        "resumed_draft": resumed,
        "reused_published": reused,
    }


def publish_release(
    repo: str,
    dataset_fingerprint_value: str,
    output_root: Path,
    entries: list[AtlasEntry],
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
        "Prompt Repeatability Atlas — All Published Data "
        f"({report.get('date_from') or 'unknown'} → {report.get('date_to') or 'unknown'})"
    )
    release_assets = sorted((output_root / "release-assets").glob("*.zip"))
    if not release_assets:
        raise RuntimeError("No ZIP release assets were created")
    non_zip = [path.name for path in release_assets if path.suffix.lower() != ".zip"]
    if non_zip:
        raise RuntimeError(
            "Atlas Release assets must all be ZIP containers: " + ", ".join(non_zip)
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
    highlights = choose_highlights(
        entries,
        int(config.get("release_notes_highlights", 4)),
    )
    complete_names = complete_asset_names(planned_assets)
    complete_links = " · ".join(
        f"[Complete part {index + 1}]({planned_assets[name]})"
        for index, name in enumerate(complete_names)
    )
    prompts_per_bundle = max(1, int(config.get("prompts_per_bundle", 15)))
    bundle_count = int(report.get("prompt_bundle_count") or 0)

    notes = [
        "# Prompt Repeatability Atlas",
        "",
        "A full-corpus snapshot built from every currently published `media-exp-*` Release.",
        "",
        f"- Dataset fingerprint: `{dataset_fingerprint_value}`",
        f"- Experiment Releases scanned: **{report.get('release_count_scanned', 0)}**",
        f"- Date range: **{report.get('date_from') or '—'} → {report.get('date_to') or '—'}**",
        f"- Comparable controlled cohorts: **{len(entries)}**",
        f"- Prompt bundles: **{bundle_count}**, up to **{prompts_per_bundle} prompt IDs per ZIP**",
        f"- Embedded previews: **{len(highlights)}**",
        "- Every Release asset is a ZIP container; there are no naked JPG, JSON, GIF, or HTML assets.",
        "- Each grouped prompt bundle contains primary cards, temporal overviews, complete paginated contact sheets, sidecars, and a bundle manifest.",
        "",
        complete_links or f"[All ZIP assets]({release_url})",
        f"[Metadata package]({planned_assets.get('atlas-metadata.zip', release_url)}) · "
        f"[Offline gallery package]({planned_assets.get('offline-gallery.zip', release_url)})",
        "",
        "## Highlights",
        "",
    ]
    for entry in highlights:
        preview = preview_urls.get(entry.cohort_id)
        bundle = planned_assets.get(entry.bundle_file or "", release_url)
        notes.extend(
            [
                f"### {entry.prompt_id} · {entry.category} · {entry.sample_count} unique samples",
                "",
                textwrap.shorten(entry.prompt, width=240, placeholder="…"),
                "",
            ]
        )
        if preview:
            notes.extend(
                [
                    f"[![{entry.prompt_id} repeatability comparison]({preview})]({preview})",
                    "",
                ]
            )
        notes.extend([f"[Download the containing {prompts_per_bundle}-prompt bundle]({bundle})", ""])
    notes.extend(
        [
            "## Interpretation",
            "",
            "Primary cards summarize temporal anchors. Extended sheets sample up to "
            f"{int(config.get('extended_max_samples', 16))} temporal quantiles. "
            "The full pages include every verified byte-unique sample in chronological order.",
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
            f"Published release {tag} is missing ZIP assets: {', '.join(missing)}"
        )
    if any(not name.endswith(".zip") for name in assets):
        raise RuntimeError(f"Published release {tag} contains a non-ZIP asset")
    return publication_result(
        tag,
        verified_release_url or release_url,
        assets,
        entries,
        config,
        resumed=resumed,
        reused=False,
    )
