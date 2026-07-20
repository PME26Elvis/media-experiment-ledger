#!/usr/bin/env python3
"""One-time branch patcher for the contract/audit migration.

This file is executed only by the temporary feature-branch bootstrap workflow.
It applies checked, idempotent textual migrations and then deletes itself and
that workflow before committing the final reviewable branch diff.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one old block, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, block: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + block.rstrip() + "\n", encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def patch_release_packaging() -> None:
    replace_once(
        "tools/release_packaging.py",
        "from typing import Any, Iterable, Sequence\n",
        "from typing import Any, Iterable, Sequence\n\nfrom release_policy import media_counts_from_file_records\n",
    )
    replace_once(
        "tools/release_packaging.py",
        '    stats["file_count"] = len(all_files)\n    stats["source_bytes"] = sum(p.stat().st_size for p in all_files)\n',
        '    stats["file_count"] = len(all_files)\n    stats["source_bytes"] = sum(p.stat().st_size for p in all_files)\n'
        '    archived = media_counts_from_file_records(file_records)\n'
        '    stats["archived_images"] = archived["images"]\n'
        '    stats["archived_videos"] = archived["videos"]\n',
    )


def patch_release_publishing() -> None:
    replace_once(
        "tools/release_publishing.py",
        "from release_packaging import CommandError, RunPlan, inspect_run, json_digest, package_run, run_command\n",
        "from release_packaging import CommandError, RunPlan, inspect_run, json_digest, package_run, run_command\n"
        "from release_policy import media_counts_from_file_records, validate_publishable_run\n",
    )
    target = ROOT / "tools/release_publishing.py"
    text = target.read_text(encoding="utf-8")
    start = text.index("def release_notes(manifest: dict[str, Any]) -> str:\n")
    end = text.index("\n\ndef next_tag", start)
    replacement = '''def release_notes(manifest: dict[str, Any]) -> str:
    runs = manifest["runs"]
    api_image_events = sum(
        int(run["stats"].get("image_completed", 0)) for run in runs
    )
    api_video_events = sum(
        int(run["stats"].get("video_completed", 0)) for run in runs
    )
    archived_images = 0
    archived_videos = 0
    for run in runs:
        stats = run.get("stats") if isinstance(run.get("stats"), dict) else {}
        files = run.get("files") if isinstance(run.get("files"), list) else []
        counted = media_counts_from_file_records(files)
        archived_images += int(stats.get("archived_images", counted["images"]))
        archived_videos += int(stats.get("archived_videos", counted["videos"]))
    error_count = sum(int(run["stats"].get("errors", 0)) for run in runs)
    media_bytes = sum(
        int(asset["size_bytes"])
        for run in runs
        for asset in run["assets"]
        if asset["kind"] in {"images", "videos"}
    )
    models = sorted(
        {model for run in runs for model in run["stats"].get("models", [])}
    )
    lines = [
        "<!-- managed:experiment-release:v2 -->",
        f"Experiment date: **{manifest['experiment_date_taipei']}** (Asia/Taipei)",
        f"Runs: **{len(runs)}**",
        f"API image completion events: **{api_image_events:,}**",
        f"Archived image files: **{archived_images:,}**",
        f"API video completion events: **{api_video_events:,}**",
        f"Archived video files: **{archived_videos:,}**",
        f"Errors: **{error_count:,}**",
        f"Packaged media: **{media_bytes / 1024**3:.2f} GiB**",
        "Integrity: **completion events match archived media files**",
        "",
        "API completion events and archived media are intentionally shown as "
        "separate evidence. Publication is blocked if their image or video "
        "counts differ.",
        "",
        "## Included runs",
    ]
    lines.extend(f"- `{run['run_id']}`" for run in runs)
    if models:
        lines.extend(["", "## Models", *[f"- `{model}`" for model in models]])
    lines.extend(
        [
            "",
            "## Data layout",
            "Media is grouped by run and media type. JSONL metadata and the "
            "release manifest are separate assets so analytics can run without "
            "downloading media archives.",
            "",
            f"Manifest digest: `{manifest['content_digest']}`",
        ]
    )
    return "\\n".join(lines) + "\\n"
'''
    target.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
    replace_once(
        "tools/release_publishing.py",
        "        inspected = inspect_run(run_dir)\n        remote_digest = remote_runs.get(inspected.run_id)\n",
        "        inspected = inspect_run(run_dir)\n        validate_publishable_run(inspected)\n        remote_digest = remote_runs.get(inspected.run_id)\n",
    )


def patch_analytics() -> None:
    replace_once(
        "tools/analyze_releases.py",
        "import matplotlib.pyplot as plt\n",
        "import matplotlib.pyplot as plt\n\nfrom release_policy import is_quarantined, quarantine_policy_digest\n",
    )
    replace_once(
        "tools/analyze_releases.py",
        "        for entry in manifest.get(\"runs\", []):\n            run, errors = summarize(date, tag, entry, root)\n",
        "        for entry in manifest.get(\"runs\", []):\n"
        "            run_id = str(entry.get(\"run_id\") or \"\") if isinstance(entry, dict) else \"\"\n"
        "            if is_quarantined(tag, run_id):\n"
        "                continue\n"
        "            run, errors = summarize(date, tag, entry, root)\n",
    )
    replace_once(
        "tools/analyze_releases.py",
        '        "media_verification": checks,\n',
        '        "media_verification": checks,\n        "quarantine_policy_digest": quarantine_policy_digest(),\n',
    )


def patch_atlas_data() -> None:
    replace_once(
        "tools/prompt_atlas_data.py",
        "from PIL import Image\n",
        "from PIL import Image\n\nfrom release_policy import metadata_is_quarantined, quarantine_policy_digest\n",
    )
    replace_once(
        "tools/prompt_atlas_data.py",
        "ATLAS_DATASET_SCHEMA_VERSION = 2\n",
        "ATLAS_DATASET_SCHEMA_VERSION = 3\n",
    )
    replace_once(
        "tools/prompt_atlas_data.py",
        "def read_jsonl(path: Path) -> list[dict[str, Any]]:\n    rows: list[dict[str, Any]] = []\n",
        "def read_jsonl(path: Path) -> list[dict[str, Any]]:\n"
        "    if metadata_is_quarantined(path):\n"
        "        return []\n"
        "    rows: list[dict[str, Any]] = []\n",
    )
    replace_once(
        "tools/prompt_atlas_data.py",
        '        "policy": config,\n',
        '        "policy": config,\n        "quarantine_policy_digest": quarantine_policy_digest(),\n',
    )


def patch_readme_summary() -> None:
    replace_once(
        "tools/update_readme_summary.py",
        "from urllib.parse import quote\n",
        "from urllib.parse import quote\n\nfrom release_policy import is_quarantined, media_counts_from_file_records\n",
    )
    replace_once(
        "tools/update_readme_summary.py",
        "    for path in sorted(target.glob(\"run_*-outputs.jsonl\")):\n        with path.open",
        "    for path in sorted(target.glob(\"run_*-outputs.jsonl\")):\n"
        "        run_id = path.name.removesuffix(\"-outputs.jsonl\")\n"
        "        if is_quarantined(tag, run_id):\n"
        "            continue\n"
        "        with path.open",
    )
    replace_once(
        "tools/update_readme_summary.py",
        "                    key = (str(run.get(\"run_id\") or \"\"), str(run.get(\"digest\") or \"\"))\n                    if key in seen_runs:\n",
        "                    run_id = str(run.get(\"run_id\") or \"\")\n"
        "                    if is_quarantined(tag, run_id):\n"
        "                        continue\n"
        "                    key = (run_id, str(run.get(\"digest\") or \"\"))\n"
        "                    if key in seen_runs:\n",
    )
    replace_once(
        "tools/update_readme_summary.py",
        "                    stats = run.get(\"stats\") if isinstance(run.get(\"stats\"), dict) else {}\n                    images += int(stats.get(\"image_completed\") or 0)\n                    videos += int(stats.get(\"video_completed\") or 0)\n",
        "                    files = run.get(\"files\") if isinstance(run.get(\"files\"), list) else []\n"
        "                    archived = media_counts_from_file_records(files)\n"
        "                    images += archived[\"images\"]\n"
        "                    videos += archived[\"videos\"]\n",
    )
    replace_once(
        "tools/update_readme_summary.py",
        "        images = sum(int(totals.per_release[tag][\"images\"]) for tag in selected_tags) if selected_tags else None\n        videos = sum(int(totals.per_release[tag][\"videos\"]) for tag in selected_tags) if selected_tags else None\n",
        "        report_images = report.get(\"metadata_image_samples\")\n"
        "        report_videos = report.get(\"metadata_video_samples\")\n"
        "        images = (\n"
        "            int(report_images)\n"
        "            if report_images is not None\n"
        "            else (sum(int(totals.per_release[tag][\"images\"]) for tag in selected_tags) if selected_tags else None)\n"
        "        )\n"
        "        videos = (\n"
        "            int(report_videos)\n"
        "            if report_videos is not None\n"
        "            else (sum(int(totals.per_release[tag][\"videos\"]) for tag in selected_tags) if selected_tags else None)\n"
        "        )\n",
    )
    replace_once(
        "tools/update_readme_summary.py",
        '"> 此區塊由 GitHub Actions 全量重建；只統計正式 `media-exp-*` Releases，`media-input-*` snapshot 不會重複計入。",\n',
        '"> 此區塊由 GitHub Actions 全量重建；只統計正式 `media-exp-*` 中非 quarantine runs 的封存媒體，`media-input-*` snapshot 與純 metadata fixture 不會重複計入。",\n',
    )
    replace_once(
        "tools/update_readme_summary.py",
        '"> Rebuilt from all Releases by GitHub Actions. Only formal `media-exp-*` Releases are counted; `media-input-*` snapshots are excluded.",\n',
        '"> Rebuilt from all Releases by GitHub Actions. Totals count archived media from non-quarantined runs in formal `media-exp-*` Releases; `media-input-*` snapshots and metadata-only fixtures are excluded.",\n',
    )


def patch_workflows() -> None:
    replace_once(
        ".github/workflows/validate.yml",
        '      - "tools/**"\n      - "tests/**"\n',
        '      - "tools/**"\n      - "tests/**"\n      - "README.md"\n      - "README.en.md"\n      - "AGENTS.md"\n      - "project-contract.json"\n      - "config/**"\n      - "docs/**"\n',
    )
    # Same block occurs in push paths after the first replacement.
    replace_once(
        ".github/workflows/validate.yml",
        '      - "tools/**"\n      - "tests/**"\n',
        '      - "tools/**"\n      - "tests/**"\n      - "README.md"\n      - "README.en.md"\n      - "AGENTS.md"\n      - "project-contract.json"\n      - "config/**"\n      - "docs/**"\n',
    )
    replace_once(
        ".github/workflows/validate.yml",
        "      - run: python -m compileall tools tests\n",
        "      - name: Validate synchronized project contract\n"
        "        run: python tools/validate_project_contract.py\n"
        "      - run: python -m compileall tools tests\n",
    )
    replace_once(
        ".github/workflows/visual-analysis.yml",
        "      - 'tools/release_publishing.py'\n",
        "      - 'tools/release_publishing.py'\n"
        "      - 'tools/release_policy.py'\n"
        "      - 'config/release-quarantine.json'\n"
        "      - 'project-contract.json'\n",
    )
    replace_once(
        ".github/workflows/analytics.yml",
        '      - "tools/forecast_*.py"\n',
        '      - "tools/forecast_*.py"\n'
        '      - "tools/analyze_releases.py"\n'
        '      - "tools/release_policy.py"\n'
        '      - "config/release-quarantine.json"\n'
        '      - "project-contract.json"\n',
    )
    replace_once(
        ".github/workflows/analytics.yml",
        '''          if [[ "$EVENT_NAME" == "release" ]]; then
            args+=(--mode exact_tag --exact-tag "$EVENT_TAG")
          else
            mode="${INPUT_MODE:-new_only}"
''',
        '''          if [[ "$EVENT_NAME" == "release" ]]; then
            args+=(--mode exact_tag --exact-tag "$EVENT_TAG")
          elif [[ "$EVENT_NAME" == "push" ]]; then
            # Contract, quarantine, or analytics-code changes must rebuild the
            # complete canonical corpus rather than retaining polluted state.
            args+=(--mode rebuild_all)
          else
            mode="${INPUT_MODE:-new_only}"
''',
    )


def patch_readmes_and_agents() -> None:
    replace_once(
        "README.md",
        "這是一個以 GitHub Releases 為資料層的媒體生成實驗平台，用來管理圖片／影片 prompt、不可變更的實驗資料、可重建分析、圖片與影片 Prompt Repeatability Atlas、預測模型與 GitHub Pages 儀表板，同時避免把大型原始結果直接提交進 Git history。\n",
        "這是一個以 GitHub Releases 為資料層的媒體生成實驗平台，用來管理圖片／影片 prompt、不可變更的實驗資料、可重建分析、圖片與影片 Prompt Repeatability Atlas、預測模型與 GitHub Pages 儀表板，同時避免把大型原始結果直接提交進 Git history。\n\n"
        "## 專案契約與資料完整性\n\n"
        "- [`project-contract.json`](project-contract.json) 是機器可驗證的同步錨點；[`docs/PROJECT_CONTRACT.md`](docs/PROJECT_CONTRACT.md) 是人類可讀版本。\n"
        "- [`config/release-quarantine.json`](config/release-quarantine.json) 保留歷史資產但排除已確認的空 run／metadata fixture。\n"
        "- 正式統計分開呈現 **API 完成事件** 與 **封存媒體**；新發布若兩者數量不一致會被阻止。\n"
        "- [`Experiment Release Audit`](docs/reports/EXPERIMENT_RELEASE_AUDIT.md) 會全量排查所有 `media-exp-*` manifests、JSONL、ZIP members、size、SHA-256 與 CRC。\n"
        "- YOLOX-Tiny／ONNX Runtime／COCO 物件偵測目前為[詳盡規格](docs/YOLO_OBJECT_DETECTION_SPEC.md)，狀態是 **specified, not implemented**。\n",
    )
    replace_once(
        "README.md",
        "Atlas Release tag 使用：\n",
        "圖片與影片維持每 15 個 prompt IDs 一個 ZIP bundle。\n\nAtlas Release tag 使用：\n",
    )
    replace_once(
        "README.en.md",
        "A release-backed experiment platform for structured image and video generation runs. The repository keeps prompt banks, immutable experiment Releases, reproducible analytics, full-corpus image/video repeatability atlases, forecasts, and an Astro/Starlight observatory without committing original result folders to Git history.\n",
        "A release-backed experiment platform for structured image and video generation runs. The repository keeps prompt banks, immutable experiment Releases, reproducible analytics, full-corpus image/video repeatability atlases, forecasts, and an Astro/Starlight observatory without committing original result folders to Git history.\n\n"
        "## Project contract and data integrity\n\n"
        "- [`project-contract.json`](project-contract.json) is the machine-validated synchronization anchor; [`docs/PROJECT_CONTRACT.md`](docs/PROJECT_CONTRACT.md) is the human-readable contract.\n"
        "- [`config/release-quarantine.json`](config/release-quarantine.json) preserves historical assets while excluding confirmed empty runs and metadata-only fixtures.\n"
        "- Formal reporting separates **API completion events** from **archived media**; new publication is blocked when those counts differ.\n"
        "- The [`Experiment Release Audit`](docs/reports/EXPERIMENT_RELEASE_AUDIT.md) fully checks every `media-exp-*` manifest, JSONL file, ZIP member, byte size, SHA-256, and CRC.\n"
        "- YOLOX-Tiny / ONNX Runtime / COCO object detection has a [detailed specification](docs/YOLO_OBJECT_DETECTION_SPEC.md) and is **specified, not implemented**.\n",
    )
    replace_once(
        "README.en.md",
        "Companion tags use:\n",
        "Image and video outputs remain in bundles containing up to 15 prompt IDs.\n\nCompanion tags use:\n",
    )
    replace_once(
        "AGENTS.md",
        "## Repository source-of-truth rules\n",
        "## Contract hierarchy\n\n"
        "- Read `project-contract.json` first for machine-enforced values and `docs/PROJECT_CONTRACT.md` for rationale.\n"
        "- Apply `config/release-quarantine.json` to every canonical corpus consumer.\n"
        "- When a contract changes, update all synchronized surfaces in the same PR and run `python tools/validate_project_contract.py`.\n"
        "- YOLOX-Tiny object detection is currently specified, not implemented; do not present planned behavior as production.\n\n"
        "## Repository source-of-truth rules\n",
    )
    replace_once(
        "AGENTS.md",
        "- Existing published experiment Releases are immutable. New data for an existing date must use the established supplemental Release flow.\n",
        "- Existing published experiment Releases are immutable. New data for an existing date must use the established supplemental Release flow.\n"
        "- Historical invalid runs remain as evidence but are excluded through `config/release-quarantine.json`; never silently delete them.\n"
        "- Distinguish API completion events from archived media files. Publication must fail when their counts differ.\n",
    )
    replace_once(
        "AGENTS.md",
        "```bash\npython -m pip install \\\n",
        "```bash\npython tools/validate_project_contract.py\npython -m pip install \\\n",
    )


def patch_specs() -> None:
    append_once(
        "docs/PROMPT_REPEATABILITY_ATLAS.md",
        "## Synchronized project contract",
        """## Synchronized project contract

