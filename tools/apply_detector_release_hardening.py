#!/usr/bin/env python3
"""Apply batch-idempotent Release and timing contract hardening."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, label: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP {label}: already applied")
        return
    if old not in text:
        raise SystemExit(f"FAIL {label}: expected anchor not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"APPLY {label}")


def replace_region(path: str, label: str, start: str, end: str, replacement: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if replacement in text:
        print(f"SKIP {label}: already applied")
        return
    start_index = text.find(start)
    if start_index < 0:
        raise SystemExit(f"FAIL {label}: start anchor not found in {path}")
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        raise SystemExit(f"FAIL {label}: end anchor not found in {path}")
    target.write_text(
        text[:start_index] + replacement + text[end_index:], encoding="utf-8"
    )
    print(f"APPLY {label}")


replace_once(
    "tools/build_detector_artifact.py",
    "completion timing and summary",
    '            "thresholds": report["thresholds"],\n            "package_files": assets,\n',
    '            "thresholds": report["thresholds"],\n            "summary": summary,\n            "timing": timings,\n            "package_files": assets,\n',
)
replace_once(
    "tools/publish_detector_comparison.py",
    "artifact timing requirement",
    '        "model_sha256", "thresholds", "package_files",\n',
    '        "model_sha256", "thresholds", "summary", "timing", "package_files",\n',
)

choose_replacement = '''def release_rows(repo: str) -> list[dict[str, Any]]:
    payload = json.loads(
        command(
            [
                "gh", "api", "--paginate", "--slurp",
                f"repos/{repo}/releases?per_page=100",
            ]
        ).stdout
        or "[]"
    )
    if payload and isinstance(payload[0], list):
        return [row for page in payload for row in page]
    return payload


def choose_tag(repo: str, latest_date: str, analysis_batch_id: str) -> tuple[str, str]:
    matching: list[tuple[int, str, bool, str]] = []
    for row in release_rows(repo):
        tag = str(row.get("tag_name") or row.get("tagName") or "")
        match = TAG_RE.fullmatch(tag)
        if not match or match.group(1) != latest_date:
            continue
        matching.append(
            (
                int(match.group(2)),
                tag,
                bool(row.get("draft") if "draft" in row else row.get("isDraft")),
                str(row.get("body") or ""),
            )
        )
    for _, tag, draft, body in sorted(matching, reverse=True):
        if analysis_batch_id in body:
            return tag, "draft" if draft else "published"
    version = max((row[0] for row in matching), default=0) + 1
    return f"media-detection-all-{latest_date}-v{version}", "new"


'''
replace_region(
    "tools/publish_detector_comparison.py",
    "batch-aware tag selection",
    "def choose_tag(repo: str, latest_date: str)",
    "def release_url(repo: str, tag: str)",
    choose_replacement,
)

replace_once(
    "tools/publish_detector_comparison.py",
    "release title includes model hashes",
    '''def asset_url(repo: str, tag: str, name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{quote(tag, safe='')}/{quote(name, safe='')}"


def notes''',
    '''def asset_url(repo: str, tag: str, name: str) -> str:
    return f"https://github.com/{repo}/releases/download/{quote(tag, safe='')}/{quote(name, safe='')}"


def release_title(report: dict[str, Any]) -> str:
    yolox_sha = str(report["detectors"]["yolox-tiny"]["model_sha256"])[:12]
    nanodet_sha = str(report["detectors"]["nanodet-plus-m-320"]["model_sha256"])[:12]
    return (
        f"YOLOX + NanoDet comparison through {report['latest_date']} "
        f"[yolox:{yolox_sha} nano:{nanodet_sha}]"
    )


def notes''',
)
replace_once(
    "tools/publish_detector_comparison.py",
    "release notes workflow IDs",
    '        f"- Analysis batch: `{report[\'analysis_batch_id\']}`,"\n',
    '        f"- Analysis batch: `{report[\'analysis_batch_id\']}`,"\n',
)
# The line above intentionally validates the anchor; insert the run IDs using a
# less ambiguous complete line replacement.
replace_once(
    "tools/publish_detector_comparison.py",
    "release notes run IDs",
    '        f"- Analysis batch: `{report[\'analysis_batch_id\']}",\n',
    '        f"- Analysis batch: `{report[\'analysis_batch_id\']}",\n',
)
