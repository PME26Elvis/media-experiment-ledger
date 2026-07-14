#!/usr/bin/env python3
"""Store, restore, and promote a large input archive through GitHub Releases.

A snapshot is intentionally separate from the date-scoped experiment Releases.
The source archive is split into assets below GitHub's per-asset limit, and a
manifest records byte sizes and SHA-256 digests. A later Codespaces command or
workflow can reconstruct the exact archive and promote it through
publish_from_archive.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Sequence
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")
DEFAULT_PART_BYTES = int(1.8 * 1024**3)
MANIFEST_NAME = "input-snapshot-manifest.json"


@dataclass(frozen=True)
class PartRecord:
    name: str
    size_bytes: int
    sha256: str
    index: int


class SnapshotError(RuntimeError):
    pass


def run_command(cmd: Sequence[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(cmd),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and proc.returncode != 0:
        detail = ((proc.stderr or "") or (proc.stdout or "")).strip()
        raise SnapshotError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{detail}")
    return proc


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def copy_exact(source: BinaryIO, destination: BinaryIO, limit: int, whole_digest: Any) -> tuple[int, str]:
    part_digest = hashlib.sha256()
    written = 0
    while written < limit:
        chunk = source.read(min(4 * 1024 * 1024, limit - written))
        if not chunk:
            break
        destination.write(chunk)
        whole_digest.update(chunk)
        part_digest.update(chunk)
        written += len(chunk)
    return written, part_digest.hexdigest()


def split_archive(source: Path, destination: Path, max_part_bytes: int) -> tuple[list[PartRecord], str, int]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input archive does not exist: {source}")
    if max_part_bytes <= 0:
        raise ValueError("Part size must be positive")
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    if before[0] == 0:
        raise SnapshotError(f"Input archive is empty: {source}")

    destination.mkdir(parents=True, exist_ok=True)
    records: list[PartRecord] = []
    whole_digest = hashlib.sha256()
    total = 0
    with source.open("rb") as input_file:
        index = 1
        while True:
            name = f"{source.name}.part{index:03d}"
            path = destination / name
            with path.open("wb") as output_file:
                written, digest = copy_exact(input_file, output_file, max_part_bytes, whole_digest)
            if written == 0:
                path.unlink(missing_ok=True)
                break
            records.append(PartRecord(name=name, size_bytes=written, sha256=digest, index=index))
            total += written
            index += 1

    after = (source.stat().st_size, source.stat().st_mtime_ns)
    if before != after:
        raise SnapshotError(
            f"{source.name} changed while it was being split. Wait for the browser upload to finish and retry."
        )
    if total != before[0]:
        raise SnapshotError(f"Split byte count mismatch: expected {before[0]}, wrote {total}")
    return records, whole_digest.hexdigest(), total


def make_manifest(source: Path, records: Sequence[PartRecord], source_sha256: str, source_size: int, tag: str) -> dict[str, Any]:
    now_taipei = datetime.now(TAIPEI).replace(microsecond=0)
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "schema_version": 1,
        "release_kind": "input_snapshot",
        "tag": tag,
        "source_filename": source.name,
        "source_size_bytes": source_size,
        "source_sha256": source_sha256,
        "created_at_taipei": now_taipei.isoformat(),
        "created_at_utc": now_utc.isoformat(),
        "timezone": "Asia/Taipei",
        "parts": [record.__dict__ for record in records],
    }


def snapshot_tag(source_sha256: str, now: datetime | None = None) -> str:
    current = now or datetime.now(TAIPEI)
    return f"media-input-{current:%Y-%m-%d}-{source_sha256[:12]}"


def release_exists(tag: str) -> bool:
    proc = run_command(["gh", "release", "view", tag], check=False)
    return proc.returncode == 0


def ensure_gh() -> None:
    run_command(["gh", "--version"])
    run_command(["gh", "auth", "status"])
    run_command(["gh", "repo", "view"])


def publish_snapshot(source: Path, staging_root: Path, max_part_bytes: int, dry_run: bool, keep_staging: bool) -> str:
    source = source.expanduser().resolve()
    # Opening the central directory gives a clear error for an incomplete ZIP
    # without reading the full archive twice. The promotion step will validate
    # every extracted member and CRC.
    if source.suffix.lower() == ".zip":
        import zipfile

        try:
            with zipfile.ZipFile(source, "r", allowZip64=True) as archive:
                if not archive.infolist():
                    raise SnapshotError(f"ZIP contains no entries: {source}")
        except zipfile.BadZipFile as exc:
            raise SnapshotError(
                f"Cannot open {source.name} as a complete ZIP. The browser upload may still be running: {exc}"
            ) from exc

    staging_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="snapshot-", dir=staging_root))
    try:
        parts, source_digest, source_size = split_archive(source, work, max_part_bytes)
        tag = snapshot_tag(source_digest)
        manifest = make_manifest(source, parts, source_digest, source_size, tag)
        manifest_path = work / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        notes_path = work / "input-snapshot-notes.md"
        notes_path.write_text(
            "\n".join(
                [
                    "A byte-preserving input snapshot for later promotion into date-scoped experiment releases.",
                    "",
                    f"Source: `{source.name}`",
                    f"Size: **{source_size / 1024**3:.2f} GiB**",
                    f"Parts: **{len(parts)}**",
                    f"SHA-256: `{source_digest}`",
                    "",
                    "Use the **Promote input snapshot** workflow or `tools/input_snapshot.py promote` to reconstruct and process it.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        title_time = datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M")
        title = f"Input Snapshot — {title_time} (Taipei)"
        assets = [work / part.name for part in parts] + [manifest_path]
        if dry_run:
            return f"DRY-RUN: would create {tag} with {len(parts)} part(s), source SHA-256 {source_digest}"
        ensure_gh()
        if release_exists(tag):
            return f"SKIP: {tag} already exists for source SHA-256 {source_digest}"
        run_command(
            [
                "gh",
                "release",
                "create",
                tag,
                *[str(path) for path in assets],
                "--title",
                title,
                "--notes-file",
                str(notes_path),
            ],
            capture=False,
        )
        return f"PUBLISHED: {tag} ({len(parts)} part(s), {source_size / 1024**3:.2f} GiB)"
    finally:
        if not keep_staging:
            shutil.rmtree(work, ignore_errors=True)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Cannot read snapshot manifest {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("release_kind") != "input_snapshot":
        raise SnapshotError(f"Not an input snapshot manifest: {path}")
    if not isinstance(value.get("parts"), list) or not value["parts"]:
        raise SnapshotError(f"Snapshot manifest contains no parts: {path}")
    return value


def download_snapshot(tag: str, directory: Path) -> dict[str, Any]:
    ensure_gh()
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / MANIFEST_NAME
    run_command(["gh", "release", "download", tag, "--pattern", MANIFEST_NAME, "--dir", str(directory)])
    manifest = load_manifest(manifest_path)
    for part in manifest["parts"]:
        name = str(part["name"])
        run_command(["gh", "release", "download", tag, "--pattern", name, "--dir", str(directory)])
    return manifest


def restore_from_directory(manifest: dict[str, Any], directory: Path, output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".partial")
    partial.unlink(missing_ok=True)
    whole_digest = hashlib.sha256()
    total = 0
    try:
        with partial.open("wb") as restored:
            for expected_index, part in enumerate(manifest["parts"], 1):
                if int(part.get("index", expected_index)) != expected_index:
                    raise SnapshotError("Snapshot part indices are not contiguous")
                path = directory / str(part["name"])
                if not path.is_file():
                    raise FileNotFoundError(f"Missing snapshot part: {path}")
                expected_size = int(part["size_bytes"])
                actual_size = path.stat().st_size
                if actual_size != expected_size:
                    raise SnapshotError(f"Part size mismatch for {path.name}: expected {expected_size}, got {actual_size}")
                actual_digest = sha256_file(path)
                if actual_digest != str(part["sha256"]):
                    raise SnapshotError(f"Part SHA-256 mismatch for {path.name}")
                with path.open("rb") as source:
                    while chunk := source.read(4 * 1024 * 1024):
                        restored.write(chunk)
                        whole_digest.update(chunk)
                        total += len(chunk)
        expected_total = int(manifest["source_size_bytes"])
        expected_digest = str(manifest["source_sha256"])
        if total != expected_total:
            raise SnapshotError(f"Restored size mismatch: expected {expected_total}, got {total}")
        if whole_digest.hexdigest() != expected_digest:
            raise SnapshotError("Restored archive SHA-256 does not match the manifest")
        partial.replace(output)
        return output
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def restore_snapshot(tag: str, output: Path, download_root: Path | None, keep_downloads: bool) -> Path:
    if download_root is not None:
        if download_root.exists() and any(download_root.iterdir()):
            raise SnapshotError(f"Download directory must be empty: {download_root}")
        download_root.mkdir(parents=True, exist_ok=True)
        manifest = download_snapshot(tag, download_root)
        restored = restore_from_directory(manifest, download_root, output)
        if not keep_downloads:
            shutil.rmtree(download_root, ignore_errors=True)
        return restored

    with tempfile.TemporaryDirectory(prefix="input-snapshot-") as temporary:
        directory = Path(temporary)
        manifest = download_snapshot(tag, directory)
        return restore_from_directory(manifest, directory, output)


def promote_snapshot(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="promote-snapshot-") as temporary:
        archive = Path(temporary) / "results.zip"
        restore_snapshot(args.tag, archive, None, False)
        command = [sys.executable, str(Path(__file__).with_name("publish_from_archive.py")), str(archive)]
        for date in args.dates or []:
            command.extend(["--date", date])
        command.extend(["--max-part-gib", str(args.max_part_gib)])
        if args.dry_run:
            command.append("--dry-run")
        if args.keep_staging:
            command.append("--keep-staging")
        proc = subprocess.run(command)
        return proc.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish, restore, or promote a split input snapshot Release.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish = subparsers.add_parser("publish", help="Split one archive and publish an input snapshot Release")
    publish.add_argument("archive", type=Path)
    publish.add_argument("--part-gib", type=float, default=1.8)
    publish.add_argument("--staging", type=Path, default=Path(".input-staging"))
    publish.add_argument("--dry-run", action="store_true")
    publish.add_argument("--keep-staging", action="store_true")

    restore = subparsers.add_parser("restore", help="Download and reconstruct one snapshot")
    restore.add_argument("--tag", required=True)
    restore.add_argument("--output", type=Path, default=Path("restored-results.zip"))
    restore.add_argument("--download-root", type=Path)
    restore.add_argument("--keep-downloads", action="store_true")

    promote = subparsers.add_parser("promote", help="Restore a snapshot and publish its date-scoped releases")
    promote.add_argument("--tag", required=True)
    promote.add_argument("--date", action="append", dest="dates")
    promote.add_argument("--max-part-gib", type=float, default=1.8)
    promote.add_argument("--dry-run", action="store_true")
    promote.add_argument("--keep-staging", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "publish":
            result = publish_snapshot(
                args.archive,
                args.staging,
                int(args.part_gib * 1024**3),
                args.dry_run,
                args.keep_staging,
            )
            print(result)
            return 0
        if args.command == "restore":
            output = restore_snapshot(args.tag, args.output, args.download_root, args.keep_downloads)
            print(f"RESTORED: {output}")
            return 0
        if args.command == "promote":
            return promote_snapshot(args)
        raise AssertionError(args.command)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
