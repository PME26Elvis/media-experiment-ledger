#!/usr/bin/env python3
"""Build canonical analytics and a static dashboard from experiment Releases."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import statistics
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt

from release_policy import is_quarantined, quarantine_policy_digest

TAG_RE = re.compile(r"^media-exp-(\d{4}-\d{2}-\d{2})(?:-s\d{2})?$")


def command(args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{(result.stderr or result.stdout).strip()}")
    return result


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number} is not a JSON object")
            rows.append(value)
    return rows


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def releases() -> list[dict[str, Any]]:
    result = command(["gh", "release", "list", "--limit", "1000", "--json", "tagName,publishedAt,name,isDraft,isPrerelease"])
    rows = json.loads(result.stdout or "[]")
    rows = [row for row in rows if TAG_RE.match(str(row.get("tagName") or ""))]
    return sorted(rows, key=lambda row: str(row.get("publishedAt") or ""))


def choose(rows: Sequence[dict[str, Any]], args: argparse.Namespace, state: dict[str, Any]) -> list[dict[str, Any]]:
    if args.mode == "rebuild_all":
        return list(rows)
    if args.mode == "new_only":
        done = set(state.get("processed_releases", {}))
        return [row for row in rows if row["tagName"] not in done]
    if args.mode == "latest_n":
        return list(rows[-args.latest_n :])
    if args.mode == "exact_tag":
        return [row for row in rows if row["tagName"] == args.exact_tag]
    selected = []
    for row in rows:
        date = TAG_RE.match(row["tagName"]).group(1)
        if args.from_date and date < args.from_date:
            continue
        if args.to_date and date > args.to_date:
            continue
        selected.append(row)
    return selected


def download(tag: str, target: Path, verify_media: bool) -> list[dict[str, Any]]:
    target.mkdir(parents=True, exist_ok=True)
    for pattern in ("manifest-*.json", "run_*-outputs.jsonl", "run_*-errors.jsonl"):
        command(["gh", "release", "download", tag, "--pattern", pattern, "--dir", str(target)], check=False)
    checks: list[dict[str, Any]] = []
    if verify_media:
        media = target / "media"
        media.mkdir()
        command(["gh", "release", "download", tag, "--pattern", "*.zip", "--dir", str(media)], check=False)
        for archive_path in sorted(media.glob("*.zip")):
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    bad = archive.testzip()
                checks.append({"asset": archive_path.name, "status": "ok" if bad is None else "failed", "bad_member": bad})
            except (OSError, zipfile.BadZipFile) as exc:
                checks.append({"asset": archive_path.name, "status": f"error: {exc}"})
    return checks


def metadata_file(root: Path, run_id: str, kind: str) -> Path | None:
    exact = root / f"{run_id}-{kind}.jsonl"
    if exact.exists():
        return exact
    matches = sorted(root.glob(f"{run_id}*{kind}.jsonl"))
    return matches[0] if matches else None


def summarize(date: str, tag: str, entry: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_id = str(entry["run_id"])
    outputs = read_jsonl(metadata_file(root, run_id, "outputs"))
    errors = read_jsonl(metadata_file(root, run_id, "errors"))
    completed = [row for row in outputs if row.get("event") in {"image_completed", "video_completed"}]
    events = Counter(str(row.get("event") or "unknown") for row in outputs)
    categories = Counter(str(row.get("category") or "uncategorized") for row in completed)
    models: Counter[str] = Counter()
    latencies: list[float] = []
    starts: list[datetime] = []
    finishes: list[datetime] = []
    for row in outputs + errors:
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("model"):
            models[str(payload["model"])] += 1
        start, finish = parse_time(row.get("timestamp")), parse_time(row.get("finished_at"))
        if start:
            starts.append(start)
        if finish:
            finishes.append(finish)
        if start and finish and finish >= start:
            latencies.append((finish - start).total_seconds())
    successes = events["image_completed"] + events["video_completed"]
    attempts = successes + len(errors)
    error_classes = Counter(str(row.get("error_class") or "unknown_error") for row in errors)
    run = {
        "date": date,
        "tag": tag,
        "run_id": run_id,
        "digest": str(entry.get("digest") or ""),
        "image_completed": events["image_completed"],
        "video_completed": events["video_completed"],
        "errors": len(errors),
        "success_rate": successes / attempts if attempts else None,
        "latency_mean_s": statistics.fmean(latencies) if latencies else None,
        "latency_p50_s": percentile(latencies, 0.50),
        "latency_p90_s": percentile(latencies, 0.90),
        "latency_p95_s": percentile(latencies, 0.95),
        "started_at": min(starts).isoformat() if starts else None,
        "finished_at": max(finishes).isoformat() if finishes else None,
        "source_bytes": int(entry.get("stats", {}).get("source_bytes", 0)),
        "file_count": int(entry.get("stats", {}).get("file_count", 0)),
        "models": dict(sorted(models.items())),
        "categories": dict(sorted(categories.items())),
        "error_classes": dict(sorted(error_classes.items())),
    }
    normalized_errors = []
    for row in errors:
        decision = row.get("decision") if isinstance(row.get("decision"), dict) else {}
        normalized_errors.append({
            "date": date,
            "tag": tag,
            "run_id": run_id,
            "phase": row.get("phase"),
            "prompt_id": row.get("prompt_id"),
            "category": row.get("category"),
            "error_class": row.get("error_class") or "unknown_error",
            "http_status": row.get("http_status"),
            "timestamp": row.get("timestamp"),
            "terminal": decision.get("terminal"),
            "stop_phase": decision.get("stop_phase"),
            "message": str(row.get("error") or "")[:1000],
        })
    return run, normalized_errors


def ingest(tag: str, root: Path, checks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifests = sorted(root.glob("manifest-*.json"))
    if not manifests:
        raise FileNotFoundError(f"No manifest found for {tag}")
    run_rows, error_rows, digests, dates = [], [], [], []
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        date = str(manifest.get("experiment_date_taipei") or "")
        dates.append(date)
        digests.append(str(manifest.get("content_digest") or ""))
        for entry in manifest.get("runs", []):
            run_id = str(entry.get("run_id") or "") if isinstance(entry, dict) else ""
            if is_quarantined(tag, run_id):
                continue
            run, errors = summarize(date, tag, entry, root)
            run_rows.append(run)
            error_rows.extend(errors)
    return run_rows, error_rows, {
        "experiment_dates": sorted(set(dates)),
        "manifest_digests": sorted(digests),
        "processed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "media_verification": checks,
        "quarantine_policy_digest": quarantine_policy_digest(),
    }


def aggregate(run_rows: Iterable[dict[str, Any]], monthly: bool = False) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        groups[row["date"][:7] if monthly else row["date"]].append(row)
    output = []
    for period, items in sorted(groups.items()):
        images = sum(row["image_completed"] for row in items)
        videos = sum(row["video_completed"] for row in items)
        errors = sum(row["errors"] for row in items)
        attempts = images + videos + errors
        latencies = [row["latency_mean_s"] for row in items if row["latency_mean_s"] is not None]
        output.append({
            "period": period,
            "runs": len(items),
            "image_completed": images,
            "video_completed": videos,
            "errors": errors,
            "success_rate": (images + videos) / attempts if attempts else None,
            "latency_mean_s": statistics.fmean(latencies) if latencies else None,
            "source_bytes": sum(row.get("source_bytes", 0) for row in items),
        })
    return output


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            value = {key: json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else item for key, item in row.items()}
            writer.writerow(value)


def table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(value) for value in row) + " |" for row in rows),
    ])


def rate(value: Any) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def seconds(value: Any) -> str:
    return "—" if value is None else f"{value:.1f}"


def reports(root: Path, runs: list[dict[str, Any]], errors: list[dict[str, Any]], daily: list[dict[str, Any]], monthly: list[dict[str, Any]]) -> None:
    images = sum(row["image_completed"] for row in runs)
    videos = sum(row["video_completed"] for row in runs)
    failures = sum(row["errors"] for row in runs)
    attempts = images + videos + failures
    overview = [
        "# Experiment Analytics", "",
        "Generated from immutable release manifests and standalone JSONL metadata.", "",
        "## Portfolio summary", "",
        table(["Metric", "Value"], [
            ["Runs", len(runs)], ["Experiment dates", len({row['date'] for row in runs})],
            ["Images completed", f"{images:,}"], ["Videos completed", f"{videos:,}"],
            ["Errors", f"{failures:,}"], ["Overall success", rate((images + videos) / attempts if attempts else None)],
        ]), "", "## Recent dates", "",
        table(["Date", "Runs", "Images", "Videos", "Errors", "Success", "Mean latency (s)"], [
            [row["period"], row["runs"], row["image_completed"], row["video_completed"], row["errors"], rate(row["success_rate"]), seconds(row["latency_mean_s"])]
            for row in reversed(daily[-20:])
        ]), "", "## Charts", "",
        "![Daily output](charts/daily-output-counts.svg)", "",
        "![Daily success](charts/daily-success-rate.svg)", "",
        "![Errors](charts/error-classes.svg)", "",
    ]
    (root / "overview.md").write_text("\n".join(overview), encoding="utf-8")
    (root / "README.md").write_text("# Analytics\n\nSee [overview.md](overview.md).\n", encoding="utf-8")
    for summary in daily:
        day_runs = [row for row in runs if row["date"] == summary["period"]]
        body = [f"# Daily report — {summary['period']}", "", table(
            ["Run", "Images", "Videos", "Errors", "Success", "P95 latency (s)"],
            [[row["run_id"], row["image_completed"], row["video_completed"], row["errors"], rate(row["success_rate"]), seconds(row["latency_p95_s"])] for row in day_runs],
        )]
        (root / "daily" / f"{summary['period']}.md").write_text("\n".join(body), encoding="utf-8")
    for summary in monthly:
        body = [f"# Monthly report — {summary['period']}", "", table(["Metric", "Value"], [
            ["Runs", summary["runs"]], ["Images", summary["image_completed"]], ["Videos", summary["video_completed"]],
            ["Errors", summary["errors"]], ["Success", rate(summary["success_rate"])], ["Mean latency (s)", seconds(summary["latency_mean_s"])],
        ])]
        (root / "monthly" / f"{summary['period']}.md").write_text("\n".join(body), encoding="utf-8")
    for row in runs:
        body = [f"# Run — {row['run_id']}", "", table(["Field", "Value"], [
            ["Date", row["date"]], ["Release", f"`{row['tag']}`"], ["Images", row["image_completed"]],
            ["Videos", row["video_completed"]], ["Errors", row["errors"]], ["Success", rate(row["success_rate"])],
            ["Mean latency (s)", seconds(row["latency_mean_s"])], ["P95 latency (s)", seconds(row["latency_p95_s"])],
            ["Source size (MiB)", f"{row['source_bytes'] / 1024**2:.1f}"], ["Digest", f"`{row['digest']}`"],
        ]), "", "## Models", "", "```json", json.dumps(row["models"], indent=2), "```", "", "## Categories", "", "```json", json.dumps(row["categories"], indent=2), "```"]
        (root / "runs" / f"{row['run_id']}.md").write_text("\n".join(body), encoding="utf-8")
    error_counts = Counter(row["error_class"] for row in errors)
    (root / "errors" / "error-analysis.md").write_text("# Error analysis\n\n" + table(["Class", "Count"], error_counts.most_common()) + "\n", encoding="utf-8")


def save_chart(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path.with_suffix(".svg"), bbox_inches="tight")
    plt.savefig(path.with_suffix(".png"), dpi=160, bbox_inches="tight")
    plt.close()


def charts(root: Path, daily: list[dict[str, Any]], monthly: list[dict[str, Any]], errors: list[dict[str, Any]]) -> None:
    if daily:
        labels = [row["period"] for row in daily]
        images = [row["image_completed"] for row in daily]
        videos = [row["video_completed"] for row in daily]
        x = list(range(len(labels)))
        plt.figure(figsize=(max(8, len(labels) * .45), 4.8))
        plt.bar(x, images, label="Images")
        plt.bar(x, videos, bottom=images, label="Videos")
        plt.xticks(x, labels, rotation=45, ha="right")
        plt.ylabel("Completed outputs")
        plt.title("Daily output counts")
        plt.legend()
        save_chart(root / "charts" / "daily-output-counts")
        plt.figure(figsize=(max(8, len(labels) * .45), 4.8))
        plt.plot(x, [(row["success_rate"] or 0) * 100 for row in daily], marker="o")
        plt.xticks(x, labels, rotation=45, ha="right")
        plt.ylim(0, 105)
        plt.ylabel("Success rate (%)")
        plt.title("Daily success rate")
        save_chart(root / "charts" / "daily-success-rate")
    if monthly:
        plt.figure(figsize=(max(7, len(monthly) * .8), 4.8))
        plt.bar([row["period"] for row in monthly], [row["image_completed"] + row["video_completed"] for row in monthly])
        plt.ylabel("Completed outputs")
        plt.title("Monthly output counts")
        save_chart(root / "charts" / "monthly-output-counts")
    counts = Counter(row["error_class"] for row in errors)
    plt.figure(figsize=(8, max(3.5, len(counts) * .45)))
    if counts:
        names, values = zip(*counts.most_common())
        plt.barh(list(reversed(names)), list(reversed(values)))
        plt.xlabel("Count")
    else:
        plt.text(.5, .5, "No errors recorded", ha="center", va="center")
        plt.axis("off")
    plt.title("Error classes")
    save_chart(root / "charts" / "error-classes")


def reset_generated(root: Path, site: Path) -> None:
    for name in ("data", "daily", "monthly", "runs", "errors", "charts"):
        shutil.rmtree(root / name, ignore_errors=True)
        (root / name).mkdir(parents=True)
    shutil.rmtree(site, ignore_errors=True)
    shutil.copytree(Path("dashboard"), site)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["new_only", "latest_n", "date_range", "exact_tag", "rebuild_all"], default="new_only")
    parser.add_argument("--latest-n", type=int, default=5)
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--exact-tag")
    parser.add_argument("--verify-media", action="store_true")
    parser.add_argument("--analytics-root", type=Path, default=Path("analytics"))
    parser.add_argument("--site-root", type=Path, default=Path("site"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "exact_tag" and not args.exact_tag:
        raise SystemExit("--exact-tag is required")
    state_path = args.analytics_root / "state" / "processed-releases.json"
    state = load_json(state_path, {"schema_version": 1, "processed_releases": {}})
    selected = choose(releases(), args, state)
    print("Selected:", [row["tagName"] for row in selected])
    if args.mode == "rebuild_all":
        run_map, error_map = {}, {}
        state = {"schema_version": 1, "processed_releases": {}}
    else:
        run_map = {row["run_id"]: row for row in load_json(args.analytics_root / "data" / "runs.json", [])}
        error_map = {json.dumps(row, sort_keys=True): row for row in load_json(args.analytics_root / "data" / "errors.json", [])}
    with tempfile.TemporaryDirectory(prefix="ledger-analysis-") as temp:
        for release in selected:
            tag = release["tagName"]
            target = Path(temp) / tag
            checks = download(tag, target, args.verify_media)
            run_rows, error_rows, release_state = ingest(tag, target, checks)
            for row in run_rows:
                run_map[row["run_id"]] = row
            for row in error_rows:
                error_map[json.dumps(row, sort_keys=True)] = row
            state.setdefault("processed_releases", {})[tag] = release_state
    run_rows = sorted(run_map.values(), key=lambda row: (row["date"], row["run_id"]))
    error_rows = sorted(error_map.values(), key=lambda row: (str(row.get("date")), str(row.get("timestamp"))))
    daily, monthly = aggregate(run_rows), aggregate(run_rows, monthly=True)
    categories = Counter()
    for row in run_rows:
        categories.update(row.get("categories", {}))
    reset_generated(args.analytics_root, args.site_root)
    save_json(args.analytics_root / "data" / "runs.json", run_rows)
    save_json(args.analytics_root / "data" / "errors.json", error_rows)
    save_json(args.analytics_root / "data" / "daily.json", daily)
    save_json(args.analytics_root / "data" / "monthly.json", monthly)
    save_json(args.analytics_root / "data" / "categories.json", dict(categories))
    save_json(args.site_root / "data.json", {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runs": run_rows, "daily": daily, "monthly": monthly,
        "error_classes": dict(Counter(row["error_class"] for row in error_rows)),
        "categories": dict(categories),
    })
    run_fields = ["date", "tag", "run_id", "image_completed", "video_completed", "errors", "success_rate", "latency_mean_s", "latency_p50_s", "latency_p90_s", "latency_p95_s", "started_at", "finished_at", "source_bytes", "file_count", "digest", "models", "categories", "error_classes"]
    write_csv(args.analytics_root / "data" / "runs.csv", run_rows, run_fields)
    write_csv(args.analytics_root / "data" / "daily.csv", daily, ["period", "runs", "image_completed", "video_completed", "errors", "success_rate", "latency_mean_s", "source_bytes"])
    write_csv(args.analytics_root / "data" / "monthly.csv", monthly, ["period", "runs", "image_completed", "video_completed", "errors", "success_rate", "latency_mean_s", "source_bytes"])
    write_csv(args.analytics_root / "data" / "errors.csv", error_rows, ["date", "tag", "run_id", "phase", "prompt_id", "category", "error_class", "http_status", "timestamp", "terminal", "stop_phase", "message"])
    reports(args.analytics_root, run_rows, error_rows, daily, monthly)
    charts(args.analytics_root, daily, monthly, error_rows)
    shutil.copytree(args.analytics_root / "charts", args.site_root / "charts", dirs_exist_ok=True)
    save_json(state_path, state)
    print(f"Generated {len(run_rows)} runs across {len(daily)} dates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
