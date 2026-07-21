#!/usr/bin/env python3
"""Fail CI when machine-readable policy and human-facing contracts drift apart."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from validate_site_build import DATA_ARTIFACTS, PRIMARY_ROUTES

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


def require_equal(actual: Any, expected: Any, label: str, errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{label}={actual!r}; expected {expected!r}")


def validate_atlas(contract: dict[str, Any], errors: list[str]) -> None:
    atlas = contract["atlas"]
    notes = atlas["release_notes"]
    config = read_json(ROOT / "visual-analysis" / "config.json")
    expected = {
        "prompts_per_bundle": atlas["prompts_per_bundle"],
        "video_prompts_per_bundle": atlas["prompts_per_bundle"],
        "release_notes_image_highlights": notes["image_max"],
        "release_notes_image_min_samples": notes["image_min_unique_samples"],
        "release_notes_video_highlights": notes["video_mode"],
        "release_notes_video_min_samples": notes["video_min_unique_samples"],
    }
    for key, value in expected.items():
        require_equal(config.get(key), value, f"visual-analysis/config.json {key}", errors)
    if "must not change" not in str(atlas.get("yolo_independence") or ""):
        errors.append("Atlas contract must prohibit detector workflows from changing Atlas")
    overrides = read_json(ROOT / atlas["history_overrides_file"]).get("overrides")
    if not isinstance(overrides, dict) or not overrides:
        errors.append("Atlas history overrides must contain an overrides object")
    else:
        for tag, item in overrides.items():
            if not isinstance(item, dict) or not item.get("reason"):
                errors.append(f"Atlas history override {tag} requires an audited reason")
            if not isinstance(item.get("authoritative", False), bool):
                errors.append(f"Atlas history override {tag}/authoritative must be boolean")
            for metric in ("images", "videos"):
                if metric in item and int(item[metric]) < 0:
                    errors.append(f"Atlas history override {tag}/{metric} cannot be negative")
    if "never current corpus totals" not in str(atlas.get("history_metric_policy") or ""):
        errors.append("Atlas history metric policy must prohibit current-total backfill")


def validate_repository(contract: dict[str, Any], errors: list[str]) -> None:
    repository = contract["repository"]
    quarantine = read_json(ROOT / repository["quarantine_file"])
    excluded = quarantine.get("excluded_runs")
    if not isinstance(excluded, list) or not excluded:
        errors.append("The versioned quarantine policy must contain excluded_runs")
    else:
        seen: set[tuple[str, str]] = set()
        for item in excluded:
            if not isinstance(item, dict):
                errors.append("Every quarantine item must be an object")
                continue
            key = (str(item.get("tag") or ""), str(item.get("run_id") or ""))
            if not all(key):
                errors.append("Every quarantine item needs tag and run_id")
            if key in seen:
                errors.append(f"Duplicate quarantine entry: {key}")
            seen.add(key)
            if not item.get("reason_zh") or not item.get("reason_en"):
                errors.append(f"Quarantine entry {key} requires bilingual reasons")
    surfaces = contract.get("synchronized_surfaces")
    if not isinstance(surfaces, list):
        errors.append("synchronized_surfaces must be a list")
    else:
        for value in surfaces:
            if not (ROOT / str(value)).exists():
                errors.append(f"Synchronized surface does not exist: {value}")


def validate_pages(contract: dict[str, Any], errors: list[str]) -> None:
    pages = contract["pages"]
    expected_static = {
        "workflow_path": ".github/workflows/analytics.yml",
        "build_output": "site/",
        "build_output_tracked": False,
        "deployment_transport": "actions/upload-pages-artifact",
        "build_deploy_writeback_separate": True,
        "deployment_independent_of_writeback": True,
        "writeback_paths": ["analytics/", "forecasts/"],
        "writeback_rebase_retries": 3,
        "primary_routes": list(PRIMARY_ROUTES),
        "deployed_json_artifacts": [relative.as_posix() for _, relative, _, _ in DATA_ARTIFACTS],
        "max_total_bytes": 1_000_000_000,
        "max_single_file_bytes": 100_000_000,
    }
    for key, expected in expected_static.items():
        require_equal(pages.get(key), expected, f"Pages contract {key}", errors)
    if "site/" not in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        errors.append(".gitignore must exclude the ephemeral site/ build output")
    workflow = ROOT / pages["workflow_path"]
    require_text(
        workflow,
        [
            "  build:", "  deploy:", "  writeback:", "needs: build",
            "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4",
            "actions/download-artifact@v5", "analytics-writeback-${{ github.run_id }}",
            "git rebase origin/main", "paths=(analytics forecasts)",
        ],
        errors,
    )
    if workflow.exists():
        text = workflow.read_text(encoding="utf-8")
        for forbidden in ("git add analytics forecasts site", "git add site"):
            if forbidden in text:
                errors.append(f"Pages workflow must not track compiled site output: {forbidden!r}")
    require_text(
        ROOT / "tools" / "validate_site_build.py",
        [
            '"visual-lab"', '"detector-lab"', '"yolo-lab"',
            'Path("data/visual-analysis.json")', 'Path("data/detection/latest.json")',
            'Path("data/yolo/latest.json")', "MAX_SITE_BYTES = 1_000_000_000",
            "MAX_FILE_BYTES = 100_000_000",
        ],
        errors,
    )


def validate_yolo(contract: dict[str, Any], errors: list[str]) -> None:
    yolo = contract["planned_analysis"]["yolo_object_detection"]
    expected = {
        "status": "implemented",
        "production_release": "media-yolo-all-2026-07-13-v1",
        "production_writeback_commit": "bab357c4f92963d5d74e7229ad86272147436295",
        "production_canonical_images": 387,
        "production_images_with_detections": 313,
        "production_total_detections": 1533,
        "workflow_path": ".github/workflows/yolo-object-detection.yml",
        "atlas_coupling": "none",
        "job_timeout_minutes": 350,
        "persistent_state": False,
        "cross_run_cache_skip": False,
        "published_result_reuse": False,
        "model_lock": "object-detection/model-lock.json",
        "labels": "object-detection/coco-80.json",
        "latest_index": "data/yolo/latest.json",
        "history_index": "data/yolo/history.json",
        "web_index": "web/public/data/yolo/latest.json",
        "visual_lab_route": "yolo-lab",
    }
    for key, value in expected.items():
        require_equal(yolo.get(key), value, f"YOLO contract {key}", errors)
    if "legacy manual recovery" not in str(yolo.get("workflow_mode") or ""):
        errors.append("YOLO legacy workflow must be manual recovery only")
    if "from scratch" not in str(yolo.get("rebuild_policy") or ""):
        errors.append("YOLO rebuild policy must require a full from-scratch rerun")
    lock = read_json(ROOT / yolo["model_lock"])
    require_equal(lock.get("model_family"), "YOLOX-Tiny", "YOLO model family", errors)
    require_equal(
        lock.get("sha256"),
        "427cc366d34e27ff7a03e2899b5e3671425c262ea2291f88bb942bc1cc70b0f7",
        "YOLO model SHA-256",
        errors,
    )
    labels = json.loads((ROOT / yolo["labels"]).read_text(encoding="utf-8"))
    if not isinstance(labels, list) or len(labels) != 80:
        errors.append("COCO labels file must contain exactly 80 classes")
    releases = read_json(ROOT / yolo["history_index"]).get("releases")
    if not isinstance(releases, list) or not releases:
        errors.append("Implemented YOLO contract requires a published history row")
    else:
        latest = releases[0]
        for key, value in {
            "tag": yolo["production_release"],
            "images": yolo["production_canonical_images"],
            "images_with_detections": yolo["production_images_with_detections"],
            "total_detections": yolo["production_total_detections"],
        }.items():
            require_equal(latest.get(key), value, f"YOLO production history {key}", errors)
    legacy = ROOT / yolo["workflow_path"]
    require_text(legacy, ["Legacy YOLO-only", "workflow_dispatch:", "default: false", "timeout-minutes: 350"], errors)
    if legacy.exists() and "  push:\n" in legacy.read_text(encoding="utf-8"):
        errors.append("Legacy YOLO-only workflow must not run automatically on push")


def validate_multidetector(contract: dict[str, Any], errors: list[str]) -> None:
    multi = contract["planned_analysis"]["multi_detector_yolox_nanodet"]
    status = multi.get("status")
    if status not in {"implemented_pending_production", "implemented"}:
        errors.append(f"Unexpected multi-detector status: {status!r}")
    expected = {
        "spec": "docs/NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md",
        "detectors": ["YOLOX-Tiny", "NanoDet-Plus-m-320"],
        "inference_workflows": [
            ".github/workflows/detector-yolox-inference.yml",
            ".github/workflows/detector-nanodet-inference.yml",
        ],
        "publisher_workflow": ".github/workflows/detector-comparison-publish.yml",
        "atlas_coupling": "none",
        "persistent_state": False,
        "cross_run_cache_skip": False,
        "published_result_reuse": False,
        "nanodet_model_lock": "object-detection/nanodet-model-lock.json",
        "nanodet_requirements": "requirements-nanodet.txt",
        "nanodet_model_smoke": "tools/nanodet_model_smoke.py",
        "artifact_builder": "tools/build_detector_artifact.py",
        "publisher_entrypoint": "tools/publish_detector_comparison.py",
        "latest_index": "data/detection/latest.json",
        "history_index": "data/detection/history.json",
        "web_index": "web/public/data/detection/latest.json",
        "detector_lab_route": "detector-lab",
        "release_notes_preview_max": 20,
    }
    for key, value in expected.items():
        require_equal(multi.get(key), value, f"Multi-detector contract {key}", errors)
    if "exact workflow run IDs" not in str(multi.get("artifact_pairing") or ""):
        errors.append("Multi-detector artifacts must be paired by exact workflow run IDs")
    if "never accuracy" not in str(multi.get("comparison_language") or ""):
        errors.append("Multi-detector contract must prohibit accuracy claims without ground truth")
    lock = read_json(ROOT / multi["nanodet_model_lock"])
    expected_lock = {
        "model_family": "NanoDet-Plus-m-320",
        "upstream_tag": "v1.0.0-alpha-1",
        "expected_size_bytes": 4_793_615,
        "sha256": "4f12723cce3d48e47ca92cb925ba74d97a965c069208edca660bbb9f7ce2c610",
        "input_width": 320,
        "input_height": 320,
        "reg_max": 7,
        "strides": [8, 16, 32, 64],
        "labels_sha256": "76ce1473f01bd271bab54429737358a97160629cf970c5ec8384c2777dd0bae9",
    }
    for key, value in expected_lock.items():
        require_equal(lock.get(key), value, f"NanoDet model lock {key}", errors)
    for path in (*multi["inference_workflows"], multi["publisher_workflow"]):
        if not (ROOT / path).exists():
            errors.append(f"Missing multi-detector workflow: {path}")
    for path in multi["inference_workflows"]:
        text = (ROOT / path).read_text(encoding="utf-8")
        if "contents: write" in text:
            errors.append(f"Inference workflow must not have contents write permission: {path}")
        for token in ("actions/upload-artifact@v4", "complete canonical corpus from scratch"):
            if token not in text:
                errors.append(f"Inference workflow {path} is missing {token!r}")
    publisher = (ROOT / multi["publisher_workflow"]).read_text(encoding="utf-8")
    for token in (
        "run-id: ${{ needs.resolve.outputs.yolox_run_id }}",
        "run-id: ${{ needs.resolve.outputs.nanodet_run_id }}",
        "github-token: ${{ github.token }}",
        "ref: main",
        "media-detection",
    ):
        if token not in publisher:
            errors.append(f"Publisher workflow is missing {token!r}")
    require_text(
        ROOT / multi["spec"],
        [
            f"Status: **`{status}`**", "detector-yolox-inference.yml",
            "detector-nanodet-inference.yml", "detector-comparison-publish.yml",
            "media-detection-all-", "exact run IDs", "analysis_batch_id",
            "Original | YOLOX-Tiny | NanoDet-Plus",
            "not ground-truth labels or an accuracy benchmark", "Atlas impact: **none**",
            "official immutable pre-exported ONNX",
        ],
        errors,
    )
    latest = read_json(ROOT / multi["latest_index"])
    history = read_json(ROOT / multi["history_index"])
    web = read_json(ROOT / multi["web_index"])
    require_equal(web, latest, "Detector web/latest index", errors)
    if not isinstance(history.get("releases"), list):
        errors.append("Detector history must contain a releases list")
    production_fields = (
        "production_release", "production_yolox_run_id", "production_nanodet_run_id",
        "production_publisher_run_id", "production_writeback_commit",
    )
    if status == "implemented_pending_production":
        for key in production_fields:
            if multi.get(key) is not None:
                errors.append(f"Pending production contract requires {key}=null")
        if latest.get("status") != "waiting_for_first_publication":
            errors.append("Pending production latest index must remain waiting_for_first_publication")
    else:
        for key in production_fields:
            if not multi.get(key):
                errors.append(f"Implemented detector contract requires {key}")
        if latest.get("status") != "published" or latest.get("release_tag") != multi.get("production_release"):
            errors.append("Implemented detector latest index must match production Release")


def validate_text_surfaces(contract: dict[str, Any], errors: list[str]) -> None:
    status = contract["planned_analysis"]["multi_detector_yolox_nanodet"]["status"]
    require_text(ROOT / "README.md", [
        "project-contract.json", "config/release-quarantine.json", "authoritative: true",
        "每 15 個 prompt", "YOLOX-Tiny", "NanoDet-Plus", "Detector Lab",
        "media-detection-*", "agreement", "NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md",
    ], errors)
    require_text(ROOT / "README.en.md", [
        "project-contract.json", "config/release-quarantine.json", "authoritative: true",
        "15 prompt", "YOLOX-Tiny", "NanoDet-Plus", "Detector Lab",
        "media-detection-*", "agreement", "NANODET_MULTI_DETECTOR_PIPELINE_SPEC.md",
    ], errors)
    require_text(ROOT / "AGENTS.md", [
        "Traditional Chinese", "normal merge", "site/", "media-detection-*",
        "exact workflow run IDs", "NanoDet-Plus", "Detector Lab", status,
    ], errors)
    require_text(ROOT / "docs" / "PROJECT_CONTRACT.md", [
        "Source of truth", "Release quarantine", "Prompt Repeatability Atlas",
        "Pages build boundary", status, "media-detection-*", "Detector Lab",
        "Contract validation",
    ], errors)
    require_text(ROOT / "docs" / "ANALYTICS_AND_PAGES.md", [
        "build", "deploy", "writeback", "not committed to Git", "cannot block Pages",
    ], errors)
    require_text(ROOT / "docs" / "WEB_EXPERIENCE_AND_FORECASTS.md", [
        "eight primary routes", "five deployed JSON artifacts", "Detector Lab", "site/",
        "actions/upload-pages-artifact",
    ], errors)
    require_text(ROOT / "docs" / "PROMPT_REPEATABILITY_ATLAS.md", ["ZIP-only", "15 prompt", "full-corpus"], errors)
    require_text(ROOT / "docs" / "VIDEO_REPEATABILITY_ATLAS.md", ["seed", "FFprobe", "15 prompt"], errors)
    require_text(ROOT / "web" / "navigation.mjs", ["Detector Lab", "detector-lab", "YOLO Lab", "yolo-lab"], errors)
    require_text(ROOT / "web" / "src" / "components" / "DetectorLab.astro", [
        "data/detection/latest.json", "not an accuracy benchmark", "Original · YOLOX-Tiny · NanoDet-Plus",
    ], errors)


def validate() -> list[str]:
    errors: list[str] = []
    contract = read_json(ROOT / "project-contract.json")
    validate_repository(contract, errors)
    validate_atlas(contract, errors)
    validate_pages(contract, errors)
    validate_yolo(contract, errors)
    validate_multidetector(contract, errors)
    validate_text_surfaces(contract, errors)
    commands = contract.get("required_validation")
    if not isinstance(commands, list):
        errors.append("required_validation must be a list")
    else:
        for required in (
            "python tools/validate_project_contract.py",
            "python tools/yolo_model_smoke.py",
            "python tools/nanodet_model_smoke.py",
            "python tools/validate_site_build.py",
        ):
            if required not in commands:
                errors.append(f"Contract required_validation is missing {required}")
    integrity = contract["experiment_integrity"]
    require_equal(integrity.get("audit_report_json"), "data/audits/experiment-releases.json", "audit_report_json", errors)
    require_equal(integrity.get("audit_report_markdown"), "docs/reports/EXPERIMENT_RELEASE_AUDIT.md", "audit_report_markdown", errors)
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
