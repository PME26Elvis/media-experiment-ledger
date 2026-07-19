"""Remote Release publication and batch-level Atlas dispatch."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from release_packaging import CommandError, RunPlan, inspect_run, json_digest, package_run, run_command

TAG_RE = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})(?:-s(\d{2}))?$")
PUBLISHED_TAG_RE = re.compile(r"^PUBLISHED\s+\d{4}-\d{2}-\d{2}:\s+(media-exp-[^\s]+)")
TAIPEI = ZoneInfo("Asia/Taipei")


def gh_repo() -> str:
    proc = run_command(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]
    )
    value = (proc.stdout or "").strip()
    if not value:
        raise CommandError("Could not resolve repository with gh repo view")
    return value


def list_release_tags() -> list[str]:
    proc = run_command(
        [
            "gh",
            "release",
            "list",
            "--limit",
            "1000",
            "--json",
            "tagName",
            "--jq",
            ".[].tagName",
        ]
    )
    return [
        line.strip()
        for line in (proc.stdout or "").splitlines()
        if line.strip()
    ]


def date_release_tags(all_tags: Sequence[str], date: str) -> list[str]:
    matches: list[tuple[int, str]] = []
    for tag in all_tags:
        match = TAG_RE.match(tag)
        if not match or match.group(1) != date:
            continue
        supplement = int(match.group(2) or 0)
        matches.append((supplement, tag))
    return [tag for _, tag in sorted(matches)]


def load_remote_manifests(
    tags: Sequence[str], date: str
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    runs: dict[str, str] = {}
    manifests: list[dict[str, Any]] = []
    for tag in tags:
        with tempfile.TemporaryDirectory(prefix="ledger-manifest-") as tmp:
            proc = run_command(
                [
                    "gh",
                    "release",
                    "download",
                    tag,
                    "--pattern",
                    f"manifest-{date}*.json",
                    "--dir",
                    tmp,
                ],
                check=False,
            )
            if proc.returncode != 0:
                continue
            for path in sorted(Path(tmp).glob("manifest-*.json")):
                try:
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                manifests.append(manifest)
                for run in manifest.get("runs", []):
                    if (
                        isinstance(run, dict)
                        and run.get("run_id")
                        and run.get("digest")
                    ):
                        runs[str(run["run_id"])] = str(run["digest"])
    return runs, manifests


def build_manifest(
    date: str,
    tag: str,
    plans: Sequence[RunPlan],
    repo: str,
    existing_tags: Sequence[str],
) -> dict[str, Any]:
    created_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    created_taipei = datetime.now(TAIPEI).replace(microsecond=0).isoformat()
    runs = []
    for plan in plans:
        runs.append(
            {
                "run_id": plan.run_id,
                "digest": plan.digest,
                "stats": plan.stats,
                "files": list(plan.files),
                "assets": [
                    {
                        "name": asset.name,
                        "kind": asset.kind,
                        "size_bytes": asset.size_bytes,
                        "sha256": asset.sha256,
                    }
                    for asset in plan.assets
                ],
            }
        )
    manifest = {
        "schema_version": 1,
        "repository": repo,
        "tag": tag,
        "experiment_date_taipei": date,
        "timezone": "Asia/Taipei",
        "created_at_taipei": created_taipei,
        "created_at_utc": created_utc,
        "release_kind": "supplement" if existing_tags else "primary",
        "previous_release_tags": list(existing_tags),
        "runs": runs,
    }
    manifest["content_digest"] = json_digest(
        {
            "date": date,
            "runs": [
                {"run_id": p.run_id, "digest": p.digest}
                for p in plans
            ],
        }
    )
    return manifest


def release_notes(manifest: dict[str, Any]) -> str:
    runs = manifest["runs"]
    image_count = sum(
        int(run["stats"].get("image_completed", 0)) for run in runs
    )
    video_count = sum(
        int(run["stats"].get("video_completed", 0)) for run in runs
    )
    error_count = sum(int(run["stats"].get("errors", 0)) for run in runs)
    media_bytes = sum(
        int(asset["size_bytes"])
        for run in runs
        for asset in run["assets"]
        if asset["kind"] in {"images", "videos"}
    )
    models = sorted(
        {model for run in runs for model in run["stats"].get("models", [])}
    )
    lines = [
        f"Experiment date: **{manifest['experiment_date_taipei']}** (Asia/Taipei)",
        f"Runs: **{len(runs)}**",
        f"Images completed: **{image_count:,}**",
        f"Videos completed: **{video_count:,}**",
        f"Errors: **{error_count:,}**",
        f"Packaged media: **{media_bytes / 1024**3:.2f} GiB**",
        "",
        "## Included runs",
    ]
    lines.extend(f"- `{run['run_id']}`" for run in runs)
    if models:
        lines.extend(["", "## Models", *[f"- `{model}`" for model in models]])
    lines.extend(
        [
            "",
            "## Data layout",
            "Media is grouped by run and media type. JSONL metadata and the "
            "release manifest are separate assets so analytics can run without "
            "downloading media archives.",
            "",
            f"Manifest digest: `{manifest['content_digest']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def next_tag(date: str, existing_tags: Sequence[str]) -> tuple[str, str]:
    if not existing_tags:
        return f"media-exp-{date}", f"Media Experiment — {date}"
    supplements = []
    for tag in existing_tags:
        match = TAG_RE.match(tag)
        supplements.append(int(match.group(2) or 0) if match else 0)
    number = max(supplements) + 1
    return (
        f"media-exp-{date}-s{number:02d}",
        f"Media Experiment — {date} · Supplement {number:02d}",
    )


def publish_date(
    date_dir: Path,
    staging_root: Path,
    max_part_bytes: int,
    all_tags: list[str],
    dry_run: bool,
) -> str:
    date = date_dir.name
    existing_tags = date_release_tags(all_tags, date)
    remote_runs, _ = load_remote_manifests(existing_tags, date)
    run_dirs = sorted(
        (
            p
            for p in date_dir.iterdir()
            if p.is_dir() and p.name.startswith("run_")
        ),
        key=lambda p: p.name,
    )
    if not run_dirs:
        return f"SKIP {date}: no run_* directories"

    date_staging = staging_root / date
    if date_staging.exists():
        shutil.rmtree(date_staging)
    date_staging.mkdir(parents=True)

    unpublished: list[RunPlan] = []
    conflicts: list[str] = []
    for run_dir in run_dirs:
        inspected = inspect_run(run_dir)
        remote_digest = remote_runs.get(inspected.run_id)
        if remote_digest is None:
            unpublished.append(inspected)
        elif remote_digest != inspected.digest:
            conflicts.append(
                f"{inspected.run_id}: local {inspected.digest[:12]} "
                f"!= remote {remote_digest[:12]}"
            )

    if conflicts:
        raise ValueError(
            f"{date}: existing run IDs have different content:\n- "
            + "\n- ".join(conflicts)
        )
    if not unpublished:
        shutil.rmtree(date_staging, ignore_errors=True)
        return f"SKIP {date}: all {len(run_dirs)} run(s) already published"

    planned = [
        package_run(plan, date_staging, max_part_bytes)
        for plan in unpublished
    ]
    tag, title = next_tag(date, existing_tags)
    repo = gh_repo()
    manifest = build_manifest(date, tag, planned, repo, existing_tags)
    manifest_path = date_staging / f"manifest-{date}.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    notes_path = date_staging / f"release-notes-{date}.md"
    notes_path.write_text(release_notes(manifest), encoding="utf-8")

    all_assets = [
        asset.path
        for plan in planned
        for asset in plan.assets
    ] + [manifest_path]
    if dry_run:
        return (
            f"DRY-RUN {date}: would create {tag} with {len(planned)} run(s), "
            f"{len(all_assets)} asset(s)"
        )

    cmd = [
        "gh",
        "release",
        "create",
        tag,
        *[str(path) for path in all_assets],
        "--title",
        title,
        "--notes-file",
        str(notes_path),
    ]
    run_command(cmd, capture=False)
    all_tags.append(tag)
    shutil.rmtree(date_staging, ignore_errors=True)
    return (
        f"PUBLISHED {date}: {tag} "
        f"({len(planned)} new run(s), {len(all_assets)} asset(s))"
    )


def atlas_batch_id(published_tags: Sequence[str]) -> str:
    timestamp = datetime.now(TAIPEI).strftime("%Y%m%d-%H%M%S")
    digest = json_digest(sorted(published_tags))[:10]
    return f"batch-{timestamp}-{len(published_tags)}releases-{digest}"


def atlas_dispatch_command(
    repo: str,
    published_tags: Sequence[str],
    *,
    batch_id: str | None = None,
) -> list[str]:
    resolved_batch_id = batch_id or atlas_batch_id(published_tags)
    return [
        "gh",
        "workflow",
        "run",
        "visual-analysis.yml",
        "--repo",
        repo,
        "--ref",
        "main",
        "-f",
        f"batch_id={resolved_batch_id}",
        "-f",
        "force=false",
    ]


def dispatch_full_atlas(repo: str, published_tags: Sequence[str]) -> str:
    if not published_tags:
        raise ValueError("Cannot dispatch an Atlas without newly published Releases")
    batch_id = atlas_batch_id(published_tags)
    run_command(atlas_dispatch_command(repo, published_tags, batch_id=batch_id))
    return batch_id
