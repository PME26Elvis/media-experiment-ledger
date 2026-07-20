#!/usr/bin/env python3
"""Audit every formal experiment Release and optionally repair managed Notes.

The audit deliberately has no persistent processing cache.  Each run lists all
published media-exp-* Releases, downloads their manifests and standalone JSONL,
and can also download every media ZIP to verify the archive central directory,
member counts, ZIP CRCs, byte sizes, and SHA-256 digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

from release_policy import (
    IMAGE_SUFFIXES,
    VIDEO_SUFFIXES,
    is_quarantined,
    media_counts_from_file_records,
    quarantine_entry,
)

MEDIA_TAG_PREFIX = "media-exp-"
MANAGED_NOTES_MARKER = "<!-- managed:experiment-release-audit:v1 -->"


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def completion_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    images = 0
    videos = 0
    for row in rows:
        event = row.get("event")
        images += int(event == "image_completed")
        videos += int(event == "video_completed")
    return {"images": images, "videos": videos}


def metadata_file(root: Path, run_id: str, kind: str) -> Path | None:
    exact = root / f"{run_id}-{kind}.jsonl"
    if exact.exists():
        return exact
    candidates = sorted(root.glob(f"{run_id}*{kind}.jsonl"))
    return candidates[0] if candidates else None


def archive_media_counts(path: Path) -> tuple[dict[str, int], str | None]:
    counts = {"images": 0, "videos": 0}
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                return counts, bad
            for name in archive.namelist():
                member = PurePosixPath(name)
                if len(member.parts) < 3 or member.parts[0] != "media":
                    continue
                if member.parts[1] == "images" and member.suffix.lower() in IMAGE_SUFFIXES:
                    counts["images"] += 1
                elif member.parts[1] == "videos" and member.suffix.lower() in VIDEO_SUFFIXES:
                    counts["videos"] += 1
    except (OSError, zipfile.BadZipFile) as exc:
        return counts, str(exc)
    return counts, None


def anomaly(
    code: str,
    message: str,
    *,
    severity: str = "error",
) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def audit_run(
    tag: str,
    run: dict[str, Any],
    root: Path,
    *,
    verify_archives: bool,
) -> dict[str, Any]:
    run_id = str(run.get("run_id") or "")
    stats = run.get("stats") if isinstance(run.get("stats"), dict) else {}
    files = run.get("files") if isinstance(run.get("files"), list) else []
    assets = run.get("assets") if isinstance(run.get("assets"), list) else []
    policy = quarantine_entry(tag, run_id)
    quarantined = policy is not None
    issues: list[dict[str, str]] = []

    outputs = read_jsonl(metadata_file(root, run_id, "outputs"))
    errors = read_jsonl(metadata_file(root, run_id, "errors"))
    events = completion_counts(outputs)
    manifest_media = media_counts_from_file_records(
        [item for item in files if isinstance(item, dict)]
    )
    stats_events = {
        "images": int(stats.get("image_completed") or 0),
        "videos": int(stats.get("video_completed") or 0),
    }

    if quarantined:
        issues.append(
            anomaly(
                "quarantined_historical_run",
                str(policy.get("reason_en") or policy.get("reason_zh") or "quarantined"),
                severity="info",
            )
        )
    if not run_id.startswith("run_"):
        issues.append(anomaly("invalid_run_id", f"Unexpected run ID: {run_id}"))
    if int(stats.get("file_count") or len(files)) == 0 and not files:
        issues.append(
            anomaly(
                "empty_run",
                "Run contains no source files",
                severity="warning" if quarantined else "error",
            )
        )
    if stats_events != events:
        issues.append(
            anomaly(
                "manifest_stats_vs_jsonl",
                f"manifest stats={stats_events}, standalone JSONL={events}",
                severity="warning" if quarantined else "error",
            )
        )
    if events != manifest_media:
        issues.append(
            anomaly(
                "completed_events_vs_manifest_media",
                f"completed events={events}, manifest media files={manifest_media}",
                severity="warning" if quarantined else "error",
            )
        )

    archive_counts = {"images": 0, "videos": 0}
    asset_checks: list[dict[str, Any]] = []
    media_bytes = 0
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        kind = str(asset.get("kind") or "")
        if kind not in {"images", "videos"}:
            continue
        media_bytes += int(asset.get("size_bytes") or 0)
        row: dict[str, Any] = {
            "name": name,
            "kind": kind,
            "expected_size_bytes": int(asset.get("size_bytes") or 0),
            "expected_sha256": str(asset.get("sha256") or ""),
            "downloaded": False,
        }
        path = root / name
        if verify_archives:
            if not path.exists():
                issues.append(anomaly("missing_release_asset", f"Missing downloaded asset {name}"))
                row["status"] = "missing"
            else:
                row["downloaded"] = True
                row["actual_size_bytes"] = path.stat().st_size
                row["actual_sha256"] = sha256_file(path)
                if row["expected_size_bytes"] and row["actual_size_bytes"] != row["expected_size_bytes"]:
                    issues.append(anomaly("asset_size_mismatch", name))
                if row["expected_sha256"] and row["actual_sha256"] != row["expected_sha256"]:
                    issues.append(anomaly("asset_sha256_mismatch", name))
                member_counts, bad_member = archive_media_counts(path)
                row["media_members"] = member_counts
                row["bad_member"] = bad_member
                if bad_member:
                    issues.append(anomaly("bad_zip", f"{name}: {bad_member}"))
                archive_counts["images"] += member_counts["images"]
                archive_counts["videos"] += member_counts["videos"]
                row["status"] = "ok" if not bad_member else "failed"
        else:
            row["status"] = "not_downloaded"
        asset_checks.append(row)

    effective_archive_counts = archive_counts if verify_archives else manifest_media
    if verify_archives and effective_archive_counts != manifest_media:
        issues.append(
            anomaly(
                "manifest_media_vs_zip_members",
                f"manifest media files={manifest_media}, ZIP media members={effective_archive_counts}",
                severity="warning" if quarantined else "error",
            )
        )

    non_quarantine_errors = [
        issue
        for issue in issues
        if issue["severity"] == "error" and not quarantined
    ]
    return {
        "run_id": run_id,
        "digest": str(run.get("digest") or ""),
        "canonical": not quarantined,
        "quarantine": policy,
        "source_bytes": int(stats.get("source_bytes") or 0),
        "file_count": int(stats.get("file_count") or len(files)),
        "error_rows": len(errors),
        "manifest_completion_events": stats_events,
        "jsonl_completion_events": events,
        "manifest_media_files": manifest_media,
        "archive_media_files": effective_archive_counts,
        "packaged_media_bytes": media_bytes,
        "asset_checks": asset_checks,
        "anomalies": issues,
        "status": "error" if non_quarantine_errors else ("quarantined" if quarantined else "ok"),
    }


def audit_release_directory(
    tag: str,
    root: Path,
    *,
    verify_archives: bool,
    release_name: str = "",
    published_at: str = "",
) -> dict[str, Any]:
    manifests = sorted(root.glob("manifest-*.json"))
    if not manifests:
        raise FileNotFoundError(f"No manifest found for {tag}")
    manifest_values = [read_json(path) for path in manifests]
    runs: list[dict[str, Any]] = []
    dates: list[str] = []
    digests: list[str] = []
    for manifest in manifest_values:
        dates.append(str(manifest.get("experiment_date_taipei") or ""))
        digests.append(str(manifest.get("content_digest") or ""))
        for run in manifest.get("runs", []):
            if isinstance(run, dict):
                runs.append(audit_run(tag, run, root, verify_archives=verify_archives))

    canonical = [run for run in runs if run["canonical"]]
    quarantined = [run for run in runs if not run["canonical"]]
    canonical_errors = [
        issue
        for run in canonical
        for issue in run["anomalies"]
        if issue["severity"] == "error"
    ]
    totals = {
        "api_image_completed": sum(run["jsonl_completion_events"]["images"] for run in canonical),
        "api_video_completed": sum(run["jsonl_completion_events"]["videos"] for run in canonical),
        "archived_images": sum(run["archive_media_files"]["images"] for run in canonical),
        "archived_videos": sum(run["archive_media_files"]["videos"] for run in canonical),
        "errors": sum(run["error_rows"] for run in canonical),
        "packaged_media_bytes": sum(run["packaged_media_bytes"] for run in canonical),
    }
    status = "error" if canonical_errors else ("corrected" if quarantined else "ok")
    return {
        "tag": tag,
        "name": release_name,
        "published_at": published_at,
        "experiment_dates": sorted({date for date in dates if date}),
        "manifest_digests": sorted({digest for digest in digests if digest}),
        "manifest_runs": len(runs),
        "canonical_runs": len(canonical),
        "quarantined_runs": len(quarantined),
        "status": status,
        "verify_archives": verify_archives,
        "totals": totals,
        "runs": runs,
    }


def render_release_notes(release: dict[str, Any]) -> str:
    totals = release["totals"]
    dates = ", ".join(release.get("experiment_dates") or []) or "unknown"
    status = str(release.get("status") or "unknown").upper()
    gib = totals["packaged_media_bytes"] / 1024**3
    lines = [
        MANAGED_NOTES_MARKER,
        f"Experiment date: **{dates}** (Asia/Taipei)",
        f"Manifest runs: **{release['manifest_runs']}**",
        f"Canonical runs: **{release['canonical_runs']}**",
        f"Quarantined historical runs: **{release['quarantined_runs']}**",
        f"API image completion events: **{totals['api_image_completed']:,}**",
        f"Archived image files: **{totals['archived_images']:,}**",
        f"API video completion events: **{totals['api_video_completed']:,}**",
        f"Archived video files: **{totals['archived_videos']:,}**",
        f"Errors in canonical runs: **{totals['errors']:,}**",
        f"Packaged canonical media: **{gib:.2f} GiB**",
        f"Audit status: **{status}**",
        "",
        "The API-event and archived-file counts intentionally use separate labels. "
        "A completion event is not accepted as archived media unless a corresponding "
        "file is present in the manifest and media ZIP.",
        "",
        "## Canonical runs",
    ]
    canonical = [run for run in release["runs"] if run["canonical"]]
    lines.extend(
        f"- `{run['run_id']}` — {run['archive_media_files']['images']} images, "
        f"{run['archive_media_files']['videos']} videos"
        for run in canonical
    )
    if not canonical:
        lines.append("- None")

    quarantined = [run for run in release["runs"] if not run["canonical"]]
    if quarantined:
        lines.extend(["", "## Quarantined historical runs"])
        for run in quarantined:
            policy = run.get("quarantine") or {}
            reason = policy.get("reason_en") or policy.get("reason_zh") or "quarantined"
            lines.append(f"- `{run['run_id']}` — {reason}")

    warnings = [
        (run["run_id"], issue)
        for run in release["runs"]
        for issue in run["anomalies"]
        if issue["severity"] in {"warning", "error"}
    ]
    if warnings:
        lines.extend(["", "## Audit findings"])
        lines.extend(
            f"- `{run_id}` · `{issue['code']}` · {issue['message']}"
            for run_id, issue in warnings
        )

    lines.extend(
        [
            "",
            "## Data layout",
            "Media remains grouped by run and media type. Standalone JSONL metadata "
            "and the Release manifest remain separate so analytics can run without "
            "downloading media archives.",
            "",
            "Full audit report: "
            "[`docs/reports/EXPERIMENT_RELEASE_AUDIT.md`](../../blob/main/docs/reports/EXPERIMENT_RELEASE_AUDIT.md)",
            "",
            "Manifest digest(s): "
            + (", ".join(f"`{value}`" for value in release.get("manifest_digests", [])) or "—"),
        ]
    )
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    totals = report["canonical_totals"]
    lines = [
        "# Experiment Release Audit",
        "",
        "> 此報告由 GitHub Actions 全量重建，不使用持久化 state 或 cache。",
        "",
        f"- Generated at (UTC): `{report['generated_at_utc']}`",
        f"- Repository: `{report['repository']}`",
        f"- Releases audited: **{report['release_count']}**",
        f"- Canonical runs: **{report['canonical_run_count']}**",
        f"- Quarantined historical runs: **{report['quarantined_run_count']}**",
        f"- Canonical archived images: **{totals['archived_images']:,}**",
        f"- Canonical archived videos: **{totals['archived_videos']:,}**",
        "",
        "## Release summary",
        "",
        "| Release | Status | Manifest runs | Canonical | Quarantined | API images | Archived images | API videos | Archived videos |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for release in report["releases"]:
        value = release["totals"]
        lines.append(
            f"| `{release['tag']}` | {release['status']} | {release['manifest_runs']} | "
            f"{release['canonical_runs']} | {release['quarantined_runs']} | "
            f"{value['api_image_completed']} | {value['archived_images']} | "
            f"{value['api_video_completed']} | {value['archived_videos']} |"
        )

    lines.extend(["", "## Findings", ""])
    findings = 0
    for release in report["releases"]:
        for run in release["runs"]:
            for issue in run["anomalies"]:
                if issue["severity"] == "info":
                    continue
                findings += 1
                lines.append(
                    f"- `{release['tag']}` / `{run['run_id']}` · "
                    f"**{issue['severity']}** · `{issue['code']}` · {issue['message']}"
                )
    if not findings:
        lines.append("- No non-informational findings.")
    lines.extend(
        [
            "",
            "## Quarantine policy",
            "",
            "歷史 Release assets 維持不變；已確認無效的 run 由 "
            "`config/release-quarantine.json` 排除。Analytics、README、Atlas 與未來衍生分析共用同一份 policy。",
        ]
    )
    return "\n".join(lines) + "\n"


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
            "tagName,name,publishedAt,isDraft,isPrerelease",
        ]
    )
    values = json.loads(result.stdout or "[]")
    return sorted(
        [
            row
            for row in values
            if isinstance(row, dict)
            and not row.get("isDraft")
            and str(row.get("tagName") or "").startswith(MEDIA_TAG_PREFIX)
        ],
        key=lambda row: (str(row.get("publishedAt") or ""), str(row.get("tagName") or "")),
    )


def download_release(repo: str, tag: str, target: Path, verify_archives: bool) -> None:
    patterns = ["manifest-*.json", "run_*-outputs.jsonl", "run_*-errors.jsonl"]
    if verify_archives:
        patterns.extend(["run_*-images*.zip", "run_*-videos*.zip"])
    for pattern in patterns:
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
                "--clobber",
            ],
            check=False,
        )


def build_report(repo: str, *, verify_archives: bool, repair_notes: bool) -> dict[str, Any]:
    audited: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="experiment-release-audit-") as tmp:
        root = Path(tmp)
        for row in release_rows(repo):
            tag = str(row.get("tagName") or "")
            target = root / tag
            target.mkdir(parents=True, exist_ok=True)
            download_release(repo, tag, target, verify_archives)
            release = audit_release_directory(
                tag,
                target,
                verify_archives=verify_archives,
                release_name=str(row.get("name") or ""),
                published_at=str(row.get("publishedAt") or ""),
            )
            audited.append(release)
            if repair_notes:
                notes_path = target / "audited-release-notes.md"
                notes_path.write_text(render_release_notes(release), encoding="utf-8")
                command(
                    [
                        "gh",
                        "release",
                        "edit",
                        tag,
                        "--repo",
                        repo,
                        "--notes-file",
                        str(notes_path),
                    ]
                )

    canonical_runs = [
        run
        for release in audited
        for run in release["runs"]
        if run["canonical"]
    ]
    quarantined_runs = [
        run
        for release in audited
        for run in release["runs"]
        if not run["canonical"]
    ]
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": repo,
        "verify_archives": verify_archives,
        "release_notes_repaired": repair_notes,
        "release_count": len(audited),
        "canonical_run_count": len(canonical_runs),
        "quarantined_run_count": len(quarantined_runs),
        "canonical_totals": {
            "api_image_completed": sum(run["jsonl_completion_events"]["images"] for run in canonical_runs),
            "api_video_completed": sum(run["jsonl_completion_events"]["videos"] for run in canonical_runs),
            "archived_images": sum(run["archive_media_files"]["images"] for run in canonical_runs),
            "archived_videos": sum(run["archive_media_files"]["videos"] for run in canonical_runs),
            "errors": sum(run["error_rows"] for run in canonical_runs),
            "packaged_media_bytes": sum(run["packaged_media_bytes"] for run in canonical_runs),
        },
        "releases": audited,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--verify-archives", action="store_true")
    parser.add_argument("--repair-notes", action="store_true")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/audits/experiment-releases.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("docs/reports/EXPERIMENT_RELEASE_AUDIT.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.repo,
        verify_archives=args.verify_archives,
        repair_notes=args.repair_notes,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    canonical_errors = [
        issue
        for release in report["releases"]
        for run in release["runs"]
        if run["canonical"]
        for issue in run["anomalies"]
        if issue["severity"] == "error"
    ]
    if canonical_errors:
        print(json.dumps(canonical_errors, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report["canonical_totals"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
