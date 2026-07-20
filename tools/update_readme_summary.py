#!/usr/bin/env python3
"""Rebuild bilingual README statistics and Atlas history from published Releases."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from atlas_history_policy import historical_metric
from release_policy import is_quarantined, media_counts_from_file_records

MEDIA_TAG_RE = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})(?:-s\d{2})?$")
ATLAS_TAG_RE = re.compile(r"^media-analysis-")
ZH_STATS_START = "<!-- AUTO:LEDGER_STATS:START -->"
ZH_STATS_END = "<!-- AUTO:LEDGER_STATS:END -->"
ZH_ATLAS_START = "<!-- AUTO:ATLAS_HISTORY:START -->"
ZH_ATLAS_END = "<!-- AUTO:ATLAS_HISTORY:END -->"
EN_STATS_START = "<!-- AUTO:LEDGER_STATS_EN:START -->"
EN_STATS_END = "<!-- AUTO:LEDGER_STATS_EN:END -->"
EN_ATLAS_START = "<!-- AUTO:ATLAS_HISTORY_EN:START -->"
EN_ATLAS_END = "<!-- AUTO:ATLAS_HISTORY_EN:END -->"


class CommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExperimentTotals:
    release_count: int
    date_from: str | None
    date_to: str | None
    images: int
    videos: int
    per_release: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class AtlasHistoryRow:
    published_at: str
    tag: str
    name: str
    scope: str
    images: int | None
    videos: int | None
    comparable_prompts: int | None
    url: str


def command(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise CommandError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result


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
    value = json.loads(result.stdout or "[]")
    if not isinstance(value, list):
        raise ValueError("Unexpected gh release list response")
    return [row for row in value if isinstance(row, dict) and not row.get("isDraft")]


def safe_directory_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "release"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def download_pattern(repo: str, tag: str, pattern: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
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
            str(destination),
        ],
        check=False,
    )


def release_manifests(repo: str, tag: str, root: Path) -> list[dict[str, Any]]:
    target = root / "experiment" / safe_directory_name(tag)
    download_pattern(repo, tag, "manifest-*.json", target)
    return [value for path in sorted(target.glob("manifest-*.json")) if (value := read_json(path))]


def fallback_output_counts(repo: str, tag: str, root: Path) -> tuple[int, int]:
    target = root / "outputs" / safe_directory_name(tag)
    download_pattern(repo, tag, "run_*-outputs.jsonl", target)
    images = 0
    videos = 0
    for path in sorted(target.glob("run_*-outputs.jsonl")):
        run_id = path.name.removesuffix("-outputs.jsonl")
        if is_quarantined(tag, run_id):
            continue
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event = row.get("event") if isinstance(row, dict) else None
                images += int(event == "image_completed")
                videos += int(event == "video_completed")
    return images, videos


def summarize_experiments(
    rows: Sequence[dict[str, Any]],
    repo: str,
    root: Path,
) -> ExperimentTotals:
    media_rows = sorted(
        (row for row in rows if MEDIA_TAG_RE.match(str(row.get("tagName") or ""))),
        key=lambda row: (str(row.get("publishedAt") or ""), str(row.get("tagName") or "")),
    )
    seen_runs: set[tuple[str, str]] = set()
    per_release: dict[str, dict[str, Any]] = {}
    dates: list[str] = []
    total_images = 0
    total_videos = 0

    for row in media_rows:
        tag = str(row.get("tagName") or "")
        match = MEDIA_TAG_RE.match(tag)
        if match:
            dates.append(match.group(1))
        images = 0
        videos = 0
        manifests = release_manifests(repo, tag, root)
        if manifests:
            for manifest in manifests:
                for run in manifest.get("runs", []):
                    if not isinstance(run, dict):
                        continue
                    run_id = str(run.get("run_id") or "")
                    if is_quarantined(tag, run_id):
                        continue
                    key = (run_id, str(run.get("digest") or ""))
                    if key in seen_runs:
                        continue
                    seen_runs.add(key)
                    has_file_records = isinstance(run.get("files"), list)
                    files = run.get("files") if has_file_records else []
                    if has_file_records:
                        # Explicit file records are authoritative, including an
                        # explicit metadata-only run whose archived media count is zero.
                        archived = media_counts_from_file_records(files)
                        images += archived["images"]
                        videos += archived["videos"]
                    else:
                        # Legacy manifests predate file records. Preserve backwards
                        # compatibility while new manifests use archived-file truth.
                        stats = run.get("stats") if isinstance(run.get("stats"), dict) else {}
                        images += int(stats.get("archived_images", stats.get("image_completed", 0)) or 0)
                        videos += int(stats.get("archived_videos", stats.get("video_completed", 0)) or 0)
        else:
            images, videos = fallback_output_counts(repo, tag, root)
        per_release[tag] = {
            "date": match.group(1) if match else None,
            "images": images,
            "videos": videos,
        }
        total_images += images
        total_videos += videos

    return ExperimentTotals(
        release_count=len(media_rows),
        date_from=min(dates) if dates else None,
        date_to=max(dates) if dates else None,
        images=total_images,
        videos=total_videos,
        per_release=per_release,
    )


def report_from_metadata_zip(path: Path) -> dict[str, Any] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith("atlas-report.json")]
            if not names:
                return None
            value = json.loads(archive.read(sorted(names)[0]).decode("utf-8"))
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def atlas_report(repo: str, tag: str, root: Path) -> dict[str, Any] | None:
    target = root / "atlas" / safe_directory_name(tag)
    download_pattern(repo, tag, "atlas-metadata.zip", target)
    for path in sorted(target.glob("atlas-metadata.zip")):
        if report := report_from_metadata_zip(path):
            return report
    download_pattern(repo, tag, "atlas-report.json", target)
    for path in sorted(target.glob("atlas-report.json")):
        if report := read_json(path):
            return report
    return None


def tags_for_report(report: dict[str, Any], totals: ExperimentTotals) -> list[str]:
    explicit = report.get("release_tags")
    if isinstance(explicit, list):
        return [str(tag) for tag in explicit if str(tag) in totals.per_release]
    source_tag = str(report.get("source_tag") or "")
    if source_tag in totals.per_release:
        return [source_tag]
    date_from = str(report.get("date_from") or "")
    date_to = str(report.get("date_to") or "")
    if report.get("dataset_scope") == "all_published_media_exp_releases" and date_to:
        return [
            tag
            for tag, values in totals.per_release.items()
            if (not date_from or str(values.get("date") or "") >= date_from)
            and str(values.get("date") or "") <= date_to
        ]
    return []


def atlas_history(
    rows: Sequence[dict[str, Any]],
    repo: str,
    root: Path,
    totals: ExperimentTotals,
) -> list[AtlasHistoryRow]:
    atlas_rows = sorted(
        (row for row in rows if ATLAS_TAG_RE.match(str(row.get("tagName") or ""))),
        key=lambda row: (str(row.get("publishedAt") or ""), str(row.get("tagName") or "")),
        reverse=True,
    )
    history: list[AtlasHistoryRow] = []
    for row in atlas_rows:
        tag = str(row.get("tagName") or "")
        report = atlas_report(repo, tag, root)
        report = report or {}
        selected_tags = tags_for_report(report, totals)
        # Historical Atlas rows are immutable snapshots. Modern reports
        # carry explicit corpus counts; audited overrides cover the few legacy
        # schemas that do not. Current experiment totals must never time-travel
        # into an older Atlas row.
        images = historical_metric(tag, report, "images")
        videos = historical_metric(tag, report, "videos")
        date_from = str(report.get("date_from") or "")
        date_to = str(report.get("date_to") or "")
        if not date_from and len(selected_tags) == 1:
            date_from = str(totals.per_release[selected_tags[0]].get("date") or "")
            date_to = date_from
        scope = f"{date_from} → {date_to}" if date_from and date_to and date_from != date_to else (date_from or "—")
        comparable = report.get("comparable_prompts")
        if comparable is None and isinstance(report.get("entries"), list):
            comparable = len(report["entries"])
        display_name = "全域重現性圖譜" if tag.startswith("media-analysis-all-") else "歷史單次圖譜"
        history.append(
            AtlasHistoryRow(
                published_at=str(row.get("publishedAt") or ""),
                tag=tag,
                name=display_name,
                scope=scope,
                images=images,
                videos=videos,
                comparable_prompts=int(comparable) if comparable is not None else None,
                url=f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}",
            )
        )
    return history


def markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def number(value: int | None) -> str:
    return f"{value:,}" if value is not None else "—"


def replace_block(text: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"README marker pair is missing: {start} / {end}")
    replacement = f"{start}\n{body.rstrip()}\n{end}"
    return pattern.sub(lambda _: replacement, text, count=1)


def render_stats_zh(totals: ExperimentTotals, history: Sequence[AtlasHistoryRow]) -> str:
    latest = history[0] if history else None
    latest_value = f"[{latest.tag}]({latest.url})" if latest else "尚未發布"
    date_range = f"{totals.date_from} → {totals.date_to}" if totals.date_from and totals.date_to else "—"
    return "\n".join(
        [
            "> 此區塊由 GitHub Actions 全量重建；只統計正式 `media-exp-*` 中非 quarantine runs 的封存媒體，`media-input-*` snapshot 與純 metadata fixture 不會重複計入。",
            "",
            "| 統計項目 | 數值 |",
            "|---|---:|",
            f"| 正式 Experiment Releases | {totals.release_count:,} |",
            f"| 實驗日期範圍 | {date_range} |",
            f"| 圖片總數 | {totals.images:,} |",
            f"| 影片總數 | {totals.videos:,} |",
            f"| 最新 Prompt Repeatability Atlas | {latest_value} |",
        ]
    )


def render_stats_en(totals: ExperimentTotals, history: Sequence[AtlasHistoryRow]) -> str:
    latest = history[0] if history else None
    latest_value = f"[{latest.tag}]({latest.url})" if latest else "Not published yet"
    date_range = f"{totals.date_from} → {totals.date_to}" if totals.date_from and totals.date_to else "—"
    return "\n".join(
        [
            "> Rebuilt from all Releases by GitHub Actions. Totals count archived media from non-quarantined runs in formal `media-exp-*` Releases; `media-input-*` snapshots and metadata-only fixtures are excluded.",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Formal experiment Releases | {totals.release_count:,} |",
            f"| Experiment date range | {date_range} |",
            f"| Total images | {totals.images:,} |",
            f"| Total videos | {totals.videos:,} |",
            f"| Latest Prompt Repeatability Atlas | {latest_value} |",
        ]
    )


def render_history_zh(history: Sequence[AtlasHistoryRow]) -> str:
    lines = [
        "> 每次 Atlas workflow 都重新掃描全部 Atlas Releases 並重建此表，不依賴增量狀態。",
        "",
        "| 發布日期 | 圖譜類型 | 資料範圍 | 圖片 | 影片 | 可比較 Prompt | Release |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in history:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row.published_at[:10] or "—"),
                    markdown_cell(row.name),
                    markdown_cell(row.scope),
                    number(row.images),
                    number(row.videos),
                    number(row.comparable_prompts),
                    f"[`{markdown_cell(row.tag)}`]({row.url})",
                ]
            )
            + " |"
        )
    if not history:
        lines.append("| — | 尚未發布 | — | — | — | — | — |")
    return "\n".join(lines)


def render_history_en(history: Sequence[AtlasHistoryRow]) -> str:
    lines = [
        "> Every Atlas workflow rescans all Atlas Releases and rebuilds this table without incremental state.",
        "",
        "| Published | Atlas type | Data range | Images | Videos | Comparable prompts | Release |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in history:
        atlas_type = "Global repeatability atlas" if row.tag.startswith("media-analysis-all-") else "Legacy single-release atlas"
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row.published_at[:10] or "—"),
                    atlas_type,
                    markdown_cell(row.scope),
                    number(row.images),
                    number(row.videos),
                    number(row.comparable_prompts),
                    f"[`{markdown_cell(row.tag)}`]({row.url})",
                ]
            )
            + " |"
        )
    if not history:
        lines.append("| — | Not published | — | — | — | — | — |")
    return "\n".join(lines)


def update_readmes(
    readme: Path,
    readme_en: Path,
    totals: ExperimentTotals,
    history: Sequence[AtlasHistoryRow],
) -> None:
    zh = readme.read_text(encoding="utf-8")
    zh = replace_block(zh, ZH_STATS_START, ZH_STATS_END, render_stats_zh(totals, history))
    zh = replace_block(zh, ZH_ATLAS_START, ZH_ATLAS_END, render_history_zh(history))
    readme.write_text(zh, encoding="utf-8")

    en = readme_en.read_text(encoding="utf-8")
    en = replace_block(en, EN_STATS_START, EN_STATS_END, render_stats_en(totals, history))
    en = replace_block(en, EN_ATLAS_START, EN_ATLAS_END, render_history_en(history))
    readme_en.write_text(en, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--readme-en", type=Path, default=Path("README.en.md"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = release_rows(args.repo)
    with tempfile.TemporaryDirectory(prefix="readme-release-summary-") as temporary:
        root = Path(temporary)
        totals = summarize_experiments(rows, args.repo, root)
        history = atlas_history(rows, args.repo, root, totals)
    if not args.dry_run:
        update_readmes(args.readme, args.readme_en, totals, history)
    print(
        json.dumps(
            {
                "experiment_releases": totals.release_count,
                "images": totals.images,
                "videos": totals.videos,
                "atlas_releases": len(history),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
