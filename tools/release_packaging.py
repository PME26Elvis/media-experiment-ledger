"""Validation and ZIP packaging for date-scoped experiment Releases."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from release_policy import media_counts_from_file_records

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
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


def run_command(
    cmd: Sequence[str], *, check: bool = True, capture: bool = True
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(cmd),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        raise CommandError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{stderr or stdout}"
        )
    return proc


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
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
        if not path.exists() or path.suffix.lower() not in {
            ".json",
            ".jsonl",
            ".md",
            ".txt",
            ".log",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{path}: matched {pattern.pattern}")
                break
    if findings:
        raise ValueError(
            "Potential secret material found in release metadata:\n- "
            + "\n- ".join(findings)
        )


def discover_dates(source: Path, requested: set[str] | None = None) -> list[Path]:
    if not source.is_dir():
        raise FileNotFoundError(f"Results directory does not exist: {source}")
    dates = [p for p in source.iterdir() if p.is_dir() and DATE_RE.match(p.name)]
    if requested:
        missing = sorted(requested - {p.name for p in dates})
        if missing:
            raise FileNotFoundError(
                f"Requested date directories not found: {', '.join(missing)}"
            )
        dates = [p for p in dates if p.name in requested]
    return sorted(dates, key=lambda p: p.name)


def collect_files(root: Path) -> list[Path]:
    return sorted(
        (p for p in root.rglob("*") if p.is_file()),
        key=lambda p: p.as_posix(),
    )


def split_files(files: Sequence[Path], max_bytes: int) -> list[list[Path]]:
    parts: list[list[Path]] = []
    current: list[Path] = []
    current_bytes = 0
    for path in files:
        size = path.stat().st_size
        if size > max_bytes:
            raise ValueError(
                f"Single file exceeds configured part limit ({max_bytes} bytes): "
                f"{path} ({size} bytes)"
            )
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
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(run_dir).as_posix())
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise IOError(f"ZIP verification failed for {zip_path}: {bad}")


def event_stats(
    outputs: Sequence[dict[str, Any]],
    errors: Sequence[dict[str, Any]],
) -> dict[str, Any]:
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
        file_records.append(
            {
                "path": rel,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    run_digest = json_digest(file_records)

    stats = event_stats(outputs, errors)
    stats["file_count"] = len(all_files)
    stats["source_bytes"] = sum(p.stat().st_size for p in all_files)
    archived = media_counts_from_file_records(file_records)
    stats["archived_images"] = archived["images"]
    stats["archived_videos"] = archived["videos"]
    return RunPlan(
        run_id,
        run_dir,
        run_digest,
        tuple(),
        stats,
        tuple(file_records),
    )


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
        assets.append(
            Asset(
                dest,
                name,
                sha256_file(dest),
                dest.stat().st_size,
                "metadata",
                run_id,
            )
        )

    media_groups = {
        "images": (
            collect_files(run_dir / "media" / "images")
            if (run_dir / "media" / "images").is_dir()
            else []
        ),
        "videos": (
            collect_files(run_dir / "media" / "videos")
            if (run_dir / "media" / "videos").is_dir()
            else []
        ),
    }
    for kind, files in media_groups.items():
        parts = split_files(files, max_part_bytes)
        for index, part in enumerate(parts, 1):
            suffix = f"-part{index:02d}" if len(parts) > 1 else ""
            name = f"{run_id}-{kind}{suffix}.zip"
            dest = staging_dir / name
            create_stored_zip(dest, run_dir, [*metadata_sources, *part])
            assets.append(
                Asset(
                    dest,
                    name,
                    sha256_file(dest),
                    dest.stat().st_size,
                    kind,
                    run_id,
                )
            )
    return RunPlan(
        plan.run_id,
        plan.source_dir,
        plan.digest,
        tuple(assets),
        plan.stats,
        plan.files,
    )


def plan_run(run_dir: Path, staging_dir: Path, max_part_bytes: int) -> RunPlan:
    """Compatibility helper used by tests and ad-hoc packaging."""
    return package_run(inspect_run(run_dir), staging_dir, max_part_bytes)
