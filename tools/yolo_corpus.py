"""Canonical full-corpus discovery and verified image extraction for YOLO."""
from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

from PIL import Image

from release_policy import IMAGE_SUFFIXES, is_quarantined, quarantine_policy_digest

MEDIA_TAG_PREFIX = "media-exp-"


class CommandError(RuntimeError):
    pass


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and result.returncode:
        raise CommandError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        raise ValueError(f"Unsafe ZIP member path: {name}")
    if len(member.parts) < 3 or member.parts[0:2] != ("media", "images"):
        raise ValueError(f"Unexpected image ZIP member path: {name}")
    if member.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError(f"Unexpected image extension in ZIP: {name}")
    return member


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            output.append(value)
    return output


@dataclass
class SourceAlias:
    release_tag: str
    run_id: str
    asset: str
    member: str
    prompt_id: str = ""
    category: str = "uncategorized"
    model: str = "unknown-model"
    prompt: str = ""
    timestamp: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "release_tag": self.release_tag,
            "run_id": self.run_id,
            "asset": self.asset,
            "member": self.member,
            "prompt_id": self.prompt_id,
            "category": self.category,
            "model": self.model,
            "prompt": self.prompt,
            "timestamp": self.timestamp,
        }


@dataclass
class CorpusImage:
    image_sha256: str
    path: Path
    width: int
    height: int
    size_bytes: int
    aliases: list[SourceAlias] = field(default_factory=list)

    @property
    def primary_alias(self) -> SourceAlias:
        return sorted(
            self.aliases,
            key=lambda item: (
                item.release_tag,
                item.run_id,
                item.prompt_id,
                item.member,
            ),
        )[0]

    def as_manifest_row(self) -> dict[str, Any]:
        return {
            "image_sha256": self.image_sha256,
            "width": self.width,
            "height": self.height,
            "size_bytes": self.size_bytes,
            "sources": [
                alias.as_dict()
                for alias in sorted(
                    self.aliases,
                    key=lambda item: (
                        item.release_tag,
                        item.run_id,
                        item.prompt_id,
                        item.member,
                    ),
                )
            ],
        }


@dataclass
class CorpusInventory:
    releases: list[dict[str, Any]]
    images: list[CorpusImage]
    date_from: str
    date_to: str
    latest_date: str
    fingerprint: str
    source_file_count: int
    quarantined_runs: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "scope": "all_published_non_quarantined_media_exp_images",
            "release_count": len(self.releases),
            "release_tags": [row["tagName"] for row in self.releases],
            "date_from": self.date_from,
            "date_to": self.date_to,
            "latest_date": self.latest_date,
            "source_image_files": self.source_file_count,
            "unique_images": len(self.images),
            "quarantined_runs": self.quarantined_runs,
            "quarantine_policy_digest": quarantine_policy_digest(),
            "corpus_fingerprint": self.fingerprint,
            "images": [image.as_manifest_row() for image in self.images],
        }


def release_rows(repo: str) -> list[dict[str, Any]]:
    result = command(
        [
            "gh",
            "release",
            "list",
            "--repo",
            repo,
            "--limit",
            "1000",
            "--json",
            "tagName,publishedAt,name,isDraft,isPrerelease",
        ]
    )
    rows = json.loads(result.stdout or "[]")
    selected = [
        row
        for row in rows
        if str(row.get("tagName") or "").startswith(MEDIA_TAG_PREFIX)
        and not row.get("isDraft")
    ]
    return sorted(
        selected,
        key=lambda row: (
            str(row.get("publishedAt") or ""),
            str(row.get("tagName") or ""),
        ),
    )


def download_release_inputs(repo: str, rows: Sequence[dict[str, Any]], root: Path) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for row in rows:
        tag = str(row["tagName"])
        target = root / tag
        target.mkdir(parents=True, exist_ok=True)
        for pattern in ("manifest-*.json", "run_*-outputs.jsonl", "run_*-images*.zip"):
            command(
                [
                    "gh",
                    "release",
                    "download",
                    tag,
                    "--repo",
                    repo,
                    "--pattern",
                    pattern,
                    "--dir",
                    str(target),
                ],
                check=False,
            )
        roots[tag] = target
    return roots


def _output_records(root: Path, run_id: str) -> list[dict[str, Any]]:
    path = root / f"{run_id}-outputs.jsonl"
    if not path.exists():
        alternatives = sorted(root.glob(f"{run_id}*outputs.jsonl"))
        path = alternatives[0] if alternatives else path
    return [row for row in read_jsonl(path) if row.get("event") == "image_completed"]


def _record_for_member(
    records: Sequence[dict[str, Any]], member: PurePosixPath
) -> dict[str, Any] | None:
    basename = member.name
    exact = []
    for row in records:
        local_path = str(row.get("local_path") or "")
        if local_path and PurePosixPath(local_path.replace("\\", "/")).name == basename:
            exact.append(row)
    if exact:
        return exact[0]
    prompt_matches = [
        row
        for row in records
        if row.get("prompt_id")
        and (
            basename.startswith(str(row["prompt_id"]) + "_")
            or basename.startswith(str(row["prompt_id"]) + "-")
            or str(row["prompt_id"]) in basename
        )
    ]
    return prompt_matches[0] if prompt_matches else None


def _alias(tag: str, run_id: str, asset: str, member: str, record: dict[str, Any] | None) -> SourceAlias:
    payload = record.get("payload") if record and isinstance(record.get("payload"), dict) else {}
    return SourceAlias(
        release_tag=tag,
        run_id=run_id,
        asset=asset,
        member=member,
        prompt_id=str((record or {}).get("prompt_id") or ""),
        category=str((record or {}).get("category") or "uncategorized"),
        model=str(payload.get("model") or "unknown-model"),
        prompt=str(payload.get("prompt") or ""),
        timestamp=str((record or {}).get("timestamp") or ""),
    )