This is a **full-corpus** analysis over non-quarantined formal runs. Release assets remain **ZIP-only**, and image/video outputs remain in deterministic bundles containing up to **15 prompt** IDs. The machine-readable values live in `project-contract.json`; the canonical quarantine is `config/release-quarantine.json`.""",
    )
    append_once(
        "docs/VIDEO_REPEATABILITY_ATLAS.md",
        "## Synchronized contract anchor",
        """## Synchronized contract anchor

Video samples use FFprobe/FFmpeg validation, retain random `seed` as evidence but not cohort identity, and remain in deterministic bundles containing up to **15 prompt** IDs. The full corpus excludes runs listed in `config/release-quarantine.json`.""",
    )


def write_tests() -> None:
    write(
        "tests/test_release_policy.py",
        '''from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from release_policy import (
    filter_manifest_runs,
    media_counts_from_file_records,
    quarantine_policy_digest,
    validate_publishable_run,
)


class ReleasePolicyTests(unittest.TestCase):
    def test_historical_fixture_and_empty_run_are_quarantined(self) -> None:
        runs = [
            {"run_id": "run_20260629_232751"},
            {"run_id": "run_20260629_233317"},
            {"run_id": "run_test"},
        ]
        included, excluded = filter_manifest_runs("media-exp-2026-06-29", runs)
        self.assertEqual([row["run_id"] for row in included], ["run_20260629_233317"])
        self.assertEqual(
            [row["run"]["run_id"] for row in excluded],
            ["run_20260629_232751", "run_test"],
        )

    def test_media_counts_use_manifest_file_records(self) -> None:
        counts = media_counts_from_file_records(
            [
                {"path": "media/images/i0001.png"},
                {"path": "media/images/i0002.webp"},
                {"path": "media/videos/v001.mp4"},
                {"path": "outputs.jsonl"},
            ]
        )
        self.assertEqual(counts, {"images": 2, "videos": 1})

    def test_publishable_run_requires_matching_events_and_media(self) -> None:
        valid = SimpleNamespace(
            run_id="run_20260720_120000",
            files=(
                {"path": "outputs.jsonl"},
                {"path": "media/images/i0001.png"},
                {"path": "media/videos/v001.mp4"},
            ),
            stats={"file_count": 3, "image_completed": 1, "video_completed": 1},
        )
        validate_publishable_run(valid)
        invalid = SimpleNamespace(
            run_id="run_20260720_120001",
            files=valid.files,
            stats={"file_count": 3, "image_completed": 2, "video_completed": 1},
        )
        with self.assertRaisesRegex(ValueError, "completion/media integrity mismatch"):
            validate_publishable_run(invalid)

    def test_test_named_and_empty_runs_cannot_be_published(self) -> None:
        with self.assertRaisesRegex(ValueError, "run ID must match"):
            validate_publishable_run(SimpleNamespace(run_id="run_test", files=(), stats={}))
        with self.assertRaisesRegex(ValueError, "empty runs"):
            validate_publishable_run(
                SimpleNamespace(
                    run_id="run_20260720_120000",
                    files=(),
                    stats={"file_count": 0},
                )
            )

    def test_quarantine_digest_is_stable_and_content_sensitive(self) -> None:
        first = quarantine_policy_digest()
        self.assertEqual(first, quarantine_policy_digest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.json"
            path.write_text(json.dumps({"schema_version": 1, "excluded_runs": []}), encoding="utf-8")
            self.assertNotEqual(first, quarantine_policy_digest(path))


if __name__ == "__main__":
    unittest.main()
''',
    )
    write(
        "tests/test_audit_experiment_releases.py",
        '''from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_experiment_releases import audit_release_directory, render_release_notes


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\\n" for row in rows), encoding="utf-8")


class ExperimentReleaseAuditTests(unittest.TestCase):
    def test_audit_separates_canonical_and_quarantined_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_id = "run_20260629_233317"
            fixture_id = "run_test"
            image_member = "media/images/i0001.png"
            archive_name = f"{canonical_id}-images.zip"
            with zipfile.ZipFile(root / archive_name, "w") as archive:
                archive.writestr(image_member, b"fake-image-bytes")
            write_jsonl(
                root / f"{canonical_id}-outputs.jsonl",
                [{"event": "image_completed", "prompt_id": "i0001"}],
            )
            write_jsonl(
                root / f"{fixture_id}-outputs.jsonl",
                [{"event": "image_completed", "prompt_id": f"i{index:04d}"} for index in range(550)],
            )
            manifest = {
                "experiment_date_taipei": "2026-06-29",
                "content_digest": "digest",
                "runs": [
                    {
                        "run_id": canonical_id,
                        "digest": "a",
                        "stats": {"image_completed": 1, "video_completed": 0, "file_count": 2},
                        "files": [
                            {"path": "outputs.jsonl"},
                            {"path": image_member},
                        ],
                        "assets": [
                            {
                                "name": archive_name,
                                "kind": "images",
                                "size_bytes": (root / archive_name).stat().st_size,
                                "sha256": "",
                            }
                        ],
                    },
                    {
                        "run_id": fixture_id,
                        "digest": "b",
                        "stats": {"image_completed": 550, "video_completed": 7, "file_count": 1, "source_bytes": 352949},
                        "files": [{"path": "outputs.jsonl"}],
                        "assets": [],
                    },
                ],
            }
            (root / "manifest-2026-06-29.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit_release_directory(
                "media-exp-2026-06-29",
                root,
                verify_archives=True,
            )
            self.assertEqual(result["canonical_runs"], 1)
            self.assertEqual(result["quarantined_runs"], 1)
            self.assertEqual(result["totals"]["archived_images"], 1)
            self.assertEqual(result["totals"]["api_image_completed"], 1)
            self.assertEqual(result["status"], "corrected")
            notes = render_release_notes(result)
            self.assertIn("API image completion events: **1**", notes)
            self.assertIn("Archived image files: **1**", notes)
            self.assertIn("`run_test`", notes)
            self.assertNotIn("API image completion events: **550**", notes)


if __name__ == "__main__":
    unittest.main()
''',
    )
    write(
        "tests/test_project_contract.py",
        '''from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_project_contract import validate


class ProjectContractTests(unittest.TestCase):
    def test_all_contract_surfaces_are_synchronized(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
''',
    )


def main() -> None:
    patch_release_packaging()
    patch_release_publishing()
    patch_analytics()
    patch_atlas_data()
    patch_readme_summary()
    patch_workflows()
    patch_readmes_and_agents()
    patch_specs()
    write_tests()
    # Bootstrap files remove themselves before the workflow commits.
    (ROOT / "tools" / "apply_contract_sync.py").unlink()
    (ROOT / ".github" / "workflows" / "contract-sync-bootstrap.yml").unlink()


if __name__ == "__main__":
    main()
