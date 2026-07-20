#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one target, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "README.md",
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) 只補足舊 Atlas schema 缺失的歷史欄位；舊快照不會被目前 totals 改寫。\n",
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) 通常只補足舊 Atlas schema 缺失欄位；若 report 本身已由 source Release、原始歷史表與 entry evidence 證實錯誤，才可使用審核過的 `authoritative: true` 修正。舊快照絕不被目前 totals 改寫。\n",
    )
    replace_once(
        "README.en.md",
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) fills only fields missing from legacy Atlas schemas; current totals never rewrite immutable historical snapshots.\n",
        "- [`config/atlas-history-overrides.json`](config/atlas-history-overrides.json) normally fills fields missing from legacy Atlas schemas. An audited `authoritative: true` correction is allowed only when the report itself is proven wrong by the source Release, original history, and entry evidence. Current totals never rewrite immutable snapshots.\n",
    )
    replace_once(
        "tools/validate_project_contract.py",
        '''        for tag, item in overrides.items():
            if not isinstance(item, dict) or not item.get("reason"):
                errors.append(f"Atlas history override {tag} requires an audited reason")
            for metric in ("images", "videos"):
                if isinstance(item, dict) and metric in item and int(item[metric]) < 0:
                    errors.append(f"Atlas history override {tag}/{metric} cannot be negative")
''',
        '''        for tag, item in overrides.items():
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
''',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/atlas-history-overrides.json",\n            "每 15 個 prompt",\n',
        '            "config/atlas-history-overrides.json",\n            "authoritative: true",\n            "每 15 個 prompt",\n',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/atlas-history-overrides.json",\n            "15 prompt",\n',
        '            "config/atlas-history-overrides.json",\n            "authoritative: true",\n            "15 prompt",\n',
    )
    replace_once(
        "tools/validate_project_contract.py",
        '            "config/atlas-history-overrides.json",\n            "Traditional Chinese",\n',
        '            "config/atlas-history-overrides.json",\n            "authoritative: true",\n            "Traditional Chinese",\n',
    )
    Path(__file__).unlink()


if __name__ == "__main__":
    main()
