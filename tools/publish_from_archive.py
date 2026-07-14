#!/usr/bin/env python3
"""Extract a ZIP upload safely and pass its results tree to publish_results.py.

The browser only needs to upload one archive. The archive may contain either:

- results/YYYY-MM-DD/run_*/...
- YYYY-MM-DD/run_*/...
- one wrapper directory containing either layout

The original archive is never deleted. Extraction is temporary unless
``--keep-extracted`` is selected.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_EXTRACTION_ROOT = Path(".archive-imports")
MIN_FREE_MARGIN_BYTES = 512 * 1024**2


@dataclass(frozen=True)
class ArchiveInspection:
    archive_size_bytes: int
    uncompressed_size_bytes: int
    largest_date_bytes: int
    file_count: int


class ArchiveInputError(RuntimeError):
    pass


def run_command(cmd: Sequence[str]) -> int:
    proc = subprocess.run(list(cmd))
    return proc.returncode


def stable_signature(path: Path) -> tuple[int, int]:
    info = path.stat()
    return info.st_size, info.st_mtime_ns


def normalized_member_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or normalized.startswith("/"):
        raise ArchiveInputError(f"Unsafe absolute or empty ZIP member: {name!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ArchiveInputError(f"Unsafe ZIP member path: {name!r}")
    if path.parts and re.match(r"^[A-Za-z]:$", path.parts[0]):
        raise ArchiveInputError(f"Unsafe drive-qualified ZIP member: {name!r}")
    return path


def is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def date_component(parts: Sequence[str]) -> str | None:
    for part in parts:
        if DATE_RE.match(part):
            return part
    return None


def inspect_archive(archive_path: Path) -> ArchiveInspection:
    archive_path = archive_path.expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")
    if archive_path.stat().st_size == 0:
        raise ArchiveInputError(f"Archive is empty: {archive_path}")

    before = stable_signature(archive_path)
    total = 0
    count = 0
    date_sizes: dict[str, int] = {}
    try:
        with zipfile.ZipFile(archive_path, "r", allowZip64=True) as archive:
            infos = archive.infolist()
            if not infos:
                raise ArchiveInputError(f"ZIP contains no entries: {archive_path}")
            for info in infos:
                member = normalized_member_path(info.filename)
                if is_symlink(info):
                    raise ArchiveInputError(f"Symbolic links are not accepted in input ZIPs: {info.filename}")
                if info.is_dir():
                    continue
                count += 1
                total += int(info.file_size)
                date = date_component(member.parts)
                if date:
                    date_sizes[date] = date_sizes.get(date, 0) + int(info.file_size)
    except zipfile.BadZipFile as exc:
        raise ArchiveInputError(
            f"Cannot open {archive_path.name} as a complete ZIP. The upload may still be running or the file is incomplete: {exc}"
        ) from exc

    after = stable_signature(archive_path)
    if before != after:
        raise ArchiveInputError(
            f"{archive_path.name} changed while it was being inspected. Wait for the upload to finish, then run the command again."
        )
    if count == 0:
        raise ArchiveInputError(f"ZIP contains no files: {archive_path}")
    return ArchiveInspection(
        archive_size_bytes=before[0],
        uncompressed_size_bytes=total,
        largest_date_bytes=max(date_sizes.values(), default=min(total, 2 * 1024**3)),
        file_count=count,
    )


def check_disk_space(root: Path, inspection: ArchiveInspection) -> None:
    root.mkdir(parents=True, exist_ok=True)
    available = shutil.disk_usage(root).free
    # The source archive already occupies disk. We need the extracted tree plus
    # approximately one date's packages at a time and a fixed working margin.
    required = inspection.uncompressed_size_bytes + inspection.largest_date_bytes + MIN_FREE_MARGIN_BYTES
    if available < required:
        raise ArchiveInputError(
            "Insufficient free space for extraction and date packaging: "
            f"need about {required / 1024**3:.2f} GiB, have {available / 1024**3:.2f} GiB."
        )


def safe_extract(archive_path: Path, destination: Path) -> None:
    archive_path = archive_path.expanduser().resolve()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    before = stable_signature(archive_path)
    try:
        with zipfile.ZipFile(archive_path, "r", allowZip64=True) as archive:
            for info in archive.infolist():
                member = normalized_member_path(info.filename)
                if is_symlink(info):
                    raise ArchiveInputError(f"Symbolic links are not accepted in input ZIPs: {info.filename}")
                target = destination.joinpath(*member.parts)
                target_resolved = target.resolve()
                if os.path.commonpath([destination, target_resolved]) != str(destination):
                    raise ArchiveInputError(f"ZIP member escapes extraction root: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=4 * 1024 * 1024)
    except zipfile.BadZipFile as exc:
        raise ArchiveInputError(f"ZIP extraction failed: {exc}") from exc
    after = stable_signature(archive_path)
    if before != after:
        raise ArchiveInputError(
            f"{archive_path.name} changed during extraction. Wait for the upload to finish and retry."
        )


def has_date_directories(path: Path) -> bool:
    return path.is_dir() and any(child.is_dir() and DATE_RE.match(child.name) for child in path.iterdir())


def find_results_root(extraction_root: Path) -> Path:
    candidates: list[Path] = []
    if has_date_directories(extraction_root):
        candidates.append(extraction_root)
    direct_results = extraction_root / "results"
    if has_date_directories(direct_results):
        candidates.append(direct_results)

    # Accept a single wrapper directory, and tolerate one additional wrapper
    # generated by desktop ZIP tools.
    for child in extraction_root.iterdir():
        if not child.is_dir() or child.name == "__MACOSX":
            continue
        if has_date_directories(child):
            candidates.append(child)
        nested_results = child / "results"
        if has_date_directories(nested_results):
            candidates.append(nested_results)
        for grandchild in child.iterdir():
            if not grandchild.is_dir() or grandchild.name == "__MACOSX":
                continue
            if grandchild.name == "results" and has_date_directories(grandchild):
                candidates.append(grandchild)

    unique = sorted({candidate.resolve() for candidate in candidates}, key=lambda p: (len(p.parts), str(p)))
    if not unique:
        raise ArchiveInputError(
            "No results tree was found after extraction. Expected results/YYYY-MM-DD/run_* or YYYY-MM-DD/run_*."
        )
    shortest_depth = len(unique[0].parts)
    shortest = [candidate for candidate in unique if len(candidate.parts) == shortest_depth]
    if len(shortest) > 1:
        rendered = "\n- ".join(str(path) for path in shortest)
        raise ArchiveInputError(f"Multiple possible results roots were found:\n- {rendered}")
    return shortest[0]


def publisher_command(args: argparse.Namespace, source: Path) -> list[str]:
    publisher = Path(__file__).with_name("publish_results.py")
    command = [
        sys.executable,
        str(publisher),
        "--source",
        str(source),
        "--staging",
        str(args.staging),
        "--max-part-gib",
        str(args.max_part_gib),
    ]
    for date in args.dates or []:
        command.extend(["--date", date])
    if args.dry_run:
        command.append("--dry-run")
    if args.keep_staging:
        command.append("--keep-staging")
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a results ZIP through the existing date-scoped release publisher.")
    parser.add_argument("archive", type=Path, help="ZIP containing results/ or date directories")
    parser.add_argument("--date", action="append", dest="dates", help="Only publish this YYYY-MM-DD date (repeatable)")
    parser.add_argument("--staging", type=Path, default=Path(".release-staging"), help="Publisher packaging directory")
    parser.add_argument("--extract-root", type=Path, default=DEFAULT_EXTRACTION_ROOT, help="Temporary extraction parent")
    parser.add_argument("--max-part-gib", type=float, default=1.8, help="Maximum media bytes per release ZIP part")
    parser.add_argument("--dry-run", action="store_true", help="Validate and package without creating Releases")
    parser.add_argument("--keep-staging", action="store_true", help="Keep publisher package files")
    parser.add_argument("--keep-extracted", action="store_true", help="Keep the extracted results tree")
    parser.add_argument("--skip-disk-check", action="store_true", help="Skip the conservative free-space check")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        archive = args.archive.expanduser().resolve()
        inspection = inspect_archive(archive)
        if not args.skip_disk_check:
            check_disk_space(args.extract_root, inspection)
        print(
            f"Archive ready: {archive.name}; {inspection.file_count:,} files; "
            f"{inspection.archive_size_bytes / 1024**3:.2f} GiB compressed; "
            f"{inspection.uncompressed_size_bytes / 1024**3:.2f} GiB extracted",
            flush=True,
        )

        args.extract_root.mkdir(parents=True, exist_ok=True)
        if args.keep_extracted:
            destination = args.extract_root / archive.stem
            if destination.exists():
                raise FileExistsError(
                    f"Extraction destination already exists: {destination}. Remove it or omit --keep-extracted."
                )
            safe_extract(archive, destination)
            results_root = find_results_root(destination)
            print(f"Detected results root: {results_root}", flush=True)
            return run_command(publisher_command(args, results_root))

        with tempfile.TemporaryDirectory(prefix=f"{archive.stem}-", dir=args.extract_root) as temporary:
            destination = Path(temporary)
            safe_extract(archive, destination)
            results_root = find_results_root(destination)
            print(f"Detected results root: {results_root}", flush=True)
            return run_command(publisher_command(args, results_root))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
