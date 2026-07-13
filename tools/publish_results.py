#!/usr/bin/env python3
"""Package local result runs and publish immutable date-scoped GitHub Releases.

Designed for GitHub Codespaces: upload a local ``results/`` directory, then run
one command. Media is stored in ZIP_STORED archives, metadata remains available
as standalone release assets, and previously published runs are skipped by
run-id plus content digest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_RE = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})(?:-s(\d{2}))?$")
TAIPEI = ZoneInfo("Asia/Taipei")
DEFAULT_MAX_PART_BYTES = int(1.8 * 1024**3)
SECRET_PATTERNS = (
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    re.compile(r"(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{24,}", re.I),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
)


@dataclass(frozen=True)
class Asset:
    path: Path
    name: str
    sha256: str
    size_bytes: int
    kind: str
    run_id: str | None = None


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    source_dir: Path
    digest: str
    assets: tuple[Asset, ...]
    stats: dict[str, Any]
    files: tuple[dict[str, Any], ...]


class CommandError(RuntimeError):
    pass


def run_command(cmd: Sequence[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(cmd),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise CommandError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{stderr or stdout}")
    return proc


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, errors
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
                else:
                    errors.append(f"{path.name}:{line_no}: JSON value is not an object")
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{line_no}: {exc.msg}")
    return rows, errors


def scan_metadata_for_secrets(paths: Iterable[Path]) -> None:
    findings: list[str] = []
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".log"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{path}: matched {pattern.pattern}")
                break
    if findings:
        raise ValueError("Potential secret material found in release metadata:\n- " + "\n- ".join(findings))


def discover_dates(source: Path, requested: set[str] | None = None) -> list[Path]:
    if not source.is_dir():
        raise FileNotFoundError(f"Results directory does not exist: {source}")
    dates = [p for p in source.iterdir() if p.is_dir() and DATE_RE.match(p.name)]
    if requested:
        missing = sorted(requested - {p.name for p in dates})
        if missing:
            raise FileNotFoundError(f"Requested date directories not found: {', '.join(missing)}")
        dates = [p for p in dates if p.name in requested]
    return sorted(dates, key=lambda p: p.name)


def collect_files(root: Path) -> list[Path]:
    return sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix())


def split_files(files: Sequence[Path], max_bytes: int) -> list[list[Path]]:
    parts: list[list[Path]] = []
    current: list[Path] = []
    current_bytes = 0
    for path in files:
        size = path.stat().st_size
        if size > max_bytes:
            raise ValueError(f"Single file exceeds configured part limit ({max_bytes} bytes): {path} ({size} bytes)")
        if current and current_bytes + size > max_bytes:
            parts.append(current)
            current = []
            current_bytes = 0
        current.append(path)
        current_bytes += size
    if current:
        parts.append(current)
    return parts


def create_stored_zip(zip_path: Path, run_dir: Path, files: Sequence[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(run_dir).as_posix())
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise IOError(f"ZIP verification failed for {zip_path}: {bad}")


def event_stats(outputs: Sequence[dict[str, Any]], errors: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    categories: dict[str, int] = {}
    models: set[str] = set()
    for row in outputs:
        event = str(row.get("event") or "unknown")
        counts[event] = counts.get(event, 0) + 1
        category = row.get("category")
        if category:
            categories[str(category)] = categories.get(str(category), 0) + 1
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("model"):
            models.add(str(payload["model"]))
    error_classes: dict[str, int] = {}
    for row in errors:
        name = str(row.get("error_class") or "unknown_error")
        error_classes[name] = error_classes.get(name, 0) + 1
    return {
        "event_counts": dict(sorted(counts.items())),
        "image_completed": counts.get("image_completed", 0),
        "video_completed": counts.get("video_completed", 0),
        "errors": len(errors),
        "categories": dict(sorted(categories.items())),
        "models": sorted(models),
        "error_classes": dict(sorted(error_classes.items())),
    }


def inspect_run(run_dir: Path) -> RunPlan:
    """Validate and hash one run without creating any ZIP assets."""
    run_id = run_dir.name
    if not run_id.startswith("run_"):
        raise ValueError(f"Unexpected run directory name: {run_dir}")

    outputs_path = run_dir / "outputs.jsonl"
    errors_path = run_dir / "errors.jsonl"
    metadata_paths = [p for p in (outputs_path, errors_path) if p.exists()]
    scan_metadata_for_secrets(metadata_paths)

    outputs, output_parse_errors = read_jsonl(outputs_path)
    errors, error_parse_errors = read_jsonl(errors_path)
    parse_errors = output_parse_errors + error_parse_errors
    if parse_errors:
        raise ValueError("Invalid JSONL detected:\n- " + "\n- ".join(parse_errors))

    all_files = collect_files(run_dir)
    file_records: list[dict[str, Any]] = []
    for path in all_files:
        rel = path.relative_to(run_dir).as_posix()
        file_records.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    run_digest = json_digest(file_records)

    stats = event_stats(outputs, errors)
    stats["file_count"] = len(all_files)
    stats["source_bytes"] = sum(p.stat().st_size for p in all_files)
    return RunPlan(run_id, run_dir, run_digest, tuple(), stats, tuple(file_records))


def package_run(plan: RunPlan, staging_dir: Path, max_part_bytes: int) -> RunPlan:
    """Create release assets only after a run is known to be unpublished."""
    run_dir = plan.source_dir
    run_id = plan.run_id
    assets: list[Asset] = []
    metadata_sources = [
        metadata
        for metadata in (run_dir / "outputs.jsonl", run_dir / "errors.jsonl")
        if metadata.exists()
    ]
    for metadata in metadata_sources:
        name = f"{run_id}-{metadata.name}"
        dest = staging_dir / name
        shutil.copy2(metadata, dest)
        assets.append(Asset(dest, name, sha256_file(dest), dest.stat().st_size, "metadata", run_id))

    media_groups = {
        "images": collect_files(run_dir / "media" / "images") if (run_dir / "media" / "images").is_dir() else [],
        "videos": collect_files(run_dir / "media" / "videos") if (run_dir / "media" / "videos").is_dir() else [],
    }
    for kind, files in media_groups.items():
        parts = split_files(files, max_part_bytes)
        for index, part in enumerate(parts, 1):
            suffix = f"-part{index:02d}" if len(parts) > 1 else ""
            name = f"{run_id}-{kind}{suffix}.zip"
            dest = staging_dir / name
            create_stored_zip(dest, run_dir, [*metadata_sources, *part])
            assets.append(Asset(dest, name, sha256_file(dest), dest.stat().st_size, kind, run_id))
    return RunPlan(plan.run_id, plan.source_dir, plan.digest, tuple(assets), plan.stats, plan.files)


def plan_run(run_dir: Path, staging_dir: Path, max_part_bytes: int) -> RunPlan:
    """Compatibility helper used by tests and ad-hoc packaging."""
    return package_run(inspect_run(run_dir), staging_dir, max_part_bytes)


def gh_repo() -> str:
    proc = run_command(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    value = (proc.stdout or "").strip()
    if not value:
        raise CommandError("Could not resolve repository with gh repo view")
    return value


def list_release_tags() -> list[str]:
    proc = run_command(["gh", "release", "list", "--limit", "1000", "--json", "tagName", "--jq", ".[].tagName"])
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]


def date_release_tags(all_tags: Sequence[str], date: str) -> list[str]:
    matches: list[tuple[int, str]] = []
    for tag in all_tags:
        match = TAG_RE.match(tag)
        if not match or match.group(1) != date:
            continue
        supplement = int(match.group(2) or 0)
        matches.append((supplement, tag))
    return [tag for _, tag in sorted(matches)]


def load_remote_manifests(tags: Sequence[str], date: str) -> tuple[dict[str, str], list[dict[str, Any]]]:
    runs: dict[str, str] = {}
    manifests: list[dict[str, Any]] = []
    for tag in tags:
        with tempfile.TemporaryDirectory(prefix="ledger-manifest-") as tmp:
            proc = run_command(
                ["gh", "release", "download", tag, "--pattern", f"manifest-{date}*.json", "--dir", tmp],
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
                    if isinstance(run, dict) and run.get("run_id") and run.get("digest"):
                        runs[str(run["run_id"])] = str(run["digest"])
    return runs, manifests


def build_manifest(date: str, tag: str, plans: Sequence[RunPlan], repo: str, existing_tags: Sequence[str]) -> dict[str, Any]:
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
    manifest["content_digest"] = json_digest({"date": date, "runs": [{"run_id": p.run_id, "digest": p.digest} for p in plans]})
    return manifest


def release_notes(manifest: dict[str, Any]) -> str:
    runs = manifest["runs"]
    image_count = sum(int(run["stats"].get("image_completed", 0)) for run in runs)
    video_count = sum(int(run["stats"].get("video_completed", 0)) for run in runs)
    error_count = sum(int(run["stats"].get("errors", 0)) for run in runs)
    media_bytes = sum(
        int(asset["size_bytes"])
        for run in runs
        for asset in run["assets"]
        if asset["kind"] in {"images", "videos"}
    )
    models = sorted({model for run in runs for model in run["stats"].get("models", [])})
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
            "Media is grouped by run and media type. JSONL metadata and the release manifest are separate assets so analytics can run without downloading media archives.",
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
    return f"media-exp-{date}-s{number:02d}", f"Media Experiment — {date} · Supplement {number:02d}"


def publish_date(date_dir: Path, staging_root: Path, max_part_bytes: int, all_tags: list[str], dry_run: bool) -> str:
    date = date_dir.name
    existing_tags = date_release_tags(all_tags, date)
    remote_runs, _ = load_remote_manifests(existing_tags, date)
    run_dirs = sorted((p for p in date_dir.iterdir() if p.is_dir() and p.name.startswith("run_")), key=lambda p: p.name)
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
            conflicts.append(f"{inspected.run_id}: local {inspected.digest[:12]} != remote {remote_digest[:12]}")

    if conflicts:
        raise ValueError(f"{date}: existing run IDs have different content:\n- " + "\n- ".join(conflicts))
    if not unpublished:
        shutil.rmtree(date_staging, ignore_errors=True)
        return f"SKIP {date}: all {len(run_dirs)} run(s) already published"

    planned = [package_run(plan, date_staging, max_part_bytes) for plan in unpublished]
    tag, title = next_tag(date, existing_tags)
    repo = gh_repo()
    manifest = build_manifest(date, tag, planned, repo, existing_tags)
    manifest_path = date_staging / f"manifest-{date}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notes_path = date_staging / f"release-notes-{date}.md"
    notes_path.write_text(release_notes(manifest), encoding="utf-8")

    all_assets = [asset.path for plan in planned for asset in plan.assets] + [manifest_path]
    if dry_run:
        return f"DRY-RUN {date}: would create {tag} with {len(planned)} run(s), {len(all_assets)} asset(s)"

    cmd = ["gh", "release", "create", tag, *[str(path) for path in all_assets], "--title", title, "--notes-file", str(notes_path)]
    run_command(cmd, capture=False)
    all_tags.append(tag)
    shutil.rmtree(date_staging, ignore_errors=True)
    return f"PUBLISHED {date}: {tag} ({len(planned)} new run(s), {len(all_assets)} asset(s))"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package result directories and publish date-scoped GitHub Releases.")
    parser.add_argument("--source", type=Path, default=Path("results"), help="Root results directory")
    parser.add_argument("--date", action="append", dest="dates", help="Only publish this YYYY-MM-DD date (repeatable)")
    parser.add_argument("--staging", type=Path, default=Path(".release-staging"), help="Temporary packaging directory")
    parser.add_argument("--max-part-gib", type=float, default=1.8, help="Maximum uncompressed media bytes per ZIP part")
    parser.add_argument("--dry-run", action="store_true", help="Build and validate packages without creating Releases")
    parser.add_argument("--keep-staging", action="store_true", help="Keep temporary packages after successful publication")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_part_bytes = int(args.max_part_gib * 1024**3)
    requested = set(args.dates or []) or None

    try:
        run_command(["gh", "--version"])
        run_command(["gh", "auth", "status"])
        run_command(["gh", "repo", "view"])
        dates = discover_dates(args.source, requested)
        if not dates:
            print(f"No YYYY-MM-DD directories found under {args.source}")
            return 0
        args.staging.mkdir(parents=True, exist_ok=True)
        tags = list_release_tags()
        results: list[str] = []
        failures: list[str] = []
        for date_dir in dates:
            try:
                message = publish_date(date_dir, args.staging, max_part_bytes, tags, args.dry_run)
                results.append(message)
                print(message, flush=True)
            except Exception as exc:
                message = f"FAILED {date_dir.name}: {exc}"
                failures.append(message)
                print(message, file=sys.stderr, flush=True)
        if not args.keep_staging and not args.dry_run and not failures:
            shutil.rmtree(args.staging, ignore_errors=True)
        print("\nSummary")
        for line in results + failures:
            print(f"- {line}")
        return 1 if failures else 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
