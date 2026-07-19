"""Corpus discovery and media extraction for Prompt Repeatability Atlas."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from PIL import Image

from prompt_atlas_core import (
    MEDIA_TAG_RE,
    Sample,
    canonical,
    cohort_identity,
    member_matches,
    normalized_settings,
)

ATLAS_DATASET_SCHEMA_VERSION = 2


class CommandError(RuntimeError):
    pass


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise CommandError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{(result.stderr or result.stdout).strip()}"
        )
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
    result = command(
        [
            "gh",
            "release",
            "list",
            "--limit",
            "1000",
            "--json",
            "tagName,publishedAt,name,isDraft,isPrerelease",
        ]
    )
    rows = json.loads(result.stdout or "[]")
    rows = [
        row
        for row in rows
        if MEDIA_TAG_RE.match(str(row.get("tagName") or "")) and not row.get("isDraft")
    ]
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("publishedAt") or ""),
            str(row.get("tagName") or ""),
        ),
    )


def resolve_source_tag(rows: Sequence[dict[str, Any]], requested: str) -> str:
    """Backward-compatible resolver retained for local ad-hoc use."""
    tags = [str(row["tagName"]) for row in rows]
    if not tags:
        raise ValueError("No published media-exp-* releases found")
    if requested in {"", "latest", "all"}:
        return tags[-1]
    if requested not in tags:
        raise ValueError(f"Unknown source tag {requested}; latest is {tags[-1]}")
    return requested


def dataset_fingerprint(rows: Sequence[dict[str, Any]], config: dict[str, Any]) -> str:
    """Fingerprint the immutable corpus and the atlas policy without using cache/state."""
    payload = {
        "atlas_dataset_schema_version": ATLAS_DATASET_SCHEMA_VERSION,
        "release_tags": [
            {
                "tag": str(row.get("tagName") or ""),
                "published_at": str(row.get("publishedAt") or ""),
            }
            for row in rows
        ],
        "policy": config,
    }
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def download_metadata(
    rows: Sequence[dict[str, Any]],
    root: Path,
) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for row in rows:
        tag = str(row["tagName"])
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        command(
            [
                "gh",
                "release",
                "download",
                tag,
                "--pattern",
                "run_*-outputs.jsonl",
                "--dir",
                str(target),
            ],
            check=False,
        )
        roots[tag] = target
    return roots


def collect_samples(
    rows: Sequence[dict[str, Any]],
    roots: dict[str, Path],
) -> list[Sample]:
    published = {
        str(row["tagName"]): str(row.get("publishedAt") or "")
        for row in rows
    }
    output: list[Sample] = []
    for tag, root in roots.items():
        for path in sorted(root.glob("run_*-outputs.jsonl")):
            run_id = path.name.removesuffix("-outputs.jsonl")
            for record in read_jsonl(path):
                if record.get("event") != "image_completed" or not record.get("prompt_id"):
                    continue
                payload = (
                    record.get("payload")
                    if isinstance(record.get("payload"), dict)
                    else {}
                )
                prompt_id = str(record["prompt_id"])
                model = str(payload.get("model") or "unknown-model")
                settings = normalized_settings(payload)
                output.append(
                    Sample(
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
                        local_path=(
                            str(record.get("local_path"))
                            if record.get("local_path")
                            else None
                        ),
                        seed=record.get("seed") or payload.get("seed"),
                    )
                )
    return sorted(output, key=lambda item: item.sort_key)


def group_candidates(
    samples: Sequence[Sample],
    source_tag: str | None = None,
) -> dict[str, list[Sample]]:
    """Group every cohort globally, or only cohorts present in one legacy source tag."""
    allowed: set[str] | None = None
    if source_tag and source_tag not in {"all", "latest"}:
        allowed = {
            sample.cohort_id
            for sample in samples
            if sample.source_tag == source_tag
        }
    groups: dict[str, list[Sample]] = {}
    for sample in samples:
        if allowed is None or sample.cohort_id in allowed:
            groups.setdefault(sample.cohort_id, []).append(sample)
    return {
        key: sorted(value, key=lambda item: item.sort_key)
        for key, value in groups.items()
        if len(value) >= 2
    }


def download_archives(
    groups: dict[str, list[Sample]],
    root: Path,
) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for tag in sorted(
        {
            sample.source_tag
            for group in groups.values()
            for sample in group
        }
    ):
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        command(
            [
                "gh",
                "release",
                "download",
                tag,
                "--pattern",
                "run_*-images*.zip",
                "--dir",
                str(target),
            ],
            check=False,
        )
        roots[tag] = target
    return roots


def extract_images(
    groups: dict[str, list[Sample]],
    archive_roots: dict[str, Path],
    extract_root: Path,
) -> None:
    needed: dict[tuple[str, str], set[str]] = {}
    index: dict[tuple[str, str, str], list[Sample]] = {}
    for group in groups.values():
        for sample in group:
            needed.setdefault(
                (sample.source_tag, sample.run_id),
                set(),
            ).add(sample.prompt_id)
            index.setdefault(
                (sample.source_tag, sample.run_id, sample.prompt_id),
                [],
            ).append(sample)

    for tag, root in archive_roots.items():
        for archive_path in sorted(root.glob("run_*-images*.zip")):
            run_id = (
                archive_path.name.split("-images", 1)[0]
                if "-images" in archive_path.name
                else None
            )
            if not run_id or (tag, run_id) not in needed:
                continue
            try:
                archive = zipfile.ZipFile(archive_path)
            except zipfile.BadZipFile:
                continue
            with archive:
                for member in archive.namelist():
                    prompt_id = next(
                        (
                            pid
                            for pid in needed[(tag, run_id)]
                            if member_matches(member, pid)
                        ),
                        None,
                    )
                    if not prompt_id:
                        continue
                    destination = (
                        extract_root
                        / tag
                        / run_id
                        / PurePosixPath(member).name
                    )
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
