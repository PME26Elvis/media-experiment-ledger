#!/usr/bin/env python3
"""Remove repository-backed binary preview mirrors from a built Pages artifact.

Visual Lab, Detector Lab, and legacy YOLO preview URLs deliberately point at
versioned files on raw.githubusercontent.com.  Astro copies the same tracked
files from web/public into site/ even though Pages never serves those copies.
Keeping both transports duplicates hundreds of MiB and eventually exceeds the
supported GitHub Pages artifact budget.

This script only mutates the ephemeral built site directory.  It never removes
tracked repository evidence or changes the versioned raw-GitHub preview URLs.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPOSITORY_PREVIEW_MIRRORS = (
    Path("data/visual-analysis/previews"),
    Path("data/detection/previews"),
    Path("data/yolo/previews"),
)


def directory_stats(path: Path) -> tuple[int, int]:
    files = [item for item in path.rglob("*") if item.is_file()]
    return len(files), sum(item.stat().st_size for item in files)


def prepare(root: Path) -> tuple[int, int]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Missing built site directory: {root}")

    removed_files = 0
    removed_bytes = 0
    for relative in REPOSITORY_PREVIEW_MIRRORS:
        target = root / relative
        if not target.exists():
            continue
        if not target.is_dir():
            raise ValueError(f"Expected preview mirror directory: {target}")
        file_count, byte_count = directory_stats(target)
        shutil.rmtree(target)
        removed_files += file_count
        removed_bytes += byte_count
        print(
            f"Excluded Pages-only duplicate mirror {relative.as_posix()}: "
            f"{file_count:,} files / {byte_count:,} bytes"
        )

    print(
        f"Prepared Pages artifact: excluded {removed_files:,} repository-backed "
        f"preview files / {removed_bytes:,} bytes; tracked evidence is unchanged"
    )
    return removed_files, removed_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    args = parser.parse_args()
    prepare(args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
