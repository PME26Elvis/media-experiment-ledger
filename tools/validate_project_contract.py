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
    contract = read_json(ROOT / "project-contract.json")
    atlas = contract.get("atlas") if isinstance(contract.get("atlas"), dict) else {}
    notes = atlas.get("release_notes") if isinstance(atlas.get("release_notes"), dict) else {}
    integrity = contract.get("experiment_integrity") if isinstance(contract.get("experiment_integrity"), dict) else {}
    planned = contract.get("planned_analysis") if isinstance(contract.get("planned_analysis"), dict) else {}

    config = read_json(ROOT / "visual-analysis" / "config.json")
    expected_atlas = {
        "prompts_per_bundle": atlas.get("prompts_per_bundle"),
        "video_prompts_per_bundle": atlas.get("prompts_per_bundle"),
        "release_notes_image_highlights": notes.get("image_max"),
        "release_notes_image_min_samples": notes.get("image_min_unique_samples"),
        "release_notes_video_highlights": notes.get("video_mode"),
        "release_notes_video_min_samples": notes.get("video_min_unique_samples"),
    }
    for key, value in expected_atlas.items():
        if config.get(key) != value:
            errors.append(
                f"visual-analysis/config.json {key}={config.get(key)!r}; "
                f"project-contract.json requires {value!r}"
            )
    if "must not change" not in str(atlas.get("yolo_independence") or ""):
        errors.append("Atlas contract must explicitly prohibit YOLO from changing Atlas")

    history_overrides_path = ROOT / str(atlas.get("history_overrides_file") or "")
    history_overrides = read_json(history_overrides_path)
    overrides = history_overrides.get("overrides")
    if not isinstance(overrides, dict) or not overrides:
        errors.append("Atlas history overrides must contain an overrides object")
    else:
        for tag, item in overrides.items():
            if not isinstance(item, dict) or not item.get("reason"):
                errors.append(f"Atlas history override {tag} requires an audited reason")
                continue
            authoritative = item.get("authoritative", False)
            if not isinstance(authoritative, bool):
                errors.append(f"Atlas history override {tag}/authoritative must be boolean")
            provided = 0
            for metric in ("images", "videos"):
                if metric in item:
                    provided += 1
                    if int(item[metric]) < 0:
                        errors.append(f"Atlas history override {tag}/{metric} cannot be negative")
            if authoritative and not provided:
                errors.append(f"Authoritative Atlas history override {tag} needs a metric")
    if "never current corpus totals" not in str(atlas.get("history_metric_policy") or ""):
        errors.append("Atlas history metric policy must prohibit current-total backfill")

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

    yolo = planned.get("yolo_object_detection") if isinstance(planned, dict) else {}
    expected_yolo = {
        "status": "implemented",
        "production_release": "media-yolo-all-2026-07-13-v1",
        "production_writeback_commit": "bab357c4f92963d5d74e7229ad86272147436295",
        "production_canonical_images": 387,
        "production_images_with_detections": 313,
        "production_total_detections": 1533,
        "workflow_path": ".github/workflows/yolo-object-detection.yml",
        "release_pattern": r"^media-yolo-all-\d{4}-\d{2}-\d{2}-v\d+$",
        "atlas_coupling": "none",
        "default_execution_plan": "one full GitHub-hosted CPU job",
        "design_corpus_images": 3000,
        "job_timeout_minutes": 350,
        "matrix_sharding_v1": False,
        "persistent_state": False,
        "cross_run_cache_skip": False,
        "published_result_reuse": False,
        "visual_lab_join_key": "image_sha256",
        "implementation_entrypoint": "tools/build_yolo_detection.py",
        "requirements": "requirements-yolo.txt",
        "model_lock": "object-detection/model-lock.json",
        "labels": "object-detection/coco-80.json",
        "latest_index": "data/yolo/latest.json",
        "history_index": "data/yolo/history.json",
        "web_index": "web/public/data/yolo/latest.json",
        "visual_lab_route": "yolo-lab",
        "release_notes_preview_max": 20,
    }
    for key, value in expected_yolo.items():
        if yolo.get(key) != value:
            errors.append(f"YOLO contract {key}={yolo.get(key)!r}; expected {value!r}")
    if "media-yolo" not in str(yolo.get("release_strategy") or ""):
        errors.append("YOLO release strategy must use the independent media-yolo-* family")
    if "from scratch" not in str(yolo.get("rebuild_policy") or ""):
        errors.append("YOLO rebuild policy must require a full from-scratch rerun")

    model_lock = read_json(ROOT / str(yolo.get("model_lock") or ""))
    labels_path = ROOT / str(yolo.get("labels") or "")
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    if model_lock.get("model_family") != "YOLOX-Tiny":
        errors.append("Pinned YOLO model must be YOLOX-Tiny")
    if model_lock.get("sha256") != "427cc366d34e27ff7a03e2899b5e3671425c262ea2291f88bb942bc1cc70b0f7":
        errors.append("Unexpected pinned YOLOX-Tiny model SHA-256")
    if not isinstance(labels, list) or len(labels) != 80:
        errors.append("COCO labels file must contain exactly 80 classes")

    history = read_json(ROOT / str(yolo.get("history_index") or ""))
    releases = history.get("releases")
    if not isinstance(releases, list) or not releases:
        errors.append("Implemented YOLO contract requires a published history row")
    else:
        latest = releases[0]
        for key, value in {
            "tag": yolo.get("production_release"),
            "images": yolo.get("production_canonical_images"),
            "images_with_detections": yolo.get("production_images_with_detections"),
            "total_detections": yolo.get("production_total_detections"),
        }.items():
            if latest.get(key) != value:
                errors.append(f"YOLO production history {key}={latest.get(key)!r}; expected {value!r}")

    require_text(ROOT / "README.md", [
        "project-contract.json", "config/release-quarantine.json",
        "config/atlas-history-overrides.json", "authoritative: true",
        "每 15 個 prompt", "YOLOX-Tiny", "API 完成事件", "封存媒體",
        "AUTO:YOLO_HISTORY:START", "media-yolo-all-2026-07-13-v1",
    ], errors)
    require_text(ROOT / "README.en.md", [
        "project-contract.json", "config/release-quarantine.json",
        "config/atlas-history-overrides.json", "authoritative: true",
        "15 prompt", "YOLOX-Tiny", "API completion events", "archived media",
        "AUTO:YOLO_HISTORY_EN:START", "media-yolo-all-2026-07-13-v1",
    ], errors)
    require_text(ROOT / "AGENTS.md", [
        "project-contract.json", "config/release-quarantine.json",
        "config/atlas-history-overrides.json", "authoritative: true",
        "Traditional Chinese", "normal merge", "implemented", "media-yolo-*",
    ], errors)
    require_text(ROOT / "docs" / "PROJECT_CONTRACT.md", [
        "Source of truth", "Release quarantine", "Prompt Repeatability Atlas",
        "atlas-history-overrides.json", "implemented", "media-yolo-*",
        "media-yolo-all-2026-07-13-v1", "Contract validation",
    ], errors)
    require_text(ROOT / "docs" / "PROMPT_REPEATABILITY_ATLAS.md", ["ZIP-only", "15 prompt", "full-corpus"], errors)
    require_text(ROOT / "docs" / "VIDEO_REPEATABILITY_ATLAS.md", ["seed", "FFprobe", "15 prompt"], errors)
    require_text(ROOT / str(yolo.get("spec") or ""), [
        "YOLOX-Tiny", "ONNX Runtime", "COCO", "media-yolo-all-",
        "單一 GitHub-hosted CPU job", "Status: **`implemented`**", "Atlas 非回歸契約",
    ], errors)
    require_text(ROOT / str(yolo.get("workflow_path") or ""), [
        "timeout-minutes: 350", "tools/build_yolo_detection.py", "media-yolo-*",
    ], errors)
    require_text(ROOT / "tools" / "build_yolo_detection.py", [
        "complete corpus from scratch", "publish_release", "rebuild_history",
    ], errors)
    require_text(ROOT / "web" / "navigation.mjs", ["YOLO Lab", "yolo-lab"], errors)

    commands = contract.get("required_validation")
    if not isinstance(commands, list):
        errors.append("required_validation must be a list")
    else:
        for required in (
            "python tools/validate_project_contract.py",
            "python tools/yolo_model_smoke.py",
        ):
            if required not in commands:
                errors.append(f"Contract required_validation is missing {required}")
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
