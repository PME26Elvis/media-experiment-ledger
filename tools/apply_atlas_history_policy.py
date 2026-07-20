#!/usr/bin/env python3
"""Apply the audited legacy Atlas history migration on the feature branch."""
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
        raise RuntimeError(f"{path}: expected one migration block, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "tools/update_readme_summary.py",
        "from release_policy import is_quarantined, media_counts_from_file_records\n",
        "from atlas_history_policy import historical_metric\n"
        "from release_policy import is_quarantined, media_counts_from_file_records\n",
    )
    replace_once(
        "tools/update_readme_summary.py",
        '''        report_images = report.get("metadata_image_samples")
        report_videos = report.get("metadata_video_samples")
        images = (
            int(report_images)
            if report_images is not None
            else (sum(int(totals.per_release[tag]["images"]) for tag in selected_tags) if selected_tags else None)
        )
        videos = (
            int(report_videos)
            if report_videos is not None
            else (sum(int(totals.per_release[tag]["videos"]) for tag in selected_tags) if selected_tags else None)
        )
''',
        '''        # Historical Atlas rows are immutable snapshots. Modern reports
        # carry explicit corpus counts; audited overrides cover the few legacy
        # schemas that do not. Current experiment totals must never time-travel
        # into an older Atlas row.
        images = historical_metric(tag, report, "images")
        videos = historical_metric(tag, report, "videos")
''',
    )
    replace_once(
        "docs/PROJECT_CONTRACT.md",
        "3. `config/release-quarantine.json`：歷史無效 run 的版本化例外。\n4. README、`AGENTS.md` 與本文件：人類／agent 操作說明。\n5. Atlas、影片與 YOLO 規格：各分析模組的完整契約。\n6. tests 與 validation workflow：防止上述內容靜默漂移。\n",
        "3. `config/release-quarantine.json`：歷史無效 run 的版本化例外。\n"
        "4. `config/atlas-history-overrides.json`：只有舊 Atlas schema 缺少 corpus-count fields 時才使用的審核記錄。\n"
        "5. README、`AGENTS.md` 與本文件：人類／agent 操作說明。\n"
        "6. Atlas、影片與 YOLO 規格：各分析模組的完整契約。\n"
        "7. tests 與 validation workflow：防止上述內容靜默漂移。\n",
    )
    replace_once(
        "docs/PROJECT_CONTRACT.md",
        "- Video Release Notes 預設放入所有至少 2 unique samples 的可比較 cohorts。\n",
        "- Video Release Notes 預設放入所有至少 2 unique samples 的可比較 cohorts。\n"
        "- Atlas 歷史表只讀該 immutable Atlas report 的明確值；舊 schema 缺欄位時才讀 `config/atlas-history-overrides.json`，兩者皆無則顯示未知，絕不以目前 corpus totals 回填舊快照。\n",
    )
    replace_once(
        "AGENTS.md",
        "- Apply `config/release-quarantine.json` to every canonical corpus consumer.\n",
        "- Apply `config/release-quarantine.json` to every canonical corpus consumer.\n"
        "- Preserve immutable Atlas history: use explicit report metrics first, then `config/atlas-history-overrides.json`; never backfill an old row from current corpus totals.\n",
    )
    replace_once(
        "README.md",
        "- [`config/release-quarantine.json`](config/release-quarantine.json) 保留歷史資產但排除已確認的空 run／metadata fixture。\n",
        "- [`config/release-quarantine.json`](config/release-quarantine.json) 保留歷史資產但排除已確認的空 run／metadata fixture。\n"
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) 只補足舊 Atlas schema 缺失的歷史欄位；舊快照不會被目前 totals 改寫。\n",
    )
    replace_once(
        "README.en.md",
        "- [`config/release-quarantine.json`](config/release-quarantine.json) preserves historical assets while excluding confirmed empty runs and metadata-only fixtures.\n",
        "- [`config/release-quarantine.json`](config/release-quarantine.json) preserves historical assets while excluding confirmed empty runs and metadata-only fixtures.\n"
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) fills only fields missing from legacy Atlas schemas; current totals never rewrite immutable historical snapshots.\n",
    )
    replace_once(
        "tools/validate_project_contract.py",
        "    quarantine_path = ROOT / str(contract.get(\"repository\", {}).get(\"quarantine_file\") or \"\")\n",
        "    history_overrides_path = ROOT / str(atlas.get(\"history_overrides_file\") or \"\")\n"
        "    history_overrides = read_json(history_overrides_path)\n"
        "    overrides = history_overrides.get(\"overrides\")\n"
        "    if not isinstance(overrides, dict) or not overrides:\n"
        "        errors.append(\"Atlas history overrides must contain an overrides object\")\n"
        "    else:\n"
        "        for tag, item in overrides.items():\n"
        "            if not isinstance(item, dict) or not item.get(\"reason\"):\n"
        "                errors.append(f\"Atlas history override {tag} requires an audited reason\")\n"
        "            for metric in (\"images\", \"videos\"):\n"
        "                if isinstance(item, dict) and metric in item and int(item[metric]) < 0:\n"
        "                    errors.append(f\"Atlas history override {tag}/{metric} cannot be negative\")\n"
        "    if \"never current corpus totals\" not in str(atlas.get(\"history_metric_policy\") or \"\"):\n"
        "        errors.append(\"Atlas history metric policy must prohibit current-total backfill\")\n\n"
        "    quarantine_path = ROOT / str(contract.get(\"repository\", {}).get(\"quarantine_file\") or \"\")\n",
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/release-quarantine.json",\n            "每 15 個 prompt",\n',
        '            "config/release-quarantine.json",\n            "config/atlas-history-overrides.json",\n            "每 15 個 prompt",\n',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/release-quarantine.json",\n            "15 prompt",\n',
        '            "config/release-quarantine.json",\n            "config/atlas-history-overrides.json",\n            "15 prompt",\n',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/release-quarantine.json",\n            "Traditional Chinese",\n',
        '            "config/release-quarantine.json",\n            "config/atlas-history-overrides.json",\n            "Traditional Chinese",\n',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "Prompt Repeatability Atlas",\n            "YOLOX-Tiny",\n',
        '            "Prompt Repeatability Atlas",\n            "atlas-history-overrides.json",\n            "YOLOX-Tiny",\n',
    )
    Path(__file__).unlink()


if __name__ == "__main__":
    main()