def build_inventory(
    rows: Sequence[dict[str, Any]],
    roots: dict[str, Path],
    extract_root: Path,
) -> CorpusInventory:
    extract_root.mkdir(parents=True, exist_ok=True)
    release_dates: list[str] = []
    source_file_count = 0
    quarantined_runs = 0
    by_digest: dict[str, CorpusImage] = {}
    manifest_digests: list[str] = []

    for row in rows:
        tag = str(row["tagName"])
        root = roots[tag]
        manifests = sorted(root.glob("manifest-*.json"))
        if not manifests:
            raise FileNotFoundError(f"No manifest downloaded for {tag}")
        for manifest_path in manifests:
            manifest = read_json(manifest_path)
            date = str(manifest.get("experiment_date_taipei") or "")
            if date:
                release_dates.append(date)
            digest = str(manifest.get("content_digest") or "")
            if digest:
                manifest_digests.append(f"{tag}:{digest}")
            for run in manifest.get("runs", []):
                if not isinstance(run, dict):
                    continue
                run_id = str(run.get("run_id") or "")
                if is_quarantined(tag, run_id):
                    quarantined_runs += 1
                    continue
                files = [item for item in run.get("files", []) if isinstance(item, dict)]
                expected_files = {
                    str(item.get("path") or ""): item
                    for item in files
                    if PurePosixPath(str(item.get("path") or "")).parts[:2]
                    == ("media", "images")
                    and PurePosixPath(str(item.get("path") or "")).suffix.lower()
                    in IMAGE_SUFFIXES
                }
                assets = [
                    item
                    for item in run.get("assets", [])
                    if isinstance(item, dict) and str(item.get("kind") or "") == "images"
                ]
                records = _output_records(root, run_id)
                found_paths: set[str] = set()
                for asset in assets:
                    name = str(asset.get("name") or "")
                    archive_path = root / name
                    if not archive_path.exists():
                        raise FileNotFoundError(f"Missing image asset {tag}/{name}")
                    expected_size = int(asset.get("size_bytes") or 0)
                    expected_sha = str(asset.get("sha256") or "")
                    if expected_size and archive_path.stat().st_size != expected_size:
                        raise ValueError(f"Asset size mismatch: {tag}/{name}")
                    if expected_sha and sha256_file(archive_path) != expected_sha:
                        raise ValueError(f"Asset SHA-256 mismatch: {tag}/{name}")
                    with zipfile.ZipFile(archive_path) as archive:
                        bad = archive.testzip()
                        if bad:
                            raise ValueError(f"ZIP CRC failure {tag}/{name}: {bad}")
                        for raw_name in archive.namelist():
                            raw_path = PurePosixPath(raw_name)
                            if len(raw_path.parts) < 3 or raw_path.parts[:2] != ("media", "images"):
                                continue
                            member = safe_member(raw_name)
                            expected = expected_files.get(member.as_posix())
                            if expected is None:
                                raise ValueError(
                                    f"ZIP member missing from manifest file records: {tag}/{run_id}/{raw_name}"
                                )
                            data = archive.read(raw_name)
                            if int(expected.get("size_bytes") or len(data)) != len(data):
                                raise ValueError(f"Image member size mismatch: {tag}/{raw_name}")
                            digest = sha256_bytes(data)
                            expected_digest = str(expected.get("sha256") or "")
                            if expected_digest and digest != expected_digest:
                                raise ValueError(f"Image member SHA-256 mismatch: {tag}/{raw_name}")
                            found_paths.add(member.as_posix())
                            source_file_count += 1
                            record = _record_for_member(records, member)
                            alias = _alias(tag, run_id, name, member.as_posix(), record)
                            if digest in by_digest:
                                by_digest[digest].aliases.append(alias)
                                continue
                            destination = extract_root / digest[:2] / digest[2:4] / f"{digest}{member.suffix.lower()}"
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            destination.write_bytes(data)
                            try:
                                with Image.open(destination) as image:
                                    image.load()
                                    width, height = image.size
                            except Exception:
                                destination.unlink(missing_ok=True)
                                raise ValueError(f"Pillow decode failed: {tag}/{raw_name}")
                            by_digest[digest] = CorpusImage(
                                image_sha256=digest,
                                path=destination,
                                width=width,
                                height=height,
                                size_bytes=len(data),
                                aliases=[alias],
                            )
                missing = sorted(set(expected_files).difference(found_paths))
                if missing:
                    raise ValueError(
                        f"Manifest image records missing from ZIP assets for {tag}/{run_id}: "
                        + ", ".join(missing[:10])
                    )

    images = sorted(by_digest.values(), key=lambda item: item.image_sha256)
    if not images:
        raise ValueError("No canonical images were discovered")
    payload = {
        "schema_version": 1,
        "releases": [
            {
                "tag": str(row.get("tagName") or ""),
                "published_at": str(row.get("publishedAt") or ""),
            }
            for row in rows
        ],
        "manifest_digests": sorted(manifest_digests),
        "quarantine_policy_digest": quarantine_policy_digest(),
        "images": [
            {
                "sha256": image.image_sha256,
                "aliases": [alias.as_dict() for alias in image.aliases],
            }
            for image in images
        ],
    }
    fingerprint = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    dates = sorted(set(release_dates))
    return CorpusInventory(
        releases=list(rows),
        images=images,
        date_from=dates[0] if dates else "",
        date_to=dates[-1] if dates else "",
        latest_date=dates[-1] if dates else "unknown-date",
        fingerprint=fingerprint,
        source_file_count=source_file_count,
        quarantined_runs=quarantined_runs,
    )
