#!/usr/bin/env python3
"""Publish all new date-scoped Releases, then dispatch one full-corpus Atlas."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from release_packaging import plan_run, run_command, split_files
from release_publishing import (
    PUBLISHED_TAG_RE, atlas_batch_id as _atlas_batch_id,
    atlas_dispatch_command as _atlas_dispatch_command, date_release_tags,
    gh_repo, list_release_tags, publish_date,
)

atlas_batch_id = _atlas_batch_id


def atlas_dispatch_command(repo: str, published_tags: list[str], *, batch_id: str | None = None) -> list[str]:
    return _atlas_dispatch_command(
        repo, published_tags, batch_id=batch_id or atlas_batch_id(published_tags)
    )


def dispatch_full_atlas(repo: str, published_tags: list[str]) -> str:
    if not published_tags:
        raise ValueError("Cannot dispatch an Atlas without newly published Releases")
    batch_id = atlas_batch_id(published_tags)
    run_command(atlas_dispatch_command(repo, published_tags, batch_id=batch_id))
    return batch_id


def discover_dates(source: Path, requested: set[str] | None = None) -> list[Path]:
    from release_packaging import discover_dates as implementation
    return implementation(source, requested)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package result directories and publish date-scoped GitHub Releases."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("results"),
        help="Root results directory",
    )
    parser.add_argument(
        "--date",
        action="append",
        dest="dates",
        help="Only publish this YYYY-MM-DD date (repeatable)",
    )
    parser.add_argument(
        "--staging",
        type=Path,
        default=Path(".release-staging"),
        help="Temporary packaging directory",
    )
    parser.add_argument(
        "--max-part-gib",
        type=float,
        default=1.8,
        help="Maximum uncompressed media bytes per ZIP part",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate packages without creating Releases",
    )
    parser.add_argument(
        "--keep-staging",
        action="store_true",
        help="Keep temporary packages after successful publication",
    )
    parser.add_argument(
        "--skip-atlas-dispatch",
        action="store_true",
        help="Do not dispatch the one full-corpus Atlas rebuild after this batch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_part_bytes = int(args.max_part_gib * 1024**3)
    requested = set(args.dates or []) or None

    try:
        run_command(["gh", "--version"])
        run_command(["gh", "auth", "status"])
        run_command(["gh", "repo", "view"])
        repo = gh_repo()
        dates = discover_dates(args.source, requested)
        if not dates:
            print(f"No YYYY-MM-DD directories found under {args.source}")
            return 0
        args.staging.mkdir(parents=True, exist_ok=True)
        tags = list_release_tags()
        results: list[str] = []
        failures: list[str] = []
        published_tags: list[str] = []
        for date_dir in dates:
            try:
                message = publish_date(
                    date_dir,
                    args.staging,
                    max_part_bytes,
                    tags,
                    args.dry_run,
                )
                results.append(message)
                if match := PUBLISHED_TAG_RE.match(message):
                    published_tags.append(match.group(1))
                print(message, flush=True)
            except Exception as exc:
                message = f"FAILED {date_dir.name}: {exc}"
                failures.append(message)
                print(message, file=sys.stderr, flush=True)

        if (
            published_tags
            and not failures
            and not args.dry_run
            and not args.skip_atlas_dispatch
        ):
            try:
                batch_id = dispatch_full_atlas(repo, published_tags)
                message = (
                    f"DISPATCHED full-corpus Atlas: {batch_id} "
                    f"after {len(published_tags)} new Release(s)"
                )
                results.append(message)
                print(message, flush=True)
            except Exception as exc:
                message = (
                    "FAILED Atlas dispatch after the experiment Releases were published: "
                    f"{exc}"
                )
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
