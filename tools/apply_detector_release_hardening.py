#!/usr/bin/env python3
"""Apply batch-idempotent Release and timing contract hardening."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, label: str, marker: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        print(f"SKIP {label}: already applied")
        return
    if old not in text:
        raise SystemExit(f"FAIL {label}: expected anchor not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"APPLY {label}")


def replace_region(
    path: str,
    label: str,
    marker: str,
    start: str,
    end: str,
    replacement: str,
) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
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
    '            "summary": summary,\n            "timing": timings,\n            "package_files": assets,',
    '            "thresholds": report["thresholds"],\n            "package_files": assets,',
    '            "thresholds": report["thresholds"],\n            "summary": summary,\n            "timing": timings,\n            "package_files": assets,',
)
replace_once(
    "tools/publish_detector_comparison.py",
    "artifact timing requirement",
    '"thresholds", "summary", "timing", "package_files"',
    '"model_sha256", "thresholds", "package_files"',
    '"model_sha256", "thresholds", "summary", "timing", "package_files"',
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
    "def release_rows(repo: str)",
    "def choose_tag(repo: str, latest_date: str)",
    "def release_url(repo: str, tag: str)",
    choose_replacement,
)

replace_once(
    "tools/publish_detector_comparison.py",
    "release title includes model hashes",
    "def release_title(report: dict[str, Any])",
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
    "release notes workflow run IDs",
    "YOLOX workflow run:",
    '''        f"- Analysis batch: `{report['analysis_batch_id']}`",
        f"- Source range: **{report['date_from']} → {report['date_to']}**",''',
    '''        f"- Analysis batch: `{report['analysis_batch_id']}`",
        f"- YOLOX workflow run: `{report['detectors']['yolox-tiny']['workflow_run_id']}`",
        f"- NanoDet workflow run: `{report['detectors']['nanodet-plus-m-320']['workflow_run_id']}`",
        f"- Source range: **{report['date_from']} → {report['date_to']}**",''',
)
replace_once(
    "tools/publish_detector_comparison.py",
    "release notes thresholds and throughput",
    "YOLOX throughput:",
    '''        f"- NanoDet model SHA-256: `{report['detectors']['nanodet-plus-m-320']['model_sha256']}`",
        "",''',
    '''        f"- NanoDet model SHA-256: `{report['detectors']['nanodet-plus-m-320']['model_sha256']}`",
        f"- Thresholds: confidence `{report['thresholds']['confidence']}`, NMS IoU `{report['thresholds']['nms_iou']}`, max `{report['thresholds']['max_detections']}`",
        f"- YOLOX throughput: **{report['detectors']['yolox-tiny']['timing'].get('mean_images_per_second', 0):.2f} images/s**",
        f"- NanoDet throughput: **{report['detectors']['nanodet-plus-m-320']['timing'].get('mean_images_per_second', 0):.2f} images/s**",
        "",''',
)

replace_once(
    "tools/publish_detector_comparison.py",
    "YOLOX report timing",
    '"summary": yolox_manifest["summary"]',
    '                "successful_images": yolox_manifest["successful_image_count"],',
    '''                "successful_images": yolox_manifest["successful_image_count"],
                "summary": yolox_manifest["summary"],
                "timing": yolox_manifest["timing"],''',
)
replace_once(
    "tools/publish_detector_comparison.py",
    "NanoDet report timing",
    '"summary": nanodet_manifest["summary"]',
    '                "successful_images": nanodet_manifest["successful_image_count"],',
    '''                "successful_images": nanodet_manifest["successful_image_count"],
                "summary": nanodet_manifest["summary"],
                "timing": nanodet_manifest["timing"],''',
)

replace_once(
    "tools/publish_detector_comparison.py",
    "release state selection",
    "release_state = choose_tag",
    '''    tag, resumed = choose_tag(args.repo, str(report["latest_date"]))
    release_page = release_url(args.repo, tag)''',
    '''    tag, release_state = choose_tag(
        args.repo, str(report["latest_date"]), str(report["analysis_batch_id"])
    )
    release_page = release_url(args.repo, tag)
    title = release_title(report)''',
)

publish_replacement = '''    if args.publish:
        preliminary = output / "preliminary.md"
        preliminary.write_text(
            "# Multi-detector analysis\\n\\n"
            f"- Analysis batch: `{report['analysis_batch_id']}`\\n"
            "- State: verified assets are being uploaded.\\n",
            encoding="utf-8",
        )
        if release_state == "new":
            command([
                "gh", "release", "create", tag, "--repo", args.repo,
                "--title", title, "--notes-file", str(preliminary),
                "--draft", "--latest=false",
            ])
        if release_state in {"new", "draft"}:
            if release_state == "draft":
                existing = json.loads(
                    command(["gh", "api", f"repos/{args.repo}/releases/tags/{tag}"]).stdout
                )
                for asset in existing.get("assets", []):
                    command([
                        "gh", "release", "delete-asset", tag,
                        str(asset["name"]), "--repo", args.repo, "--yes",
                    ])
            command([
                "gh", "release", "upload", tag, "--repo", args.repo,
                *map(str, sorted(release_assets.glob("*.zip"))), "--clobber",
            ])
            command([
                "gh", "release", "edit", tag, "--repo", args.repo,
                "--title", title, "--notes-file", str(output / "release-notes.md"),
                "--draft=false", "--latest=false",
            ])
        published = json.loads(
            command(["gh", "api", f"repos/{args.repo}/releases/tags/{tag}"]).stdout
        )
        if report["analysis_batch_id"] not in str(published.get("body") or ""):
            raise RuntimeError(f"Release {tag} does not carry the expected analysis batch")
        actual = {item["name"]: int(item["size"]) for item in published.get("assets", [])}
        expected = {item["name"]: int(item["size_bytes"]) for item in asset_manifest}
        if actual != expected:
            raise RuntimeError(f"Published detector asset mismatch: expected={expected}, actual={actual}")
        release_page = str(published.get("html_url") or release_page)

'''
replace_region(
    "tools/publish_detector_comparison.py",
    "batch-idempotent publication",
    'release_state in {"new", "draft"}',
    "    if args.publish:\n        preliminary = output / \"preliminary.md\"",
    "    preview_root = args.preview_root / tag",
    publish_replacement,
)

replace_once(
    ".github/workflows/detector-comparison-publish.yml",
    "trusted-main artifact runs",
    "must use the trusted main branch",
    '''              if run.get('head_branch') != 'main' and run.get('event') != 'workflow_dispatch':
                  raise SystemExit(f'Run {run_id} is not an authorized main/manual run')''',
    '''              if run.get('head_branch') != 'main':
                  raise SystemExit(f'Run {run_id} must use the trusted main branch')''',
)

replace_once(
    "tests/test_detector_comparison.py",
    "artifact fixture timing",
    '"summary": {},\n                "timing": {},',
    '                "thresholds": {"confidence": 0.25},\n                "package_files": [',
    '                "thresholds": {"confidence": 0.25},\n                "summary": {},\n                "timing": {},\n                "package_files": [',
)
replace_once(
    "tests/test_detector_comparison.py",
    "publication hardening test",
    "def test_publisher_is_batch_idempotent_and_carries_runtime",
    "    def test_artifact_validates_zip_hash_and_sidecar_coverage(self) -> None:\n",
    '''    def test_publisher_is_batch_idempotent_and_carries_runtime(self) -> None:
        source = (ROOT / "tools" / "publish_detector_comparison.py").read_text(encoding="utf-8")
        builder = (ROOT / "tools" / "build_detector_artifact.py").read_text(encoding="utf-8")
        self.assertIn('return tag, "draft" if draft else "published"', source)
        self.assertIn('release_state in {"new", "draft"}', source)
        self.assertIn("does not carry the expected analysis batch", source)
        self.assertIn('"timing": timings', builder)
        self.assertIn('"summary": summary', builder)

    def test_artifact_validates_zip_hash_and_sidecar_coverage(self) -> None:
''',
)
replace_once(
    "AGENTS.md",
    "publisher wording",
    "the publisher is `.github/workflows/detector-comparison-publish.yml`",
    "the planned publisher is `.github/workflows/detector-comparison-publish.yml`",
    "the publisher is `.github/workflows/detector-comparison-publish.yml`",
)
