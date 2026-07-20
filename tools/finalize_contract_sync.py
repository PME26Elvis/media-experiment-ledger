#!/usr/bin/env python3
"""Apply the one-time migration from a same-repository PR validation run.

Workflow files are intentionally left untouched here because a GITHUB_TOKEN
cannot safely rewrite the workflow that is currently executing. The connector
updates those files after this commit lands.
"""
from __future__ import annotations

from pathlib import Path

import apply_contract_sync as sync

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sync.patch_release_packaging()
    sync.patch_release_publishing()
    sync.patch_analytics()
    sync.patch_atlas_data()
    sync.patch_readme_summary()
    sync.patch_readmes_and_agents()
    sync.patch_specs()
    sync.write_tests()

    # Remove only the temporary Python migration tools. Workflow files are
    # restored/deleted through the GitHub connector after this commit succeeds.
    for path in (
        ROOT / "tools" / "apply_contract_sync.py",
        ROOT / "tools" / "finalize_contract_sync.py",
    ):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
