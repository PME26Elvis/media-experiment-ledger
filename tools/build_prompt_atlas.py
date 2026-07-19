#!/usr/bin/env python3
"""Build, package, publish, and index a full-corpus Prompt Repeatability Atlas."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_atlas_build import build, stage_highlight_previews, write_pages_index
from prompt_atlas_github import dataset_fingerprint, publish_release, release_rows
from prompt_atlas_packages import create_release_packages


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["all"], default="all")
    parser.add_argument("--source-tag", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--batch-id",
        default=os.environ.get("ATLAS_BATCH_ID")
        or datetime.now(timezone.utc).strftime("manual-%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--config", type=Path, default=Path("visual-analysis/config.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("visual-analysis/output"))
    parser.add_argument("--pages-index", type=Path, default=Path("web/public/data/visual-analysis.json"))
    parser.add_argument(
        "--preview-root",
        type=Path,
        default=Path("web/public/data/visual-analysis/previews"),
    )
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json(args.config, {})
    rows = release_rows()
    if not rows:
        raise RuntimeError("No published media-exp-* Releases are available")
    fingerprint = dataset_fingerprint(rows, config)
    with tempfile.TemporaryDirectory(prefix="prompt-atlas-") as temp:
        entries, report = build(
            rows,
            fingerprint,
            config,
            Path(temp),
            args.output_dir,
            args.batch_id,
        )
    preview_urls = stage_highlight_previews(
        args.output_dir,
        args.preview_root,
        args.repo,
        fingerprint,
        args.batch_id,
        entries,
        config,
    )
    publication = (
        publish_release(
            args.repo,
            fingerprint,
            args.output_dir,
            entries,
            config,
            report,
            preview_urls,
            force=args.force,
        )
        if args.publish and entries
        else None
    )
    write_pages_index(args.pages_index, report, publication, preview_urls)
    print(
        json.dumps(
            {
                "dataset_fingerprint": fingerprint,
                "release_count_scanned": len(rows),
                "comparable_prompts": len(entries),
                "analysis_tag": publication.get("analysis_tag") if publication else None,
                "reused_published": publication.get("reused_published", False) if publication else False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
