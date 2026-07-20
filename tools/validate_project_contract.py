#!/usr/bin/env python3
"""Fail CI when machine-readable policy and human-facing contracts drift apart."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def require_text(path: Path, tokens: list[str], errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"Missing synchronized contract surface: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in tokens:
        if token not in text:
            errors.append(f"{path.relative_to(ROOT)} is missing contract token: {token!r}")


def validate() -> list[str]:
    errors: list[str] = []
    contract_path = ROOT / "project-contract.json"
    contract = read_json(contract_path)
    atlas = contract.get("atlas") if isinstance(contract.get("atlas"), dict) else {}
    notes = atlas.get("release_notes") if isinstance(atlas.get("release_notes"), dict) else {}
    integrity = (
        contract.get("experiment_integrity")
        if isinstance(contract.get("experiment_integrity"), dict)
        else {}
    )
    planned = (
        contract.get("planned_analysis")
        if isinstance(contract.get("planned_analysis"), dict)
        else {}
    )

    config = read_json(ROOT / "visual-analysis" / "config.json")
    expected = {
        "prompts_per_bundle": atlas.get("prompts_per_bundle"),
        "video_prompts_per_bundle": atlas.get("prompts_per_bundle"),
        "release_notes_image_highlights": notes.get("image_max"),
        "release_notes_image_min_samples": notes.get("image_min_unique_samples"),
        "release_notes_video_highlights": notes.get("video_mode"),
        "release_notes_video_min_samples": notes.get("video_min_unique_samples"),
    }
    for key, value in expected.items():
        if config.get(key) != value:
            errors.append(
                f"visual-analysis/config.json {key}={config.get(key)!r}; "
                f"project-contract.json requires {value!r}"
            )

    quarantine_path = ROOT / str(contract.get("repository", {}).get("quarantine_file") or "")
    quarantine = read_json(quarantine_path)
    excluded = quarantine.get("excluded_runs")
    if not isinstance(excluded, list) or not excluded:
        errors.append("The versioned quarantine policy must contain excluded_runs")
    else:
        keys: set[tuple[str, str]] = set()
        for item in excluded:
            if not isinstance(item, dict):
                errors.append("Every quarantine item must be an object")
                continue
            key = (str(item.get("tag") or ""), str(item.get("run_id") or ""))
            if not all(key):
                errors.append("Every quarantine item needs tag and run_id")
            if key in keys:
                errors.append(f"Duplicate quarantine entry: {key}")
            keys.add(key)
            if not item.get("reason_zh") or not item.get("reason_en"):
                errors.append(f"Quarantine entry {key} requires bilingual reasons")

    surfaces = contract.get("synchronized_surfaces")
    if not isinstance(surfaces, list):
        errors.append("synchronized_surfaces must be a list")
    else:
        for value in surfaces:
            if not (ROOT / str(value)).exists():
                errors.append(f"Synchronized surface does not exist: {value}")

    require_text(
        ROOT / "README.md",
        [
            "project-contract.json",
            "config/release-quarantine.json",
            "每 15 個 prompt",
            "YOLOX-Tiny",
            "API 完成事件",
            "封存媒體",
        ],
        errors,
    )
    require_text(
        ROOT / "README.en.md",
        [
            "project-contract.json",
            "config/release-quarantine.json",
            "15 prompt",
            "YOLOX-Tiny",
            "API completion events",
            "archived media",
        ],
        errors,
    )
    require_text(
        ROOT / "AGENTS.md",
        [
            "project-contract.json",
            "config/release-quarantine.json",
            "Traditional Chinese",
            "normal merge",
            "YOLOX-Tiny",
        ],
        errors,
    )
    require_text(
        ROOT / "docs" / "PROJECT_CONTRACT.md",
        [
            "Source of truth",
            "Release quarantine",
            "Prompt Repeatability Atlas",
            "YOLOX-Tiny",
            "Contract validation",
        ],
        errors,
    )
    require_text(
        ROOT / "docs" / "PROMPT_REPEATABILITY_ATLAS.md",
        ["ZIP-only", "15 prompt", "full-corpus"],
        errors,
    )
    require_text(
        ROOT / "docs" / "VIDEO_REPEATABILITY_ATLAS.md",
        ["seed", "FFprobe", "15 prompt"],
        errors,
    )
    yolo = planned.get("yolo_object_detection") if isinstance(planned, dict) else {}
    spec_path = ROOT / str(yolo.get("spec") or "")
    require_text(
        spec_path,
        [
            "YOLOX-Tiny",
            "ONNX Runtime",
            "COCO",
            "6 hours",
            "matrix",
            "namespaced",
            "specified_not_implemented",
        ],
        errors,
    )

    commands = contract.get("required_validation")
    if not isinstance(commands, list) or "python tools/validate_project_contract.py" not in commands:
        errors.append("Contract validator must list itself in required_validation")
    if integrity.get("audit_report_json") != "data/audits/experiment-releases.json":
        errors.append("Unexpected canonical audit JSON path")
    if integrity.get("audit_report_markdown") != "docs/reports/EXPERIMENT_RELEASE_AUDIT.md":
        errors.append("Unexpected canonical audit Markdown path")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Project contract validation failed:", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("Project contract surfaces are synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
