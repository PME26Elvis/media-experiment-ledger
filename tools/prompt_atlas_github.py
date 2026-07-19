"""GitHub Release I/O for Prompt Repeatability Atlas."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence
from urllib.parse import quote

from PIL import Image

from prompt_atlas_core import MEDIA_TAG_RE, AtlasEntry, Sample, cohort_identity, member_matches, normalized_settings

ANALYSIS_VERSION_RE = re.compile(r"-v(\d+)$")


class CommandError(RuntimeError):
    pass


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise CommandError(f"Command failed ({result.returncode}): {' '.join(args)}\n{(result.stderr or result.stdout).strip()}")
    return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected object")
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def release_rows() -> list[dict[str, Any]]:
    result = command(["gh", "release", "list", "--limit", "1000", "--json", "tagName,publishedAt,name,isDraft,isPrerelease"])
    rows = json.loads(result.stdout or "[]")
    rows = [row for row in rows if MEDIA_TAG_RE.match(str(row.get("tagName") or "")) and not row.get("isDraft")]
    return sorted(rows, key=lambda row: (str(row.get("publishedAt") or ""), str(row.get("tagName") or "")))


def resolve_source_tag(rows: Sequence[dict[str, Any]], requested: str) -> str:
    tags = [str(row["tagName"]) for row in rows]
    if not tags:
        raise ValueError("No published media-exp-* releases found")
    if requested in {"", "latest"}:
        return tags[-1]
    if requested not in tags:
        raise ValueError(f"Unknown source tag {requested}; latest is {tags[-1]}")
    return requested


def download_metadata(rows: Sequence[dict[str, Any]], root: Path) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for row in rows:
        tag = str(row["tagName"])
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        command(["gh", "release", "download", tag, "--pattern", "run_*-outputs.jsonl", "--dir", str(target)], check=False)
        roots[tag] = target
    return roots


def collect_samples(rows: Sequence[dict[str, Any]], roots: dict[str, Path]) -> list[Sample]:
    published = {str(row["tagName"]): str(row.get("publishedAt") or "") for row in rows}
    output: list[Sample] = []
    for tag, root in roots.items():
        for path in sorted(root.glob("run_*-outputs.jsonl")):
            run_id = path.name.removesuffix("-outputs.jsonl")
            for record in read_jsonl(path):
                if record.get("event") != "image_completed" or not record.get("prompt_id"):
                    continue
                payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
                prompt_id = str(record["prompt_id"])
                model = str(payload.get("model") or "unknown-model")
                settings = normalized_settings(payload)
                output.append(Sample(
                    prompt_id=prompt_id,
                    category=str(record.get("category") or "uncategorized"),
                    prompt=str(payload.get("prompt") or ""),
                    model=model,
                    settings=settings,
                    cohort_id=cohort_identity(prompt_id, model, settings),
                    source_tag=tag,
                    release_published_at=published.get(tag, ""),
                    run_id=run_id,
                    timestamp=str(record.get("timestamp") or ""),
                    finished_at=str(record.get("finished_at") or ""),
                    local_path=str(record.get("local_path")) if record.get("local_path") else None,
                    seed=record.get("seed") or payload.get("seed"),
                ))
    return sorted(output, key=lambda item: item.sort_key)


def group_candidates(samples: Sequence[Sample], source_tag: str) -> dict[str, list[Sample]]:
    target = {sample.cohort_id for sample in samples if sample.source_tag == source_tag}
    groups: dict[str, list[Sample]] = {}
    for sample in samples:
        if sample.cohort_id in target:
            groups.setdefault(sample.cohort_id, []).append(sample)
    return {key: sorted(value, key=lambda item: item.sort_key) for key, value in groups.items() if len(value) >= 2}


def download_archives(groups: dict[str, list[Sample]], root: Path) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for tag in sorted({sample.source_tag for group in groups.values() for sample in group}):
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        command(["gh", "release", "download", tag, "--pattern", "run_*-images*.zip", "--dir", str(target)], check=False)
        roots[tag] = target
    return roots


def extract_images(groups: dict[str, list[Sample]], archive_roots: dict[str, Path], extract_root: Path) -> None:
    needed: dict[tuple[str, str], set[str]] = {}
    index: dict[tuple[str, str, str], list[Sample]] = {}
    for group in groups.values():
        for sample in group:
            needed.setdefault((sample.source_tag, sample.run_id), set()).add(sample.prompt_id)
            index.setdefault((sample.source_tag, sample.run_id, sample.prompt_id), []).append(sample)

    for tag, root in archive_roots.items():
        for archive_path in sorted(root.glob("run_*-images*.zip")):
            run_id = archive_path.name.split("-images", 1)[0] if "-images" in archive_path.name else None
            if not run_id or (tag, run_id) not in needed:
                continue
            try:
                archive = zipfile.ZipFile(archive_path)
            except zipfile.BadZipFile:
                continue
            with archive:
                for member in archive.namelist():
                    prompt_id = next((pid for pid in needed[(tag, run_id)] if member_matches(member, pid)), None)
                    if not prompt_id:
                        continue
                    destination = extract_root / tag / run_id / PurePosixPath(member).name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    try:
                        with Image.open(destination) as image:
                            image.verify()
                        with Image.open(destination) as image:
                            width, height = image.size
                    except Exception:
                        destination.unlink(missing_ok=True)
                        continue
                    digest = sha256_file(destination)
                    for sample in index.get((tag, run_id, prompt_id), []):
                        sample.archive_name = archive_path.name
                        sample.archive_member = member
                        sample.extracted_path = str(destination)
                        sample.sha256 = digest
                        sample.width = width
                        sample.height = height


def choose_highlights(entries: Sequence[AtlasEntry], limit: int) -> list[AtlasEntry]:
    ranked = sorted(entries, key=lambda entry: (-min(entry.sample_count, 8), entry.category, entry.prompt_id))
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


def next_analysis_tag(source_tag: str, existing_tags: Iterable[str]) -> str:
    base = source_tag.replace("media-exp-", "media-analysis-", 1)
    versions = []
    for tag in existing_tags:
        if tag.startswith(base + "-v") and (match := ANALYSIS_VERSION_RE.search(tag)):
            versions.append(int(match.group(1)))
    return f"{base}-v{max(versions, default=0) + 1}"


def analysis_tag_for_run(source_tag: str, releases: Sequence[dict[str, Any]]) -> tuple[str, bool]:
    """Resume the newest matching draft; otherwise allocate the next immutable version."""
    base = source_tag.replace("media-exp-", "media-analysis-", 1)
    matching_drafts: list[tuple[int, str]] = []
    all_tags: list[str] = []
    for release in releases:
        tag = str(release.get("tagName") or "")
        if not tag:
            continue
        all_tags.append(tag)
        if not release.get("isDraft") or not tag.startswith(base + "-v"):
            continue
        match = ANALYSIS_VERSION_RE.search(tag)
        if match:
            matching_drafts.append((int(match.group(1)), tag))
    if matching_drafts:
        return max(matching_drafts)[1], True
    return next_analysis_tag(source_tag, all_tags), False


def release_asset_url(repo: str, tag: str, asset_name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{quote(tag, safe='')}/{quote(asset_name, safe='')}"


def release_page_url(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def asset_map(repo: str, tag: str) -> tuple[dict[str, str], str]:
    # This endpoint intentionally runs only after publication. GitHub's
    # releases/tags endpoint returns published releases, not drafts.
    release = json.loads(command(["gh", "api", f"repos/{repo}/releases/tags/{tag}"]).stdout)
    return ({str(asset["name"]): str(asset["browser_download_url"]) for asset in release.get("assets", [])}, str(release.get("html_url") or ""))


def publish_release(repo: str, source_tag: str, output_root: Path, entries: list[AtlasEntry], config: dict[str, Any]) -> dict[str, Any]:
    listed = json.loads(command([
        "gh", "release", "list", "--repo", repo, "--limit", "1000", "--json", "tagName,isDraft,publishedAt"
    ]).stdout or "[]")
    tag, resumed = analysis_tag_for_run(source_tag, listed)
    title = f"Prompt Repeatability Atlas — {source_tag}"

    preliminary = output_root / "release-notes-preliminary.md"
    preliminary.write_text(
        "# Prompt Repeatability Atlas\n\nRendering is complete. Assets and inline previews are being finalized.\n",
        encoding="utf-8",
    )
    if not resumed:
        command([
            "gh", "release", "create", tag, "--repo", repo, "--title", title,
            "--notes-file", str(preliminary), "--draft", "--latest=false",
        ])

    archive = output_root / "prompt-repeatability-atlas.zip"
    report = output_root / "atlas-report.json"
    gallery = output_root / "index.html"
    files = [*(output_root / "primary" / entry.primary_file for entry in entries), report, archive, gallery]
    chunk_size = int(config.get("upload_chunk_size", 80))
    for start in range(0, len(files), chunk_size):
        upload = ["gh", "release", "upload", tag, "--repo", repo, *map(str, files[start : start + chunk_size])]
        if resumed:
            upload.append("--clobber")
        command(upload)

    highlights = choose_highlights(entries, int(config.get("release_notes_highlights", 4)))
    source_url = release_page_url(repo, source_tag)
    planned_assets = {path.name: release_asset_url(repo, tag, path.name) for path in files}
    release_url = release_page_url(repo, tag)
    notes = [
        "# Prompt Repeatability Atlas",
        "",
        f"Generated from [{source_tag}]({source_url}) with identical prompt ID, model, and appearance-relevant settings per cohort.",
        "",
        f"- Comparable prompts: **{len(entries)}**",
        f"- Embedded highlights: **{len(highlights)}**",
        "- Complete ZIP includes all primary cards, extended temporal sheets, JSON sidecars, and an offline gallery.",
        "",
        f"[Download the complete atlas ZIP]({planned_assets[archive.name]}) · [Machine-readable report]({planned_assets[report.name]})",
        "",
        "## Highlights",
        "",
    ]
    for entry in highlights:
        url = planned_assets[entry.primary_file]
        notes.extend([
            f"### {entry.prompt_id} · {entry.category} · {entry.sample_count} samples",
            "",
            textwrap.shorten(entry.prompt, width=220, placeholder="…"),
            "",
            f"[![{entry.prompt_id} repeatability comparison]({url})]({url})",
            "",
        ])
    notes.extend([
        "## Interpretation",
        "",
        "Differences inside a card primarily represent stochastic run variability. Different models or appearance-relevant settings are separated into different cohorts.",
    ])
    final_notes = output_root / "release-notes.md"
    final_notes.write_text("\n".join(notes) + "\n", encoding="utf-8")

    # Publish only after the final notes already reference every uploaded image.
    # The URLs are deterministic and become public atomically with the release.
    command([
        "gh", "release", "edit", tag, "--repo", repo, "--title", title,
        "--notes-file", str(final_notes), "--draft=false", "--latest=false",
    ])

    assets, verified_release_url = asset_map(repo, tag)
    expected = {path.name for path in files}
    missing = sorted(expected.difference(assets))
    if missing:
        raise RuntimeError(f"Published release {tag} is missing assets: {', '.join(missing)}")
    for entry in highlights:
        if entry.primary_file not in assets:
            raise RuntimeError(f"Published release {tag} is missing highlight asset {entry.primary_file}")

    return {
        "analysis_tag": tag,
        "analysis_url": verified_release_url or release_url,
        "source_tag": source_tag,
        "source_url": source_url,
        "archive_url": assets.get(archive.name),
        "report_url": assets.get(report.name),
        "gallery_url": assets.get(gallery.name),
        "highlights": [entry.prompt_id for entry in highlights],
        "assets": assets,
        "resumed_draft": resumed,
    }
