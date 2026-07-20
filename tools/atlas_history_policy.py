"""Resolve historical Atlas corpus counts without time-traveling current totals.

Modern Atlas reports contain explicit ``metadata_image_samples`` and
``metadata_video_samples``. A few immutable legacy reports predate one or both
fields. Those releases use a small, versioned and audited override file. One
known legacy report contains a proven polluted global count; it is marked with
an explicit authoritative override. Unknown legacy reports stay unknown instead
of inheriting today's corpus totals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OVERRIDES_PATH = ROOT / "config" / "atlas-history-overrides.json"
_REPORT_KEYS = {
    "images": (
        "metadata_image_samples",
        "image_samples",
        "source_image_count",
    ),
    "videos": (
        "metadata_video_samples",
        "video_samples",
        "source_video_count",
    ),
}


def load_atlas_history_overrides(
    path: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    source = Path(path) if path is not None else DEFAULT_OVERRIDES_PATH
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Atlas history override file must be an object: {source}")
    overrides = value.get("overrides")
    if not isinstance(overrides, dict):
        raise ValueError(f"Atlas history override file needs an overrides object: {source}")
    output: dict[str, dict[str, Any]] = {}
    for tag, item in overrides.items():
        if not isinstance(item, dict):
            raise ValueError(f"Atlas history override for {tag} must be an object")
        if not str(item.get("reason") or "").strip():
            raise ValueError(f"Atlas history override for {tag} requires a reason")
        authoritative = item.get("authoritative", False)
        if not isinstance(authoritative, bool):
            raise ValueError(
                f"Atlas history override {tag}/authoritative must be a boolean"
            )
        normalized: dict[str, Any] = {
            "reason": str(item["reason"]),
            "authoritative": authoritative,
        }
        for metric in ("images", "videos"):
            if metric not in item:
                continue
            count = int(item[metric])
            if count < 0:
                raise ValueError(f"Atlas history override {tag}/{metric} cannot be negative")
            normalized[metric] = count
        if authoritative and not any(metric in normalized for metric in ("images", "videos")):
            raise ValueError(
                f"Authoritative Atlas history override {tag} must provide a metric"
            )
        output[str(tag)] = normalized
    return output


def explicit_report_metric(report: dict[str, Any], metric: str) -> int | None:
    if metric not in _REPORT_KEYS:
        raise ValueError(f"Unknown Atlas history metric: {metric}")
    for key in _REPORT_KEYS[metric]:
        value = report.get(key)
        if value is None:
            continue
        count = int(value)
        if count < 0:
            raise ValueError(f"Atlas report field {key} cannot be negative")
        return count
    source_counts = report.get("source_counts")
    if isinstance(source_counts, dict) and source_counts.get(metric) is not None:
        count = int(source_counts[metric])
        if count < 0:
            raise ValueError(f"Atlas report source_counts.{metric} cannot be negative")
        return count
    return None


def historical_metric(
    tag: str,
    report: dict[str, Any],
    metric: str,
    *,
    overrides_path: Path | str | None = None,
) -> int | None:
    """Return an immutable Atlas snapshot metric.

    Priority:
    1. an audited ``authoritative`` override for a proven corrupt legacy report;
    2. an explicit value embedded in that Atlas's own report;
    3. a non-authoritative override for a known missing legacy field;
    4. unknown (``None``).

    Current experiment totals are intentionally not accepted as an argument.
    """
    override = load_atlas_history_overrides(overrides_path).get(tag, {})
    override_value = override.get(metric)
    if override.get("authoritative") and override_value is not None:
        return int(override_value)

    explicit = explicit_report_metric(report, metric)
    if explicit is not None:
        return explicit

    return int(override_value) if override_value is not None else None
