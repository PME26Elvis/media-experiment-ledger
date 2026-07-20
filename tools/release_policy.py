"""Shared release-integrity and historical quarantine policy.

The immutable Release assets remain untouched.  This module defines which runs
belong to the canonical corpus and validates new runs before publication so an
accidental fixture or empty directory cannot pollute analytics again.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUARANTINE_PATH = ROOT / "config" / "release-quarantine.json"
PRODUCTION_RUN_RE = re.compile(
    r"^run_\d{8}_\d{6}(?:_[A-Za-z0-9][A-Za-z0-9._-]*)?$"
)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def load_quarantine(path: Path | str | None = None) -> dict[str, Any]:
    source = Path(path) if path is not None else DEFAULT_QUARANTINE_PATH
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema_version": 1, "excluded_runs": []}
    if not isinstance(value, dict):
        raise ValueError(f"Quarantine policy must be a JSON object: {source}")
    excluded = value.get("excluded_runs")
    if not isinstance(excluded, list):
        raise ValueError(f"excluded_runs must be a list: {source}")
    return value


def quarantine_map(path: Path | str | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for item in load_quarantine(path).get("excluded_runs", []):
        if not isinstance(item, dict):
            continue
        tag = str(item.get("tag") or "")
        run_id = str(item.get("run_id") or "")
        if not tag or not run_id:
            raise ValueError("Every quarantine entry requires tag and run_id")
        key = (tag, run_id)
        if key in output:
            raise ValueError(f"Duplicate quarantine entry: {tag}/{run_id}")
        output[key] = item
    return output


def quarantine_entry(
    tag: str,
    run_id: str,
    path: Path | str | None = None,
) -> dict[str, Any] | None:
    return quarantine_map(path).get((tag, run_id))


def is_quarantined(
    tag: str,
    run_id: str,
    path: Path | str | None = None,
) -> bool:
    return quarantine_entry(tag, run_id, path) is not None


def filter_manifest_runs(
    tag: str,
    runs: Iterable[dict[str, Any]],
    path: Path | str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    policy = quarantine_map(path)
    for run in runs:
        run_id = str(run.get("run_id") or "")
        entry = policy.get((tag, run_id))
        if entry is None:
            included.append(run)
        else:
            excluded.append({"run": run, "policy": entry})
    return included, excluded


def metadata_run_id(path: Path) -> str | None:
    name = path.name
    for suffix in ("-outputs.jsonl", "-errors.jsonl"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return None


def metadata_is_quarantined(
    path: Path,
    quarantine_path: Path | str | None = None,
) -> bool:
    run_id = metadata_run_id(path)
    if not run_id:
        return False
    tag = path.parent.name
    return is_quarantined(tag, run_id, quarantine_path)


def media_counts_from_file_records(
    files: Sequence[dict[str, Any]],
) -> dict[str, int]:
    images = 0
    videos = 0
    for item in files:
        path = PurePosixPath(str(item.get("path") or ""))
        if len(path.parts) < 3 or path.parts[0] != "media":
            continue
        if path.parts[1] == "images" and path.suffix.lower() in IMAGE_SUFFIXES:
            images += 1
        elif path.parts[1] == "videos" and path.suffix.lower() in VIDEO_SUFFIXES:
            videos += 1
    return {"images": images, "videos": videos}


def validate_publishable_run(plan: Any) -> None:
    """Reject empty, synthetic-looking, or internally inconsistent runs."""
    run_id = str(getattr(plan, "run_id", "") or "")
    if not PRODUCTION_RUN_RE.fullmatch(run_id):
        raise ValueError(
            f"{run_id or '<missing>'}: run ID must match {PRODUCTION_RUN_RE.pattern}; "
            "test fixtures must never be published as experiment runs"
        )

    files = list(getattr(plan, "files", ()) or ())
    stats = dict(getattr(plan, "stats", {}) or {})
    if not files or int(stats.get("file_count") or 0) <= 0:
        raise ValueError(f"{run_id}: empty runs are not publishable")

    archived = media_counts_from_file_records(files)
    image_events = int(stats.get("image_completed") or 0)
    video_events = int(stats.get("video_completed") or 0)
    mismatches: list[str] = []
    if image_events != archived["images"]:
        mismatches.append(
            f"image_completed={image_events} but archived image files={archived['images']}"
        )
    if video_events != archived["videos"]:
        mismatches.append(
            f"video_completed={video_events} but archived video files={archived['videos']}"
        )
    if mismatches:
        raise ValueError(f"{run_id}: completion/media integrity mismatch: " + "; ".join(mismatches))


def quarantine_policy_digest(path: Path | str | None = None) -> str:
    value = load_quarantine(path)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
